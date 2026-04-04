"""Neural LSTM Strategy — primary signal generator.

Replaces ICT + SMA crossover as the signal source.  The existing Council
(ICT expert, DanialFX expert, Traditional expert) stays active and acts as
a confirmation layer for every neural signal.

Flow
----
NeuralStrategy.detect(context)
  ├─ model_manager.predict(symbol, candles, context)   ← LSTM inference
  │     → (direction, confidence) or None
  ├─ if None or confidence < threshold  → return None
  └─ build Signal with SL=2×ATR, TP1/2/3 from 1R/2R/3R
        → Council confirms (in main.py pipeline — unchanged)
        → Risk validates
        → Execution opens trade
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from config import settings
from models.market_data import MarketContext
from models.signal import EntrySnapshot, Signal
from strategies.base_strategy import BaseStrategy

if TYPE_CHECKING:
    from agents.model_manager import ModelManager

logger = logging.getLogger(__name__)


def _candle_volume_sufficient(candles: list, lookback: int = 20, threshold: float = 0.5) -> bool:
    if not candles or len(candles) < 2:
        return False
    recent = candles[-lookback:] if len(candles) >= lookback else candles
    avg = sum(c.volume for c in recent[:-1]) / max(1, len(recent) - 1)
    return avg > 0 and candles[-1].volume >= avg * threshold


class NeuralStrategy(BaseStrategy):
    """LSTM-based strategy.  Generates BUY/SELL signals from candle sequences."""

    name = "neural_lstm"

    def __init__(self, model_manager: "ModelManager") -> None:
        self._mm = model_manager

    # ── BaseStrategy interface ────────────────────────────────────────────

    def detect(self, context: MarketContext) -> Optional[Signal]:
        if not context.candles or len(context.candles) < settings.NEURAL_MIN_CANDLES:
            return None

        result = self._mm.predict(context.symbol, context.candles, context)
        if result is None:
            return None

        direction, confidence = result

        # ── MTF D1 veto: veto only when BOTH D1 and H4 oppose the signal ──
        # A solo D1 opposition is a regime context issue (ICT trades against
        # D1 all the time — selling into premium, buying at discount).
        # Only veto when the two higher timeframes agree against the trade.
        if settings.MTF_D1_VETO:
            d1 = getattr(context, "d1_trend", "neutral")
            h4 = getattr(context, "h4_trend", "neutral")
            d1_against = (direction == "BUY" and d1 == "bearish") or \
                         (direction == "SELL" and d1 == "bullish")
            h4_against = (direction == "BUY" and h4 == "bearish") or \
                         (direction == "SELL" and h4 == "bullish")
            if d1_against and h4_against:
                logger.info(
                    "[neural] %s %s vetoed — D1 (%s) + H4 (%s) both contradict signal",
                    direction, context.symbol, d1, h4,
                )
                return None
            if d1_against:
                # Solo D1 opposition: penalise confidence instead of vetoing
                confidence -= 0.06
                logger.debug(
                    "[neural] %s %s D1 (%s) opposes — confidence -0.06 (H4=%s supports)",
                    direction, context.symbol, d1, h4,
                )

        # ── MTF alignment boost/penalty ───────────────────────────────────
        mtf_bias      = getattr(context, "mtf_bias",      "unknown")
        mtf_alignment = getattr(context, "mtf_alignment", 0.0)
        aligned = (mtf_bias == "aligned_bull" and direction == "BUY") or \
                  (mtf_bias == "aligned_bear" and direction == "SELL")
        if aligned:
            confidence += settings.MTF_ALIGNMENT_BOOST * mtf_alignment
        elif mtf_bias == "mixed":
            confidence -= settings.MTF_ALIGNMENT_BOOST  # slight penalty for choppy stack

        # ── Regime confidence penalty — ranging markets are noisier ──────
        if context.regime == "ranging":
            confidence -= settings.REGIME_CONFIDENCE_PENALTY

        # Sanitise confidence into the [0.5, 1.0] range used by risk/sizing
        confidence = max(0.50, min(1.0, confidence))

        entry = context.current_price
        sl    = self.calculate_sl(context, direction)
        if sl == 0.0:
            return None

        tp1, tp2, tp3 = self.calculate_tps(context, entry, sl, direction)

        rsi         = context.rsi or 50.0
        rsi_aligned = (40 <= rsi <= 70) if direction == "BUY" else (30 <= rsi <= 60)

        snap = EntrySnapshot(
            spread=context.spread,
            rsi_aligned=rsi_aligned,
            trend_aligned=(context.trend_direction == "bullish" and direction == "BUY")
                        or (context.trend_direction == "bearish" and direction == "SELL"),
            volume_sufficient=_candle_volume_sufficient(context.candles),
            near_news_event=context.near_news_event,
            market_condition=context.regime,
            session=context.session,
            day_of_week=context.day_of_week,
        )

        logger.info(
            "[neural] Signal: %s %s conf=%.1f%% entry=%.5f sl=%.5f mtf=%s(%.0f%%)",
            direction, context.symbol, confidence * 100, entry, sl,
            getattr(context, "mtf_bias", "?"), mtf_alignment * 100,
        )

        return Signal(
            strategy=self.name,
            symbol=context.symbol,
            direction=direction,
            entry_price=entry,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            confidence=confidence,
            timestamp=datetime.now(UTC),
            reason=f"LSTM {direction} {confidence:.1%} — Council confirmation pending",
            entry_snapshot=snap,
        )

    def calculate_sl(self, context: MarketContext, direction: str) -> float:
        atr = context.atr or 0.0
        if atr <= 0:
            return 0.0
        sl_dist = 2.0 * atr
        if direction == "BUY":
            return round(context.current_price - sl_dist, 5)
        return round(context.current_price + sl_dist, 5)

    def calculate_tps(
        self,
        context: MarketContext,
        entry: float,
        sl: float,
        direction: str,
    ) -> tuple[float, float, float]:
        risk = abs(entry - sl)
        regime = getattr(context, "regime", "unknown")

        if regime == "ranging":
            mult1 = settings.TP_RANGING_TP1_MULT   # 0.8R
            mult2 = settings.TP_RANGING_TP2_MULT   # 1.5R
            mult3 = 2.0
        elif regime == "trending":
            mult1 = 1.0
            mult2 = 2.0
            mult3 = settings.TP_TRENDING_TP3_MULT  # 4.0R
        else:
            mult1, mult2, mult3 = 1.0, 2.0, 3.0

        if direction == "BUY":
            return (
                round(entry + mult1 * risk, 5),
                round(entry + mult2 * risk, 5),
                round(entry + mult3 * risk, 5),
            )
        return (
            round(entry - mult1 * risk, 5),
            round(entry - mult2 * risk, 5),
            round(entry - mult3 * risk, 5),
        )
