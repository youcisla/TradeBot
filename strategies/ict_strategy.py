"""ICT Strategy — BaseStrategy implementation wrapping the ICT Engine.

This is the glue between the ICT analysis engine and the existing
strategy agent pipeline.  It receives a MarketContext (which carries
raw candles), fetches HTF candles from the broker, runs the full ICT
pipeline, and returns a Signal compatible with StrategyAgent.
"""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime
from typing import Optional

from config import settings
from config.symbols import asset_class as _asset_class
from models.market_data import Candle, MarketContext
from models.signal import EntrySnapshot, Signal
from strategies.base_strategy import BaseStrategy
from strategies.ict.engine import ICTEngine
from utils.helpers import day_of_week

logger = logging.getLogger(__name__)


def _candle_volume_sufficient(candles: list, lookback: int = 20, threshold: float = 0.5) -> bool:
    """True if the most recent candle's volume >= threshold × average of last `lookback` candles.

    MT5 tick volume (symbol_info_tick().volume) is often 0 for non-exchange instruments
    and cannot be used as a volume confirmation.  Candle volume (from get_rates_from_pos)
    is the tick count per bar and is always populated — this is the correct source.
    """
    if not candles or len(candles) < 2:
        return False
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    avg = sum(c.volume for c in recent[:-1]) / max(1, len(recent) - 1)
    return avg > 0 and candles[-1].volume >= avg * threshold


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
        # Guard: broker is required for HTF candle fetching
        if self._broker is None:
            logger.warning("ICTStrategy: broker is None — cannot fetch HTF candles, skipping %s", ctx.symbol)
            return None

        # Crypto lacks forex killzones so the session score is capped lower.
        # Use a reduced minimum-confidence threshold to avoid filtering good setups.
        _is_crypto = _asset_class(ctx.symbol) == "crypto"
        _orig_min = self._engine.min_confidence
        if _is_crypto:
            self._engine.min_confidence = settings.MIN_ICT_SCORE_CRYPTO
        try:
            return self._detect_crypto_inner(ctx, _is_crypto)
        finally:
            if _is_crypto:
                self._engine.min_confidence = _orig_min

    def _detect_crypto_inner(self, ctx: MarketContext, _is_crypto: bool) -> Optional[Signal]:
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
                _thresh = self._engine.range_min_confidence if _is_range else (
                    settings.MIN_ICT_SCORE_CRYPTO if _is_crypto else self._engine.min_confidence
                )
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
            try:
                db_conf = self._db.get_confidence(model_slug)
                if db_conf is not None:
                    historical_conf = db_conf
            except Exception:
                logger.warning(
                    "ICTStrategy: confidence lookup failed for %s — using fallback %.2f",
                    model_slug,
                    historical_conf,
                    exc_info=True,
                )
                self._emit(
                    "warn",
                    (
                        f"ICT confidence lookup failed for {model_slug}; "
                        f"using fallback {historical_conf:.2f}"
                    ),
                    {"model": model_slug, "fallback_confidence": historical_conf},
                )
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
            volume_sufficient=_candle_volume_sufficient(ctx.candles),
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

        # ── Pillar 3: Entry precision ────────────────────────────────
        # Snap the entry price to the zone midpoint (FVG CE or OB midpoint).
        # If price has already moved past it by more than the staleness threshold,
        # the edge is gone — skip the signal.
        entry_price, skipped = self._precision_entry(
            best, ctx.current_price, ctx.atr,
        )
        if skipped:
            self._emit(
                "info",
                f"ICT {ctx.symbol} {best.direction}: entry STALE — price "
                f"{ctx.current_price:.5f} already {skipped:.1f}× ATR past zone midpoint "
                f"({entry_price:.5f}) — signal skipped",
            )
            return None

        # ── Pillar 4: TP4 runner + structural breakeven ──────────────
        tp4 = self._compute_tp4(best.direction, ict_ctx)
        structural_be = self._compute_structural_be(best.direction, entry_price, ict_ctx)

        if tp4 > 0:
            confluences.append(f"TP4={tp4:.5f}")
        if structural_be > 0:
            confluences.append(f"struct_BE={structural_be:.5f}")

        signal = Signal(
            strategy=model_slug,  # Tell TradeManager exactly which model this is!
            symbol=ctx.symbol,
            direction=best.direction,
            entry_price=entry_price,
            stop_loss=best.stop_loss,
            take_profit_1=best.take_profit_1,
            take_profit_2=best.take_profit_2,
            take_profit_3=best.take_profit_3,
            take_profit_4=tp4,
            structural_be=structural_be,
            confidence=final_conf,  # normalized to 0.0 - 1.0
            timestamp=datetime.now(UTC),
            reason=reason,
            entry_snapshot=snapshot,
        )

        if not self._is_signal_geometry_valid(signal):
            self._emit(
                "warn",
                (
                    f"ICT {ctx.symbol}: invalid signal geometry "
                    f"({signal.direction} entry={signal.entry_price:.5f} "
                    f"sl={signal.stop_loss:.5f} tp1={signal.take_profit_1:.5f}) — skipped"
                ),
            )
            return None

        # Persist setup to DB for dashboard analytics
        self._log_setup(best, ict_ctx)

        return signal

    # ── Pillar 3 helpers ─────────────────────────────────────────────

    def _precision_entry(
        self,
        best,
        current_price: float,
        atr: float,
    ) -> tuple[float, float]:
        """Return (snapped_entry, staleness_ratio).

        Snaps entry to FVG CE or OB midpoint (whichever is most precise).
        Returns staleness_ratio > 0 if price has already moved past the
        snapped level by more than LIMIT_ENTRY_MAX_DISTANCE_ATR × ATR.
        A staleness_ratio of 0 means the entry is still valid.
        """

        snapped = best.entry_price  # fallback: keep engine's value

        # Prefer OB midpoint → FVG CE (OB is more precise)
        if best.ob is not None:
            snapped = round(best.ob.mean_threshold, 5)
        elif best.fvg is not None:
            snapped = round(best.fvg.ce, 5)

        # Check staleness: has price already blown past the entry zone?
        # Crypto and high-value instruments (BTCUSD, XAUUSD) have ATR >> 10
        # in price terms; use a wider multiplier so we don't reject every setup.
        if atr > 0:
            _multiplier = (
                settings.LIMIT_ENTRY_MAX_DISTANCE_ATR_CRYPTO
                if atr > 10.0
                else settings.LIMIT_ENTRY_MAX_DISTANCE_ATR
            )
            max_dist = _multiplier * atr
            if best.direction == "BUY":
                # For a BUY, entry should be at or below current price (price
                # retraced into the zone).  Stale if price has already moved
                # MORE than max_dist ABOVE the snapped entry (missed the zone).
                overshoot = current_price - snapped
            else:
                # For a SELL, stale if price is more than max_dist BELOW snapped entry.
                overshoot = snapped - current_price

            if overshoot > max_dist:
                return snapped, round(overshoot / atr, 2)

        return snapped, 0.0

    # ── Pillar 4 helpers ─────────────────────────────────────────────

    def _compute_tp4(self, direction: str, ict_ctx) -> float:
        """Return the nearest HTF liquidity level as the TP4 runner target.

        BUY  → nearest buy-side liquidity (BSL) above current price.
        SELL → nearest sell-side liquidity (SSL) below current price.
        Returns 0.0 if no suitable level is found.
        """
        current = ict_ctx.current_price

        if direction == "BUY":
            candidates = [
                lvl.price for lvl in ict_ctx.bsl_levels
                if lvl.price > current and not lvl.swept
            ]
            if candidates:
                return round(min(candidates), 5)
            # Fallback: HTF OB top as liquidity proxy
            htf_targets = [
                ob.high for ob in ict_ctx.htf_obs
                if ob.high > current and ob.valid and not ob.mitigated
            ]
            if htf_targets:
                return round(min(htf_targets), 5)
        else:
            candidates = [
                lvl.price for lvl in ict_ctx.ssl_levels
                if lvl.price < current and not lvl.swept
            ]
            if candidates:
                return round(max(candidates), 5)
            htf_targets = [
                ob.low for ob in ict_ctx.htf_obs
                if ob.low < current and ob.valid and not ob.mitigated
            ]
            if htf_targets:
                return round(max(htf_targets), 5)

        return 0.0

    def _compute_structural_be(
        self,
        direction: str,
        entry_price: float,
        ict_ctx,
    ) -> float:
        """Return the nearest structural swing level to use as breakeven.

        BUY  → most recent swing LOW below entry (protecting the leg base).
        SELL → most recent swing HIGH above entry.
        Returns 0.0 if no qualifying swing is found.
        """
        if direction == "BUY":
            # Most recent swing low that sits below the entry price
            candidates = [
                sp.price for sp in ict_ctx.swing_lows
                if sp.price < entry_price and not sp.broken
            ]
            if candidates:
                return round(max(candidates), 5)  # nearest below entry
        else:
            candidates = [
                sp.price for sp in ict_ctx.swing_highs
                if sp.price > entry_price and not sp.broken
            ]
            if candidates:
                return round(min(candidates), 5)  # nearest above entry

        return 0.0

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

    def _is_signal_geometry_valid(self, signal: Signal) -> bool:
        """Validate basic directional geometry for SL/TP levels."""
        direction = signal.direction.upper().strip()
        entry = signal.entry_price
        sl = signal.stop_loss
        tp1 = signal.take_profit_1
        tp2 = signal.take_profit_2
        tp3 = signal.take_profit_3
        tp4 = signal.take_profit_4

        if direction not in {"BUY", "SELL"}:
            return False
        for value in (entry, sl, tp1):
            if value <= 0 or not math.isfinite(value):
                return False

        if direction == "BUY":
            if sl >= entry or tp1 <= entry:
                return False
            if tp2 > 0 and tp2 < tp1:
                return False
            if tp3 > 0 and tp2 > 0 and tp3 < tp2:
                return False
            if tp4 > 0 and tp3 > 0 and tp4 < tp3:
                return False
            return True

        if sl <= entry or tp1 >= entry:
            return False
        if tp2 > 0 and tp2 > tp1:
            return False
        if tp3 > 0 and tp2 > 0 and tp3 > tp2:
            return False
        if tp4 > 0 and tp3 > 0 and tp4 > tp3:
            return False
        return True
