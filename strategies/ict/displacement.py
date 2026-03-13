"""Displacement Engine — impulsive candle / move detection.

Displacement = strong directional conviction.  It is identified by:
- Abnormally large body relative to recent average
- A body that dominates the candle range (small wicks)
- Creation of an FVG is a strong confirmation
"""

from __future__ import annotations

from models.market_data import Candle
from models.ict_models import Bias, Displacement


def detect_displacement(
    candles: list[Candle],
    lookback: int = 5,
    body_ratio_threshold: float = 2.0,
) -> list[Displacement]:
    """Scan recent candles for displacement events.

    A candle qualifies as displacement if:
    1. Its body is >= ``body_ratio_threshold`` × the average body of the
       preceding candles.
    2. Its body is > 60% of its total range (wick-dominant candles are
       not displacement).
    """
    displacements: list[Displacement] = []
    if len(candles) < lookback + 1:
        return displacements

    for i in range(lookback, len(candles)):
        c = candles[i]
        body = abs(c.close - c.open)
        rng = c.high - c.low
        if rng == 0:
            continue

        # Body must dominate the range
        body_ratio_of_range = body / rng
        if body_ratio_of_range < 0.60:
            continue

        # Compare to average body
        avg_body = _avg_body(candles, i, lookback)
        if avg_body == 0:
            continue

        ratio = body / avg_body
        if ratio < body_ratio_threshold:
            continue

        direction = Bias.BULLISH if c.close > c.open else Bias.BEARISH

        # Check if an FVG would be created (gap between candle i-1 and i+1)
        created_fvg = False
        if i >= 1 and i < len(candles) - 1:
            prev_c = candles[i - 1]
            next_c = candles[i + 1]
            if direction == Bias.BULLISH:
                created_fvg = next_c.low > prev_c.high
            else:
                created_fvg = next_c.high < prev_c.low

        displacements.append(Displacement(
            direction=direction,
            candle_idx=i,
            body_size=body,
            avg_body=avg_body,
            ratio=round(ratio, 2),
            created_fvg=created_fvg,
            timestamp=c.timestamp,
        ))

    return displacements


def _avg_body(candles: list[Candle], current_idx: int, lookback: int) -> float:
    """Average absolute body size of the preceding *lookback* candles."""
    total = 0.0
    count = 0
    for j in range(max(0, current_idx - lookback), current_idx):
        total += abs(candles[j].close - candles[j].open)
        count += 1
    return total / count if count > 0 else 0.0
