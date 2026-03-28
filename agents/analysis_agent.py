"""Analysis Agent — interprets raw market data into context.

Answers: *What does it mean?*
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from config import settings
from models.market_data import MarketContext, MarketData
from utils.helpers import current_session, day_of_week

if TYPE_CHECKING:
    from agents.crucix_agent import CrucixAgent
    from database.db import Database

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """Computes technical indicators and market regime from raw data."""

    def __init__(self, crucix_agent: "CrucixAgent | None" = None, db: "Database | None" = None) -> None:
        self._crucix = crucix_agent
        self._db = db

    def analyze(self, data: MarketData) -> MarketContext:
        try:
            ctx = self._analyze_inner(data)
            self._emit("info",
                       f"Crunching {data.symbol} — regime={ctx.regime} trend={ctx.trend_direction} "
                       f"RSI={ctx.rsi:.1f} ATR={ctx.atr:.5f} "
                       f"SMA_fast={ctx.sma_fast:.5f} SMA_slow={ctx.sma_slow:.5f} "
                       f"prev_fast={ctx.prev_sma_fast:.5f} prev_slow={ctx.prev_sma_slow:.5f} "
                       f"session={ctx.session} news_blackout={ctx.near_news_event}",
                       {"regime": ctx.regime, "trend": ctx.trend_direction,
                        "rsi": ctx.rsi, "atr": ctx.atr,
                        "sma_fast": ctx.sma_fast, "sma_slow": ctx.sma_slow,
                        "prev_sma_fast": ctx.prev_sma_fast, "prev_sma_slow": ctx.prev_sma_slow,
                        "session": ctx.session, "day": ctx.day_of_week,
                        "near_news": ctx.near_news_event,
                        "price": ctx.current_price, "spread": ctx.spread})
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

        sma_fast = self._sma(closes, settings.SMA_FAST_PERIOD)
        sma_slow = self._sma(closes, settings.SMA_SLOW_PERIOD)
        prev_sma_fast = self._sma(closes[:-1], settings.SMA_FAST_PERIOD) if len(closes) > settings.SMA_FAST_PERIOD else 0.0
        prev_sma_slow = self._sma(closes[:-1], settings.SMA_SLOW_PERIOD) if len(closes) > settings.SMA_SLOW_PERIOD else 0.0
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

        near_news = self._crucix.is_blackout(data.symbol) if self._crucix else False

        ctx = MarketContext(
            symbol=data.symbol,
            current_price=data.mid_price,
            bid=data.bid,
            ask=data.ask,
            spread=data.spread,
            volume=data.volume,
            timestamp=data.timestamp,
            sma_fast=sma_fast,
            sma_slow=sma_slow,
            prev_sma_fast=prev_sma_fast,
            prev_sma_slow=prev_sma_slow,
            rsi=rsi,
            atr=atr,
            regime=regime,
            trend_direction=trend,
            session=current_session(),
            day_of_week=day_of_week(),
            near_news_event=near_news,
            candles=data.candles,
        )

        # Enrich with world context from Crucix (fails safely if not running)
        if self._crucix:
            ctx.macro = self._crucix.get_context()

        return ctx

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
        if not gains and not losses:
            return 50.0  # flat market — no movement in either direction
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
