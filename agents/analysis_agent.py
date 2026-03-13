"""Analysis Agent — interprets raw market data into context.

Answers: *What does it mean?*
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from filters.news_filter import NewsFilter
from models.market_data import MarketContext, MarketData
from utils.helpers import current_session, day_of_week

if TYPE_CHECKING:
    from database.db import Database

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """Computes technical indicators and market regime from raw data."""

    def __init__(self, news_filter: NewsFilter | None = None, db: Database | None = None) -> None:
        self._news = news_filter or NewsFilter()
        self._db = db

    def analyze(self, data: MarketData) -> MarketContext:
        try:
            ctx = self._analyze_inner(data)
            self._emit("info",
                       f"Crunching {data.symbol} — regime={ctx.regime} trend={ctx.trend_direction} "
                       f"RSI={ctx.rsi:.1f} ATR={ctx.atr:.5f}",
                       {"regime": ctx.regime, "trend": ctx.trend_direction,
                        "rsi": ctx.rsi, "atr": ctx.atr})
            return ctx
        except Exception:
            logger.exception("AnalysisAgent.analyze failed")
            self._emit("error", f"Failed to analyze {data.symbol} — returning defaults")
            return MarketContext(symbol=data.symbol, current_price=data.mid_price)

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("analysis", level, msg, data)

    def _analyze_inner(self, data: MarketData) -> MarketContext:
        closes = [c.close for c in data.candles] if data.candles else []
        volumes = [c.volume for c in data.candles] if data.candles else []

        sma_fast = self._sma(closes, 10)
        sma_slow = self._sma(closes, 50)
        rsi = self._rsi(closes, 14)
        atr = self._atr(data.candles, 14) if data.candles else 0.0

        # Regime
        if atr > 0 and len(closes) > 1:
            recent_range = max(closes[-14:]) - min(closes[-14:]) if len(closes) >= 14 else 0
            if recent_range > atr * 3:
                regime = "volatile"
            elif sma_fast != 0 and sma_slow != 0 and abs(sma_fast - sma_slow) > atr:
                regime = "trending"
            else:
                regime = "ranging"
        else:
            regime = "unknown"

        if sma_fast > sma_slow:
            trend = "bullish"
        elif sma_fast < sma_slow:
            trend = "bearish"
        else:
            trend = "neutral"

        near_news = self._news.is_blackout(data.symbol)

        return MarketContext(
            symbol=data.symbol,
            current_price=data.mid_price,
            bid=data.bid,
            ask=data.ask,
            spread=data.spread,
            volume=data.volume,
            timestamp=data.timestamp,
            sma_fast=sma_fast,
            sma_slow=sma_slow,
            rsi=rsi,
            atr=atr,
            regime=regime,
            trend_direction=trend,
            session=current_session(),
            day_of_week=day_of_week(),
            near_news_event=near_news,
            candles=data.candles,
        )

    # ── indicator helpers ────────────────────────────────────────────────

    @staticmethod
    def _sma(values: list[float], period: int) -> float:
        if len(values) < period:
            return 0.0
        return round(sum(values[-period:]) / period, 5)

    @staticmethod
    def _rsi(closes: list[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        recent = deltas[-period:]
        gains = [d for d in recent if d > 0]
        losses = [-d for d in recent if d < 0]
        avg_gain = sum(gains) / period if gains else 0.0
        avg_loss = sum(losses) / period if losses else 0.0001
        rs = avg_gain / avg_loss
        return round(100 - 100 / (1 + rs), 2)

    @staticmethod
    def _atr(candles: list, period: int = 14) -> float:
        if len(candles) < period + 1:
            return 0.0
        trs: list[float] = []
        for i in range(1, len(candles)):
            h = candles[i].high
            l = candles[i].low
            pc = candles[i - 1].close
            trs.append(max(h - l, abs(h - pc), abs(l - pc)))
        recent = trs[-period:]
        return round(sum(recent) / len(recent), 5) if recent else 0.0
