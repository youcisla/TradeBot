"""microstructure.py — order-flow and spread microstructure features.

Extracts leading indicators from raw tick or OHLCV data that are absent
from standard candlestick analysis:

    - Bid-ask spread (% of mid)
    - Trade imbalance proxy (close position within bar range)
    - Intrabar range expansion vs ATR (volatility spike flag)
    - Roll-adjusted signed volume (approximate Kyle's lambda)
    - Candle body ratio (body / range) — wicking pressure

All values are normalised to [0, 1] or [-1, 1] for downstream model use.

Usage::

    from features.microstructure import MicrostructureFeatures, OHLCV

    feat = MicrostructureFeatures()
    result = feat.compute(
        symbol="EURUSD",
        open=1.0850, high=1.0870, low=1.0840, close=1.0865,
        volume=1200,
        bid=1.0864, ask=1.0866,
        atr14=0.0018,
    )
    print(result.spread_pct, result.imbalance)
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from collections import deque
from typing import NamedTuple


class OHLCV(NamedTuple):
    open: float
    high: float
    low: float
    close: float
    volume: float = 0.0


@dataclass
class MicroBarFeatures:
    """Per-candle microstructure metrics."""

    # Bid/ask spread as fraction of mid-price (0 … ~0.01)
    spread_pct: float = 0.0

    # Trade imbalance: close position within [low, high] mapped to [-1, +1]
    # -1 = close at low (bearish pressure), +1 = close at high (bullish)
    imbalance: float = 0.0

    # Body ratio: |close - open| / (high - low); 1 = marubozu, 0 = doji
    body_ratio: float = 0.0

    # Range ratio: current bar range / ATR14
    # > 1.5 = expanding (momentum or spike); < 0.5 = compression
    range_ratio: float = 1.0

    # Kyle lambda proxy (approximate): signed_vol_pressure per pip
    # Positive = net buying; negative = net selling
    kyle_lambda: float = 0.0

    # Wicking pressure: upper / lower shadow asymmetry
    # > 0 = upper wick dominates (selling above); < 0 = lower wick dominates
    wick_asymmetry: float = 0.0

    # High-to-low ratio: high / low — measures intraday range as a multiplicative
    # factor.  E.g. 1.005 means price travelled 0.5% within the bar.
    # NaN if low == 0.  Clamped to [0.5, 2.0] for downstream stability.
    high2low_ratio: float = 1.0


class MicrostructureFeatures:
    """Stateful microstructure feature extractor.

    Keeps a rolling signed-volume history to estimate Kyle's lambda.
    """

    def __init__(self, lookback: int = 20) -> None:
        self._lookback = lookback
        self._sv_history: deque[float] = deque(maxlen=lookback)
        self._price_chg_history: deque[float] = deque(maxlen=lookback)

    def compute(
        self,
        *,
        symbol: str = "",
        open: float,
        high: float,
        low: float,
        close: float,
        volume: float = 0.0,
        bid: float | None = None,
        ask: float | None = None,
        prev_close: float | None = None,
        atr14: float | None = None,
    ) -> MicroBarFeatures:
        """Compute microstructure features for one OHLCV bar."""

        feat = MicroBarFeatures()

        bar_range = high - low
        mid = (high + low) / 2.0

        # ── Spread ────────────────────────────────────────────────────────
        if bid is not None and ask is not None and ask > bid > 0:
            spread = ask - bid
            feat.spread_pct = spread / ((bid + ask) / 2) if (bid + ask) > 0 else 0.0
        elif mid > 0:
            # Estimate spread from bar range (rough proxy when tick data absent)
            feat.spread_pct = bar_range / mid * 0.10

        # ── Imbalance ─────────────────────────────────────────────────────
        if bar_range > 0:
            feat.imbalance = ((close - low) / bar_range) * 2 - 1  # [-1, +1]

        # ── Body ratio ────────────────────────────────────────────────────
        if bar_range > 0:
            feat.body_ratio = abs(close - open) / bar_range

        # ── Range ratio ───────────────────────────────────────────────────
        if atr14 and atr14 > 0 and bar_range > 0:
            feat.range_ratio = bar_range / atr14

        # ── Wick asymmetry ────────────────────────────────────────────────
        upper_wick = high - max(open, close)
        lower_wick = min(open, close) - low
        wick_total = upper_wick + lower_wick
        if wick_total > 0:
            feat.wick_asymmetry = (upper_wick - lower_wick) / wick_total  # [-1, +1]

        # ── High-to-low ratio ───────────────────────────────────────────
        if low > 0:
            feat.high2low_ratio = min(2.0, max(0.5, high / low))

        # ── Kyle lambda proxy ─────────────────────────────────────────────
        if prev_close and prev_close > 0:
            price_chg = (close - prev_close) / prev_close
            # Signed volume: convention — positive if bull candle
            sign = 1.0 if close >= open else -1.0
            signed_vol = sign * volume

            self._sv_history.append(signed_vol)
            self._price_chg_history.append(price_chg)

            if len(self._sv_history) >= min(5, self._lookback):
                sv_list = list(self._sv_history)
                pc_list = list(self._price_chg_history)
                cov = _covariance(sv_list, pc_list)
                sv_var = _variance(sv_list)
                feat.kyle_lambda = cov / sv_var if sv_var != 0 else 0.0
                # Normalise to reasonable range
                feat.kyle_lambda = max(-1.0, min(1.0, feat.kyle_lambda * 1e6))

        return feat


# ── Utility ───────────────────────────────────────────────────────────────

def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _covariance(xs: list[float], ys: list[float]) -> float:
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    mx = _mean(xs[:n])
    my = _mean(ys[:n])
    return sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / n


def _variance(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    mx = _mean(xs)
    return sum((x - mx) ** 2 for x in xs) / len(xs)
