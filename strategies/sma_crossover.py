"""Simple SMA crossover strategy for V1.

Generates a BUY when the fast SMA crosses above the slow SMA and a SELL
when it crosses below.  SL is set at 1× ATR from entry; TPs at 1×, 2×,
and 3× risk (RR 1:1 / 1:2 / 1:3).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Optional

from config import settings
from models.market_data import MarketContext
from models.signal import EntrySnapshot, Signal
from strategies.base_strategy import BaseStrategy
from utils.helpers import current_session, day_of_week

logger = logging.getLogger(__name__)


class SmaCrossoverStrategy(BaseStrategy):
    name = "sma_crossover"

    def detect(self, context: MarketContext) -> Optional[Signal]:
        try:
            return self._detect_inner(context)
        except Exception:
            logger.exception("SmaCrossover.detect failed")
            return None

    def _detect_inner(self, ctx: MarketContext) -> Optional[Signal]:
        # Need enough candles to compute indicators
        if len(ctx.candles) < 2:
            return None
        # Need valid SMA values
        if ctx.sma_fast == 0 or ctx.sma_slow == 0:
            return None
        if ctx.atr <= 0:
            return None

        # Determine crossover direction from last two candle closes
        prev_fast = ctx.candles[-2].close
        prev_slow = ctx.sma_slow  # simplified — use current slow as proxy
        cur_fast = ctx.sma_fast
        cur_slow = ctx.sma_slow

        direction: str | None = None
        if cur_fast > cur_slow and prev_fast <= prev_slow:
            direction = "BUY"
        elif cur_fast < cur_slow and prev_fast >= prev_slow:
            direction = "SELL"

        if direction is None:
            return None

        entry = ctx.current_price
        sl = self.calculate_sl(ctx, direction)
        tp1, tp2, tp3 = self.calculate_tps(ctx, entry, sl, direction)

        snapshot = EntrySnapshot(
            spread=ctx.spread,
            rsi_aligned=(direction == "BUY" and ctx.rsi < 70) or (direction == "SELL" and ctx.rsi > 30),
            trend_aligned=(direction == "BUY" and ctx.trend_direction == "bullish")
                          or (direction == "SELL" and ctx.trend_direction == "bearish"),
            volume_sufficient=ctx.volume > 0,
            near_news_event=ctx.near_news_event,
            market_condition=ctx.regime,
            session=current_session(),
            day_of_week=day_of_week(),
        )

        return Signal(
            strategy=self.name,
            symbol=ctx.symbol,
            direction=direction,
            entry_price=entry,
            stop_loss=sl,
            take_profit_1=tp1,
            take_profit_2=tp2,
            take_profit_3=tp3,
            confidence=settings.DEFAULT_CONFIDENCE,
            timestamp=datetime.now(UTC),
            reason=f"SMA crossover: fast({ctx.sma_fast:.5f}) {'above' if direction == 'BUY' else 'below'} slow({ctx.sma_slow:.5f})",
            entry_snapshot=snapshot,
        )

    def calculate_sl(self, ctx: MarketContext, direction: str) -> float:
        risk = ctx.atr  # 1× ATR
        if direction == "BUY":
            return round(ctx.current_price - risk, 5)
        return round(ctx.current_price + risk, 5)

    def calculate_tps(
        self, ctx: MarketContext, entry: float, sl: float, direction: str
    ) -> tuple[float, float, float]:
        risk = abs(entry - sl)
        if direction == "BUY":
            return (
                round(entry + risk, 5),
                round(entry + risk * 2, 5),
                round(entry + risk * 3, 5),
            )
        return (
            round(entry - risk, 5),
            round(entry - risk * 2, 5),
            round(entry - risk * 3, 5),
        )
