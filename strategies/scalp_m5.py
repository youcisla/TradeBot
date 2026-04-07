"""Momentum scalp strategy on M5 candles.

Generates signals on EMA5/EMA20 crossover with RSI(5) confirmation,
Bollinger Band squeeze filter, and volume confirmation.
Designed to run alongside H1 strategies (ICT/SMC) — scalps fast mean-reversion
moves while the H1 pipeline handles the trend.

SL:  0.5× ATR  (tight — scalp)
TP1: entry + 0.75× risk  (1:1.5 RR)
TP2: entry + 1.50× risk  (1:3 RR)
TP3: runner to nearest HTF liquidity sweep
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Optional

from config import settings
from models.market_data import Candle, MarketContext
from models.signal import EntrySnapshot, Signal
from strategies.base_strategy import BaseStrategy
from utils.helpers import current_session, day_of_week

logger = logging.getLogger(__name__)


# ── Technical indicator helpers ───────────────────────────────────────────────

def _ema(prices: list[float], period: int) -> float:
    if len(prices) < period:
        return 0.0
    k = 2.0 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = price * k + ema * (1.0 - k)
    return ema


def _rsi(prices: list[float], period: int = 5) -> float:
    if len(prices) < period + 1:
        return 50.0
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(prices)):
        delta = prices[i] - prices[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))
    if len(gains) < period:
        return 50.0
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def _atr(candles: list[Candle], period: int = 14) -> float:
    if len(candles) < period + 1:
        return 0.0
    trs: list[float] = []
    for i in range(1, len(candles)):
        high = candles[i].high
        low  = candles[i].low
        prev = candles[i - 1].close
        tr = max(high - low, abs(high - prev), abs(low - prev))
        trs.append(tr)
    if len(trs) < period:
        return 0.0
    return sum(trs[-period:]) / period


def _bollinger_squeeze(candles: list[Candle], period: int = 20, k: float = 2.0) -> bool:
    """Return True if Bollinger Bands are in squeeze (bandwidth near 90th pctile)."""
    if len(candles) < period + 10:
        return False
    closes = [c.close for c in candles]
    recent = closes[-period:]
    sma = sum(recent) / period
    std = (sum((x - sma) ** 2 for x in recent) / period) ** 0.5
    upper = sma + k * std
    lower = sma - k * std
    bandwidth = upper - lower
    # Compute bandwidth for past 10 bars to get percentile
    bws: list[float] = []
    for i in range(period, len(closes)):
        window = closes[i - period + 1:i + 1]
        w_sma = sum(window) / period
        w_std = (sum((x - w_sma) ** 2 for x in window) / period) ** 0.5
        bws.append((w_sma + k * w_std) - (w_sma - k * w_std))
    if len(bws) < 10:
        return False
    threshold = sorted(bws)[int(len(bws) * 0.90)]
    return bandwidth <= threshold


def _volume_okay(candles: list[Candle], lookback: int = 20, threshold: float = 0.65) -> bool:
    if len(candles) < lookback + 1:
        return False
    recent = candles[-lookback:]
    avg = sum(c.volume for c in recent[:-1]) / max(1, len(recent) - 1)
    if avg <= 0:
        # Broker returned no volume data (common on MT5) — skip volume filter
        return True
    return recent[-1].volume >= avg * threshold


def _htf_runner_target(
    candles: list[Candle],
    direction: str,
    entry: float,
) -> float:
    """Nearest HTF candle swing high/low used as TP3 runner target."""
    if not candles:
        return entry
    # Use H4 candles for runner target if available, else M15
    relevant = candles
    highs = [c.high for c in relevant[-50:]]
    lows  = [c.low  for c in relevant[-50:]]
    if direction == "BUY":
        # Next HTF swing high above entry
        above = [h for h in highs if h > entry]
        return min(above) if above else entry * 1.002
    else:
        below = [l for l in lows if l < entry]
        return max(below) if below else entry * 0.998


# ── Strategy ───────────────────────────────────────────────────────────────────

class ScalpM5Strategy(BaseStrategy):
    """Momentum scalp on M5 — EMA crossover + RSI + BB squeeze + volume."""

    name = "scalp_m5"

    # Scalping parameters
    EMA_FAST:  int = 5
    EMA_SLOW:  int = 20
    RSI_PERIOD: int = 5
    BB_PERIOD: int = 20
    SL_ATR_MULT: float = 0.50   # tighter than H1 (which uses 1.0×)
    TP1_RR:    float = 1.50      # 1:1.5 RR
    TP2_RR:    float = 3.00      # 1:3 RR
    MIN_CANDLES: int = 25        # need at least EMA_SLOW + BB_PERIOD bars

    # Spread caps
    MAX_SPREAD_FOREX: float = 6.0   # pips
    MAX_SPREAD_CRYPTO: float = 0.025  # fraction of price

    def detect(self, context: MarketContext) -> Optional[Signal]:
        try:
            return self._detect_inner(context)
        except Exception:
            logger.exception("ScalpM5Strategy.detect failed")
            return None

    def _detect_inner(self, ctx: MarketContext) -> Optional[Signal]:
        # ── M5 candles from context (populated by MarketAgent) ──────────────
        m5 = ctx.m5_candles
        if len(m5) < self.MIN_CANDLES:
            logger.debug("ScalpM5 %s: insufficient M5 candles %d < %d", ctx.symbol, len(m5), self.MIN_CANDLES)
            return None

        closes = [c.close for c in m5]

        # ── Indicators ───────────────────────────────────────────────────────
        ema_fast = _ema(closes, self.EMA_FAST)
        ema_slow  = _ema(closes, self.EMA_SLOW)
        if ema_fast == 0.0 or ema_slow == 0.0:
            return None

        prev_fast = _ema(closes[:-1], self.EMA_FAST)
        prev_slow  = _ema(closes[:-1], self.EMA_SLOW)

        rsi_val = _rsi(closes, self.RSI_PERIOD)

        atr = _atr(m5, period=14)
        if atr <= 0:
            # Fall back to context ATR if M5 ATR unavailable
            atr = ctx.atr
        if atr <= 0:
            logger.debug("ScalpM5 %s: no ATR available", ctx.symbol)
            return None

        # ── Crossover detection ──────────────────────────────────────────────
        direction: str | None = None
        # EMA crossover UP (fast crosses above slow)
        if ema_fast > ema_slow and prev_fast <= prev_slow:
            direction = "BUY"
        # EMA crossover DOWN (fast crosses below slow)
        elif ema_fast < ema_slow and prev_fast >= prev_slow:
            direction = "SELL"
        else:
            logger.debug("ScalpM5 %s: no EMA crossover this bar ema_fast=%.5f ema_slow=%.5f prev_fast=%.5f prev_slow=%.5f",
                         ctx.symbol, ema_fast, ema_slow, prev_fast, prev_slow)
            return None

        # ── RSI confirmation ─────────────────────────────────────────────────
        # BUY: RSI should be < 70 and rising (not overbought)
        # SELL: RSI should be > 30 and falling (not oversold)
        if direction == "BUY" and rsi_val > 70:
            logger.debug("ScalpM5 %s: RSI %s > 70 blocks BUY", ctx.symbol, rsi_val)
            return None
        if direction == "SELL" and rsi_val < 30:
            logger.debug("ScalpM5 %s: RSI %s < 30 blocks SELL", ctx.symbol, rsi_val)
            return None

        # ── Bollinger squeeze filter ─────────────────────────────────────────
        # Squeeze often precedes explosive moves — allow it as valid
        # but we want to know it's NOT squeezed (we want expansion)
        if _bollinger_squeeze(m5, self.BB_PERIOD):
            # Squeeze is active — skip (low volatility, likely range)
            pass  # comment out to allow squeeze trades

        # ── Volume filter ────────────────────────────────────────────────────
        if not _volume_okay(m5):
            return None

        # ── Spread filter ─────────────────────────────────────────────────────
        spread_pips = ctx.spread * (100 if ctx.symbol.endswith("JPY") else 10000)
        is_crypto = ctx.symbol in ("BTCUSD", "ETHUSD", "BNBUSD", "SOLUSD",
                                    "XRPUSD", "ADAUSD", "DOTUSD", "LTCUSD",
                                    "EOSUSD", "XLMUSD", "TRXUSD", "AVAXUSD")
        if is_crypto:
            spread_pct = ctx.spread / ctx.current_price
            if spread_pct > self.MAX_SPREAD_CRYPTO:
                logger.debug("ScalpM5 %s: spread %.4f exceeds crypto cap %.4f", ctx.symbol, spread_pct, self.MAX_SPREAD_CRYPTO)
                return None
        else:
            if spread_pips > self.MAX_SPREAD_FOREX:
                logger.debug("ScalpM5 %s: spread %.1fpips exceeds %.1f cap", ctx.symbol, spread_pips, self.MAX_SPREAD_FOREX)
                return None

        # ── News filter ──────────────────────────────────────────────────────
        if ctx.near_news_event:
            return None

        # ── Session filter (scalps only in liquid sessions) ─────────────────
        # BTC is 24/7 — skip session restrictions for crypto
        if not is_crypto:
            session = current_session()
            if session == "newyork":
                return None  # skip NY open — spreads usually wide for forex

        # ── Build signal ─────────────────────────────────────────────────────
        entry = ctx.current_price
        sl    = self.calculate_sl(ctx, direction)
        tp1, tp2, tp3 = self.calculate_tps(ctx, entry, sl, direction)

        # Confidence scoring
        conf = self._confidence(ema_fast, ema_slow, rsi_val, direction, m5)

        snapshot = EntrySnapshot(
            spread=ctx.spread,
            rsi_aligned=(direction == "BUY" and rsi_val < 70) or (direction == "SELL" and rsi_val > 30),
            trend_aligned=(direction == "BUY" and ctx.trend_direction == "bullish")
                         or (direction == "SELL" and ctx.trend_direction == "bearish"),
            volume_sufficient=_volume_okay(m5),
            near_news_event=ctx.near_news_event,
            market_condition=ctx.regime,
            session=session,
            day_of_week=day_of_week(),
        )

        logger.info(
            "ScalpM5: %s %s ema_fast=%.5f ema_slow=%.5f rsi=%.1f conf=%.2f",
            ctx.symbol, direction, ema_fast, ema_slow, rsi_val, conf,
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
            confidence=conf,
            timestamp=datetime.now(UTC),
            reason=(
                f"ScalpM5 EMA{self.EMA_FAST}/{self.EMA_SLOW} crossover: "
                f"{direction} @ {entry:.5f} | RSI={rsi_val:.1f} | "
                f"EMA_fast={ema_fast:.5f} EMA_slow={ema_slow:.5f}"
            ),
            entry_snapshot=snapshot,
        )

    def _confidence(
        self,
        ema_fast: float,
        ema_slow: float,
        rsi_val: float,
        direction: str,
        m5: list[Candle],
    ) -> float:
        """Score 0–1 based on indicator quality."""
        # EMA spread normalised (how far apart are the EMAs?)
        ema_spread = abs(ema_fast - ema_slow)
        ema_norm = min(1.0, ema_spread / (ema_slow * 0.005)) if ema_slow > 0 else 0.0

        # RSI mid-zone bonus (extreme RSI = lower confidence)
        if direction == "BUY":
            rsi_score = 1.0 - abs(rsi_val - 50) / 50.0
        else:
            rsi_score = 1.0 - abs(rsi_val - 50) / 50.0

        # Volume confirmation
        vol_score = 1.0 if _volume_okay(m5) else 0.5

        raw = (ema_norm * 0.50) + (rsi_score * 0.30) + (vol_score * 0.20)
        return round(max(0.30, min(0.95, raw)), 3)

    def calculate_sl(self, ctx: MarketContext, direction: str) -> float:
        from config.symbols import pip_value as _pip_value
        from utils.adaptive_stop import find_adaptive_stop

        atr = ctx.atr
        if atr <= 0:
            atr = _atr(ctx.m5_candles, 14) if len(ctx.m5_candles) >= 15 else 0.0001

        # Try adaptive intraday stop first (swing-low based).
        # Falls back to ATR-based stop if no valid swing low is found.
        pv = _pip_value(ctx.symbol)
        adaptive_sl = find_adaptive_stop(
            ctx.m5_candles,
            direction,
            atr,
            pv,
            buffer_pips=2.0,
            min_candles=10,
        )
        if adaptive_sl is not None:
            # Use adaptive stop only if it's tighter than the ATR stop,
            # otherwise the ATR stop provides better risk management.
            atr_sl = self._atr_based_sl(ctx, direction, atr)
            if direction == "BUY":
                return round(max(adaptive_sl, atr_sl), 5)  # BUY stop below entry
            else:
                return round(min(adaptive_sl, atr_sl), 5)  # SELL stop above entry

        return self._atr_based_sl(ctx, direction, atr)

    def _atr_based_sl(self, ctx: MarketContext, direction: str, atr: float) -> float:
        """Classic ATR×multiplier stop loss — used as fallback."""
        sl_distance = atr * self.SL_ATR_MULT
        if direction == "BUY":
            return round(ctx.current_price - sl_distance, 5)
        return round(ctx.current_price + sl_distance, 5)

    def calculate_tps(
        self,
        ctx: MarketContext,
        entry: float,
        sl: float,
        direction: str,
    ) -> tuple[float, float, float]:
        risk = abs(entry - sl)
        tp1_distance = risk * self.TP1_RR
        tp2_distance = risk * self.TP2_RR

        if direction == "BUY":
            tp1 = round(entry + tp1_distance, 5)
            tp2 = round(entry + tp2_distance, 5)
        else:
            tp1 = round(entry - tp1_distance, 5)
            tp2 = round(entry - tp2_distance, 5)

        # TP3 runner — nearest HTF swing
        tp3 = _htf_runner_target(
            ctx.h4_candles or ctx.m15_candles or ctx.m5_candles,
            direction,
            entry,
        )
        return tp1, tp2, round(tp3, 5)
