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
            volume_sufficient=context.volume > 0,
            near_news_event=context.near_news_event,
            market_condition=context.regime,
            session=context.session,
            day_of_week=context.day_of_week,
        )

        logger.info(
            "[neural] Signal: %s %s conf=%.1f%% entry=%.5f sl=%.5f",
            direction, context.symbol, confidence * 100, entry, sl,
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
        if direction == "BUY":
            return (
                round(entry + 1.0 * risk, 5),
                round(entry + 2.0 * risk, 5),
                round(entry + 3.0 * risk, 5),
            )
        return (
            round(entry - 1.0 * risk, 5),
            round(entry - 2.0 * risk, 5),
            round(entry - 3.0 * risk, 5),
        )
