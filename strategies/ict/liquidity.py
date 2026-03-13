"""Liquidity Engine — BSL/SSL mapping and sweep detection.

Maps:
- Swing high clusters → buy-side liquidity (BSL)
- Swing low clusters → sell-side liquidity (SSL)
- Equal highs / equal lows
- Previous day high/low, session high/low
- Detects when price sweeps a level then reverses
"""

from __future__ import annotations

from models.market_data import Candle
from models.ict_models import (
    LiquidityLevel, LiquidityType, LiquiditySweep, SwingPoint, SessionInfo,
)


# Tolerance for "equal" highs/lows (as a fraction of price)
_EQ_TOL = 0.0003


def map_liquidity(
    swing_highs: list[SwingPoint],
    swing_lows: list[SwingPoint],
    session_info: SessionInfo,
    current_price: float,
) -> tuple[list[LiquidityLevel], list[LiquidityLevel]]:
    """Return (bsl_levels, ssl_levels) sorted by distance from price."""
    bsl: list[LiquidityLevel] = []
    ssl: list[LiquidityLevel] = []

    # Swing highs → buy-side liquidity
    for sh in swing_highs:
        if sh.broken:
            continue
        bsl.append(LiquidityLevel(
            price=sh.price,
            kind=LiquidityType.BSL,
            source="swing_high",
            timestamp=sh.timestamp,
        ))

    # Swing lows → sell-side liquidity
    for sl in swing_lows:
        if sl.broken:
            continue
        ssl.append(LiquidityLevel(
            price=sl.price,
            kind=LiquidityType.SSL,
            source="swing_low",
            timestamp=sl.timestamp,
        ))

    # Detect equal highs (clustered swing highs)
    _mark_equal_levels(bsl)
    _mark_equal_levels(ssl)

    # Session / PDH / PDL levels
    if session_info.prev_day_high > 0:
        bsl.append(LiquidityLevel(
            price=session_info.prev_day_high,
            kind=LiquidityType.BSL,
            source="pdh",
            strength=2,
        ))
    if session_info.prev_day_low > 0:
        ssl.append(LiquidityLevel(
            price=session_info.prev_day_low,
            kind=LiquidityType.SSL,
            source="pdl",
            strength=2,
        ))
    if session_info.asian_high > 0:
        bsl.append(LiquidityLevel(
            price=session_info.asian_high,
            kind=LiquidityType.BSL,
            source="asian_high",
        ))
    if session_info.asian_low > 0:
        ssl.append(LiquidityLevel(
            price=session_info.asian_low,
            kind=LiquidityType.SSL,
            source="asian_low",
        ))
    if session_info.session_high > 0 and session_info.session_high != session_info.prev_day_high:
        bsl.append(LiquidityLevel(
            price=session_info.session_high,
            kind=LiquidityType.BSL,
            source="session_high",
        ))
    if session_info.session_low > 0 and session_info.session_low != session_info.prev_day_low:
        ssl.append(LiquidityLevel(
            price=session_info.session_low,
            kind=LiquidityType.SSL,
            source="session_low",
        ))

    # Sort by distance from current price (nearest first)
    bsl.sort(key=lambda l: abs(l.price - current_price))
    ssl.sort(key=lambda l: abs(l.price - current_price))

    return bsl, ssl


def detect_sweeps(
    candles: list[Candle],
    bsl: list[LiquidityLevel],
    ssl: list[LiquidityLevel],
    lookback: int = 5,
) -> list[LiquiditySweep]:
    """Detect sweeps: price wick through a level then closes back.

    A sweep is a wick beyond the level followed by a close on the
    opposite side — shows the level was raided, not broken.
    """
    sweeps: list[LiquiditySweep] = []
    if len(candles) < 2:
        return sweeps

    start = max(0, len(candles) - lookback)

    for i in range(start, len(candles)):
        c = candles[i]
        # BSL sweep: wick above level, close below
        for level in bsl:
            if level.swept:
                continue
            if c.high > level.price and c.close < level.price:
                level.swept = True
                level.sweep_time = c.timestamp
                sweeps.append(LiquiditySweep(
                    level=level,
                    sweep_price=c.high,
                    sweep_candle_idx=i,
                    timestamp=c.timestamp,
                ))

        # SSL sweep: wick below level, close above
        for level in ssl:
            if level.swept:
                continue
            if c.low < level.price and c.close > level.price:
                level.swept = True
                level.sweep_time = c.timestamp
                sweeps.append(LiquiditySweep(
                    level=level,
                    sweep_price=c.low,
                    sweep_candle_idx=i,
                    timestamp=c.timestamp,
                ))

    return sweeps


def _mark_equal_levels(levels: list[LiquidityLevel]) -> None:
    """Cluster levels that are within tolerance and boost their strength."""
    for i, a in enumerate(levels):
        for b in levels[i + 1:]:
            if a.price > 0 and abs(a.price - b.price) / a.price < _EQ_TOL:
                src = "equal_highs" if a.kind == LiquidityType.BSL else "equal_lows"
                a.source = src
                b.source = src
                a.strength = max(a.strength, 2)
                b.strength = max(b.strength, 2)


def infer_draw_on_liquidity(
    bsl: list[LiquidityLevel],
    ssl: list[LiquidityLevel],
    structure_bias: str,
    current_price: float,
) -> str:
    """Infer which side price is likely targeting next."""
    nearest_bsl = bsl[0].price if bsl else 0
    nearest_ssl = ssl[0].price if ssl else 0

    if structure_bias == "bullish" and nearest_bsl > current_price:
        return "buy_side"
    if structure_bias == "bearish" and nearest_ssl < current_price:
        return "sell_side"
    # Fallback: whichever is closer
    dist_bsl = abs(nearest_bsl - current_price) if nearest_bsl else float("inf")
    dist_ssl = abs(nearest_ssl - current_price) if nearest_ssl else float("inf")
    return "buy_side" if dist_bsl < dist_ssl else "sell_side"
