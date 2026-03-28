"""Bias Engine — HTF bias resolution, premium/discount, regime detection.

Determines the higher-timeframe directional bias that filters LTF setups.
Uses H4/D1 candles to establish:
- Directional bias (bullish / bearish / neutral)
- Regime (trending / ranging / reversing / volatile)
- Premium / discount relative to HTF dealing range
"""

from __future__ import annotations

from models.market_data import Candle
from models.ict_models import (
    Bias, Regime, DealingRange,
)
from strategies.ict.structure import find_swing_points, get_structure_bias


def resolve_htf_bias(
    htf_candles: list[Candle],
    left: int = 3,
    right: int = 2,
) -> Bias:
    """Determine directional bias from higher-timeframe candles.

    Uses swing-point structure to detect HH/HL (bullish) or LH/LL (bearish).
    Falls back to simple close-vs-open on last N candles.
    """
    if len(htf_candles) < 10:
        return Bias.NEUTRAL

    highs, lows = find_swing_points(htf_candles, left=left, right=right)
    bias = get_structure_bias(highs, lows)

    # If structure is clear, use it
    if bias != Bias.NEUTRAL:
        return bias

    # Fallback: net directional pressure of last 10 candles
    recent = htf_candles[-10:]
    bulls = sum(1 for c in recent if c.close > c.open)
    bears = sum(1 for c in recent if c.close < c.open)
    if bulls >= 7:
        return Bias.BULLISH
    if bears >= 7:
        return Bias.BEARISH
    return Bias.NEUTRAL


def detect_regime(
    htf_candles: list[Candle],
    atr: float = 0.0,
) -> Regime:
    """Classify market regime from HTF candles.

    - Trending: clear directional bias + expanding range
    - Ranging: no bias + small bodies + equal-ish highs/lows
    - Volatile: large bodies without clear direction
    - Reversing: recent MSS or bias flip detected
    """
    if len(htf_candles) < 10:
        return Regime.UNKNOWN

    recent = htf_candles[-10:]

    # Body sizes
    bodies = [abs(c.close - c.open) for c in recent]
    ranges = [c.high - c.low for c in recent if c.high > c.low]
    avg_body = sum(bodies) / len(bodies) if bodies else 0
    avg_range = sum(ranges) / len(ranges) if ranges else 1

    # Directional count
    bulls = sum(1 for c in recent if c.close > c.open)
    bears = sum(1 for c in recent if c.close < c.open)

    # Body / range ratio (how decisive are candles?)
    body_ratio = avg_body / avg_range if avg_range > 0 else 0

    # Volatility: compare recent ATR to average range
    is_volatile = False
    if atr > 0 and avg_range > 0:
        is_volatile = atr > avg_range * 1.5

    # Trending: strong directional dominance + decent body ratio
    if (bulls >= 6 or bears >= 6) and body_ratio > 0.3:
        return Regime.TRENDING

    # Volatile but indecisive
    if is_volatile and abs(bulls - bears) < 3:
        return Regime.VOLATILE

    # Reversing: first half and second half disagree
    first_half = recent[:5]
    second_half = recent[5:]
    f_bulls = sum(1 for c in first_half if c.close > c.open)
    s_bulls = sum(1 for c in second_half if c.close > c.open)
    if (f_bulls >= 4 and s_bulls <= 1) or (f_bulls <= 1 and s_bulls >= 4):
        return Regime.REVERSING

    # Ranging: small body candles, no strong direction
    if body_ratio < 0.35:
        return Regime.RANGING

    # Moderate trend: weaker directional dominance
    if (bulls >= 5 or bears >= 5) and body_ratio > 0.25:
        return Regime.TRENDING

    # Volatile: decent-sized bodies but no clear direction
    if body_ratio > 0.35 and abs(bulls - bears) <= 3:
        return Regime.VOLATILE

    # Last resort: ranging
    return Regime.RANGING


def build_htf_dealing_range(
    htf_candles: list[Candle],
    left: int = 3,
    right: int = 2,
) -> DealingRange:
    """Build a dealing range from HTF swing points."""
    if len(htf_candles) < 10:
        return DealingRange()

    highs, lows = find_swing_points(htf_candles, left=left, right=right)
    if not highs or not lows:
        # Fallback: use raw high/low of available candles
        h = max(c.high for c in htf_candles[-20:])
        l = min(c.low for c in htf_candles[-20:])
        return DealingRange(high=h, low=l, is_parent=True)

    # Use the most recent swing high and swing low
    top = max(highs[-3:], key=lambda sp: sp.price) if len(highs) >= 3 else highs[-1]
    bot = min(lows[-3:], key=lambda sp: sp.price) if len(lows) >= 3 else lows[-1]

    return DealingRange(
        high=top.price,
        low=bot.price,
        is_parent=True,
    )


def classify_premium_discount(
    price: float,
    dealing_range: DealingRange,
) -> str:
    """Return 'premium', 'discount', or 'equilibrium'."""
    if dealing_range.high == 0:
        return "unknown"

    eq = dealing_range.equilibrium
    total_range = dealing_range.high - dealing_range.low
    if total_range <= 0:
        return "equilibrium"

    # Within 5% of equilibrium = equilibrium zone
    eq_band = total_range * 0.05
    if abs(price - eq) <= eq_band:
        return "equilibrium"

    if price > eq:
        return "premium"
    return "discount"
