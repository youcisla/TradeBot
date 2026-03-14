"""ICT Strategy — BaseStrategy implementation wrapping the ICT Engine.

This is the glue between the ICT analysis engine and the existing
strategy agent pipeline.  It receives a MarketContext (which carries
raw candles), fetches HTF candles from the broker, runs the full ICT
pipeline, and returns a Signal compatible with StrategyAgent.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Optional

from config import settings
from models.market_data import Candle, MarketContext
from models.signal import EntrySnapshot, Signal
from strategies.base_strategy import BaseStrategy
from strategies.ict.engine import ICTEngine
from utils.helpers import current_session, day_of_week

logger = logging.getLogger(__name__)


class ICTStrategy(BaseStrategy):
    """ICT / Smart Money Concepts strategy.

    Wraps :class:`ICTEngine` so that the existing ``StrategyAgent``
    can iterate over it just like any other strategy.
    """

    name = "ict_smc"

    def __init__(
        self,
        broker=None,
        db=None,
        min_confidence: float = 55.0,
        htf_timeframe: str = "H4",
        htf_candle_count: int = 200,
        entry_timeframe: str = "M15",
        entry_candle_count: int = 250,
    ) -> None:
        self._broker = broker
        self._db = db
        self._engine = ICTEngine(min_confidence=min_confidence)
        self._htf_tf = htf_timeframe
        self._htf_count = htf_candle_count
        self._entry_tf = entry_timeframe
        self._entry_count = entry_candle_count

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("strategy", level, msg, data)

    # ── BaseStrategy interface ───────────────────────────────────────

    def detect(self, context: MarketContext) -> Optional[Signal]:
        try:
            return self._detect_inner(context)
        except Exception:
            logger.exception("ICTStrategy.detect failed on %s", context.symbol)
            return None

    def calculate_sl(self, context: MarketContext, direction: str) -> float:
        # SL is computed inside the engine per-setup; this is a fallback
        risk = context.atr if context.atr > 0 else 0.001
        if direction == "BUY":
            return round(context.current_price - risk * 1.5, 5)
        return round(context.current_price + risk * 1.5, 5)

    def calculate_tps(
        self,
        context: MarketContext,
        entry: float,
        sl: float,
        direction: str,
    ) -> tuple[float, float, float]:
        # TPs computed inside the engine; this is a fallback
        risk = abs(entry - sl)
        if direction == "BUY":
            return (
                round(entry + risk * 1.5, 5),
                round(entry + risk * 2.5, 5),
                round(entry + risk * 3.5, 5),
            )
        return (
            round(entry - risk * 1.5, 5),
            round(entry - risk * 2.5, 5),
            round(entry - risk * 3.5, 5),
        )

    # ── Internal ─────────────────────────────────────────────────────

    def _detect_inner(self, ctx: MarketContext) -> Optional[Signal]:
        candles = ctx.candles
        if len(candles) < 30:
            self._emit("warn", f"ICT {ctx.symbol}: only {len(candles)} candles (need 30+) — skipping")
            return None

        # Fetch HTF candles from broker (H4 for bias/regime)
        htf_candles: list[Candle] = []
        if self._broker:
            try:
                htf_candles = self._broker.get_candles(
                    ctx.symbol, self._htf_tf, self._htf_count,
                )
            except Exception:
                logger.warning("Failed to fetch HTF candles for %s", ctx.symbol)

        # Fetch entry-TF candles (M15) for more precise setup detection
        entry_candles: list[Candle] = []
        if self._broker and self._entry_tf != settings.DEFAULT_TIMEFRAME:
            try:
                entry_candles = self._broker.get_candles(
                    ctx.symbol, self._entry_tf, self._entry_count,
                )
            except Exception:
                logger.warning("Failed to fetch %s candles for %s",
                               self._entry_tf, ctx.symbol)

        # Run on entry TF first (more precise), fall back to H1
        execution_candles = entry_candles if len(entry_candles) >= 30 else candles
        execution_tf = self._entry_tf if len(entry_candles) >= 30 else settings.DEFAULT_TIMEFRAME

        # Run the ICT engine
        ict_ctx, best, rejected = self._engine.analyze(
            symbol=ctx.symbol,
            candles=execution_candles,
            htf_candles=htf_candles,
            current_price=ctx.current_price,
            bid=ctx.bid,
            ask=ctx.ask,
            atr=ctx.atr,
            timeframe=execution_tf,
        )

        # Store ICT context for dashboard Fibonacci visualization
        try:
            from utils.candle_server import set_ict_context
            set_ict_context(ctx.symbol, ict_ctx)
        except Exception:
            pass

        # If M15 found nothing, try H1 as a fallback
        if best is None and execution_candles is not candles and len(candles) >= 30:
            ict_ctx, best, rejected = self._engine.analyze(
                symbol=ctx.symbol,
                candles=candles,
                htf_candles=htf_candles,
                current_price=ctx.current_price,
                bid=ctx.bid,
                ask=ctx.ask,
                atr=ctx.atr,
                timeframe=settings.DEFAULT_TIMEFRAME,
            )
            try:
                from utils.candle_server import set_ict_context
                set_ict_context(ctx.symbol, ict_ctx)
            except Exception:
                pass

        if best is None:
            # Log why to the agent feed for dashboard visibility
            if rejected:
                # Determine which threshold applied
                from models.ict_models import SetupModel as _SM
                _is_range = rejected.model in (_SM.RANGE_DEALING_LONG, _SM.RANGE_DEALING_SHORT)
                _thresh = self._engine.range_min_confidence if _is_range else self._engine.min_confidence
                self._emit("info",
                           f"ICT {ctx.symbol}: {rejected.model.value} setup found but score "
                           f"{rejected.confidence:.0f}/100 < {_thresh:.0f} threshold "
                           f"(bias={ict_ctx.htf_bias.value} zone={ict_ctx.premium_discount})")
            else:
                self._emit("info",
                           f"ICT {ctx.symbol}: no setup found "
                           f"(bias={ict_ctx.htf_bias.value} regime={ict_ctx.htf_regime.value} "
                           f"zone={ict_ctx.premium_discount} "
                           f"candles={len(candles)} htf={len(htf_candles)})")
            return None

        # We include historical backtest analysis in the Agent decision
        model_slug = f"{self.name}:{best.model.name}"
        historical_conf = 0.5
        
        if self._db:
            historical_conf = self._db.get_confidence(model_slug)
            # If backtesting proved this model is unprofitable, the agent suppresses the signal
            if historical_conf < settings.CONFIDENCE_ALLOW:
                self._emit("info", f"Rejecting {best.model.name} setup due to poor historical confidence ({historical_conf:.2f})")
                return None
                
        # Blend the real-time confluence score (115 scale) with historical confidence
        realtime_conf = max(0.1, min(1.0, best.confidence / 100.0))
        final_conf = (historical_conf + realtime_conf) / 2.0
        
        if final_conf < settings.CONFIDENCE_ALLOW:
            self._emit("info", f"Rejecting {best.model.name} (blended conf {final_conf:.2f} < {settings.CONFIDENCE_ALLOW})")
            return None

        # Build Signal for the existing pipeline
        snapshot = EntrySnapshot(
            spread=ctx.spread,
            rsi_aligned=True,  # ICT doesn't use RSI directly
            trend_aligned=best.htf_bias_aligned,
            volume_sufficient=ctx.volume > 0,
            near_news_event=ctx.near_news_event,
            market_condition=ict_ctx.htf_regime.value,
            session=ict_ctx.session_info.session.value,
            day_of_week=day_of_week(),
        )

        # Build a rich reason string for dashboard explainability
        confluences = []
        if best.htf_bias_aligned:
            confluences.append(f"HTF={ict_ctx.htf_bias.value}")
        if best.premium_discount_aligned:
            confluences.append(f"zone={ict_ctx.premium_discount}")
        if best.liquidity_swept:
            confluences.append("sweep=✓")
        if best.mss_confirmed:
            confluences.append("MSS=✓")
        if best.displacement_present:
            confluences.append("disp=✓")
        if best.fvg_present:
            confluences.append("FVG=✓")
        if best.ob_present:
            confluences.append("OB=✓")
        if best.session_valid:
            confluences.append(f"session={ict_ctx.session_info.session.value}")

        reason = (
            f"ICT {best.model.value}: {best.reason} | "
            f"Confluences: {', '.join(confluences)} | "
            f"Score: {best.confidence:.0f}/100 | Hist_Conf: {historical_conf:.2f}"
        )
        if best.missing:
            reason += f" | Missing: {', '.join(best.missing)}"

        signal = Signal(
            strategy=model_slug,  # Tell TradeManager exactly which model this is!
            symbol=ctx.symbol,
            direction=best.direction,
            entry_price=best.entry_price,
            stop_loss=best.stop_loss,
            take_profit_1=best.take_profit_1,
            take_profit_2=best.take_profit_2,
            take_profit_3=best.take_profit_3,
            confidence=final_conf,  # normalized to 0.0 - 1.0
            timestamp=datetime.now(UTC),
            reason=reason,
            entry_snapshot=snapshot,
        )

        # Persist setup to DB for dashboard analytics
        self._log_setup(best, ict_ctx)

        return signal

    def _log_setup(self, best, ict_ctx) -> None:
        """Log the detected ICT setup to the database."""
        if not self._db:
            return
        try:
            self._db.save_ict_setup({
                "symbol": best.symbol,
                "direction": best.direction,
                "model": best.model.value,
                "entry_price": best.entry_price,
                "stop_loss": best.stop_loss,
                "take_profit_1": best.take_profit_1,
                "take_profit_2": best.take_profit_2,
                "take_profit_3": best.take_profit_3,
                "confidence": best.confidence,
                "htf_bias": ict_ctx.htf_bias.value,
                "htf_regime": ict_ctx.htf_regime.value,
                "premium_discount": ict_ctx.premium_discount,
                "entry_zone": best.entry_zone,
                "reason": best.reason,
                "confluences": {
                    "htf_bias_aligned": best.htf_bias_aligned,
                    "premium_discount_aligned": best.premium_discount_aligned,
                    "liquidity_swept": best.liquidity_swept,
                    "mss_confirmed": best.mss_confirmed,
                    "displacement_present": best.displacement_present,
                    "fvg_present": best.fvg_present,
                    "ob_present": best.ob_present,
                    "session_valid": best.session_valid,
                    "rr_acceptable": best.rr_acceptable,
                },
                "missing": best.missing,
                "session": ict_ctx.session_info.session.value,
                "executed": False,
            })
        except Exception:
            logger.debug("Failed to log ICT setup to DB", exc_info=True)
