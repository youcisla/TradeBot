"""Analysis Agent — interprets raw market data into context.

Answers: *What does it mean?*
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from config import settings
from models.garch_regime import GarchRegimeDetector
from models.market_data import MarketContext, MarketData
from utils.helpers import current_session, day_of_week
from utils.kalman_filter import KalmanPriceFilter
from utils.mesh_bus import mesh_span

if TYPE_CHECKING:
    from agents.crucix_agent import CrucixAgent
    from adapters.db.db import Database

logger = logging.getLogger(__name__)


class AnalysisAgent:
    """Computes technical indicators and market regime from raw data."""

    def __init__(self, crucix_agent: "CrucixAgent | None" = None, db: "Database | None" = None) -> None:
        self._crucix = crucix_agent
        self._db = db
        # Per-symbol stateful filters (persist across ticks)
        self._garch: dict[str, GarchRegimeDetector] = {}
        self._kalman: dict[str, KalmanPriceFilter] = {}

    def analyze(self, data: MarketData) -> MarketContext:
        try:
            with mesh_span("analysis"):
                ctx = self._analyze_inner(data)
            self._emit("info",
                       f"Crunching {data.symbol} — regime={ctx.regime} trend={ctx.trend_direction} "
                       f"RSI={ctx.rsi:.1f} ATR={ctx.atr:.5f} "
                       f"MTF bias={ctx.mtf_bias} align={ctx.mtf_alignment:.0%} "
                       f"[D1={ctx.d1_trend} H4={ctx.h4_trend} H1={ctx.trend_direction} M30={ctx.m30_trend}] "
                       f"session={ctx.session} news_blackout={ctx.near_news_event}",
                       {"regime": ctx.regime, "trend": ctx.trend_direction,
                        "rsi": ctx.rsi, "atr": ctx.atr,
                        "mtf_bias": ctx.mtf_bias, "mtf_alignment": ctx.mtf_alignment,
                        "d1_trend": ctx.d1_trend, "h4_trend": ctx.h4_trend,
                        "m30_trend": ctx.m30_trend,
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

        # ── Kalman price filter (smooths microstructure noise) ─────────────────
        kf = self._kalman.setdefault(data.symbol, KalmanPriceFilter(symbol=data.symbol))
        kalman_price = kf.update(data.mid_price)
        kalman_velocity = kf.velocity

        # ── GARCH volatility regime ────────────────────────────────────────
        garch = self._garch.setdefault(data.symbol, GarchRegimeDetector(symbol=data.symbol))
        if len(closes) >= 2:
            garch.update_price(closes[-1], closes[-2])
        garch_regime = garch.regime
        garch_vol = garch.conditional_vol

        # ── H1 indicators (primary analysis timeframe) ───────────────────
        sma_fast = self._sma(closes, settings.SMA_FAST_PERIOD)
        sma_slow = self._sma(closes, settings.SMA_SLOW_PERIOD)
        prev_sma_fast = self._sma(closes[:-1], settings.SMA_FAST_PERIOD) if len(closes) > settings.SMA_FAST_PERIOD else 0.0
        prev_sma_slow = self._sma(closes[:-1], settings.SMA_SLOW_PERIOD) if len(closes) > settings.SMA_SLOW_PERIOD else 0.0
        rsi = self._rsi(closes, 14)
        atr = self._atr(data.candles, 14) if data.candles else 0.0
        adx = self._adx(data.candles, 14) if len(data.candles) >= 28 else 0.0

        # ADX-based regime
        if atr > 0 and len(closes) > 1:
            recent_range = max(closes[-14:]) - min(closes[-14:]) if len(closes) >= 14 else 0
            if recent_range > atr * 3:
                regime = "volatile"
            elif adx >= settings.REGIME_ADX_TRENDING:
                regime = "trending"
            elif adx <= settings.REGIME_ADX_RANGING:
                regime = "ranging"
            else:
                regime = "trending" if (sma_fast != 0 and sma_slow != 0
                                        and abs(sma_fast - sma_slow) > atr) else "ranging"
        else:
            regime = "unknown"

        # GARCH overrides ADX volatile detection when enabled and model has warmed up
        if settings.GARCH_ENABLED and garch.is_high_vol and regime != "volatile":
            regime = "volatile"

        h1_trend = self._tf_trend(closes, settings.SMA_FAST_PERIOD, settings.SMA_SLOW_PERIOD)

        # ── Per-timeframe trend (analysis stack: M30, H4, D1) ────────────
        m30_trend = self._tf_trend_candles(data.m30_candles)
        h4_trend  = self._tf_trend_candles(data.h4_candles)
        d1_trend  = self._tf_trend_candles(data.d1_candles)

        # ── MTF alignment: how many analysis TFs agree with H1 ───────────
        analysis_tfs = [m30_trend, h1_trend, h4_trend, d1_trend]
        bull_count = sum(1 for t in analysis_tfs if t == "bullish")
        bear_count = sum(1 for t in analysis_tfs if t == "bearish")
        known = [t for t in analysis_tfs if t != "neutral"]

        if len(known) == 0:
            mtf_bias      = "unknown"
            mtf_alignment = 0.0
        elif bull_count > bear_count:
            mtf_alignment = bull_count / len(known)
            mtf_bias      = "aligned_bull" if bull_count >= 3 else "mixed"
        elif bear_count > bull_count:
            mtf_alignment = bear_count / len(known)
            mtf_bias      = "aligned_bear" if bear_count >= 3 else "mixed"
        else:
            mtf_bias      = "mixed"
            mtf_alignment = 0.5

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
            adx=adx,
            regime=regime,
            trend_direction=h1_trend,
            session=current_session(),
            day_of_week=day_of_week(),
            near_news_event=near_news,
            candles=data.candles,
            m30_candles=data.m30_candles,
            m15_candles=data.m15_candles,
            m5_candles=data.m5_candles,
            h4_candles=data.h4_candles,
            d1_candles=data.d1_candles,
            m30_trend=m30_trend,
            h4_trend=h4_trend,
            d1_trend=d1_trend,
            mtf_alignment=mtf_alignment,
            mtf_bias=mtf_bias,
            shock_detected=data.shock_detected,
            tick_drop_pct=data.tick_drop_pct,
            tick_drop_window_seconds=data.tick_drop_window_seconds,
            garch_regime=garch_regime,
            garch_vol=garch_vol,
            kalman_price=kalman_price,
            kalman_velocity=kalman_velocity,
        )

        if self._crucix:
            ctx.macro = self._crucix.get_context()

        return ctx

    # ── indicator helpers ────────────────────────────────────────────────

    @staticmethod
    def _tf_trend(closes: list[float], fast: int, slow: int) -> str:
        """SMA crossover trend direction from a close price list."""
        if len(closes) < slow:
            return "neutral"
        sma_f = sum(closes[-fast:]) / fast
        sma_s = sum(closes[-slow:]) / slow
        if sma_f > sma_s:
            return "bullish"
        if sma_f < sma_s:
            return "bearish"
        return "neutral"

    @classmethod
    def _tf_trend_candles(cls, candles: list, fast: int = 10, slow: int = 50) -> str:
        """Compute SMA crossover trend from a candle list (any timeframe)."""
        if not candles or len(candles) < slow:
            return "neutral"
        closes = [c.close for c in candles]
        return cls._tf_trend(closes, fast, slow)

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
            lo = candles[i].low
            pc = candles[i - 1].close
            trs.append(max(h - lo, abs(h - pc), abs(lo - pc)))
        recent = trs[-period:]
        return round(sum(recent) / len(recent), 5) if recent else 0.0

    @staticmethod
    def _adx(candles: list, period: int = 14) -> float:
        """Wilder-smoothed ADX.  Requires at least 2*period candles."""
        if len(candles) < period * 2:
            return 0.0
        plus_dm: list[float] = []
        minus_dm: list[float] = []
        trs: list[float] = []
        for i in range(1, len(candles)):
            h, lo, pc = candles[i].high, candles[i].low, candles[i - 1].close
            ph, pl = candles[i - 1].high, candles[i - 1].low
            up = h - ph
            down = pl - lo
            plus_dm.append(up if up > down and up > 0 else 0.0)
            minus_dm.append(down if down > up and down > 0 else 0.0)
            trs.append(max(h - lo, abs(h - pc), abs(lo - pc)))

        def wilder_smooth(values: list[float], n: int) -> list[float]:
            smoothed = [sum(values[:n])]
            for v in values[n:]:
                smoothed.append(smoothed[-1] - smoothed[-1] / n + v)
            return smoothed

        atr_s = wilder_smooth(trs, period)
        pdm_s = wilder_smooth(plus_dm, period)
        mdm_s = wilder_smooth(minus_dm, period)

        dx_vals: list[float] = []
        for atr_v, pdm_v, mdm_v in zip(atr_s, pdm_s, mdm_s):
            if atr_v == 0:
                continue
            pdi = 100 * pdm_v / atr_v
            mdi = 100 * mdm_v / atr_v
            denom = pdi + mdi
            dx_vals.append(100 * abs(pdi - mdi) / denom if denom else 0.0)

        if len(dx_vals) < period:
            return 0.0
        adx = sum(dx_vals[-period:]) / period
        return round(adx, 2)
