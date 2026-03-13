"""Structure Engine — swing points, BOS, MSS, dealing ranges.

Identifies:
- Swing highs and swing lows (configurable lookback)
- Break of Structure (BOS) — continuation
- Market Structure Shift (MSS) — reversal, requires displacement
- Bullish / bearish market structure
- Dealing ranges (parent + internal)
"""

from __future__ import annotations

from models.market_data import Candle
from models.ict_models import (
    Bias, SwingPoint, StructureBreak, DealingRange,
)


def find_swing_points(
    candles: list[Candle],
    left: int = 3,
    right: int = 3,
) -> tuple[list[SwingPoint], list[SwingPoint]]:
    """Return (swing_highs, swing_lows) using left/right bar comparison."""
    highs: list[SwingPoint] = []
    lows: list[SwingPoint] = []
    if len(candles) < left + right + 1:
        return highs, lows

    for i in range(left, len(candles) - right):
        c = candles[i]
        # Swing high: higher high than left AND right neighbours
        is_sh = all(c.high >= candles[i - j].high for j in range(1, left + 1)) and \
                all(c.high >= candles[i + j].high for j in range(1, right + 1))
        if is_sh:
            highs.append(SwingPoint(
                index=i, price=c.high, is_high=True, timestamp=c.timestamp,
            ))

        # Swing low: lower low than left AND right neighbours
        is_sl = all(c.low <= candles[i - j].low for j in range(1, left + 1)) and \
                all(c.low <= candles[i + j].low for j in range(1, right + 1))
        if is_sl:
            lows.append(SwingPoint(
                index=i, price=c.low, is_high=False, timestamp=c.timestamp,
            ))

    return highs, lows


def detect_structure_breaks(
    candles: list[Candle],
    swing_highs: list[SwingPoint],
    swing_lows: list[SwingPoint],
    lookback: int = 20,
) -> list[StructureBreak]:
    """Detect BOS and MSS events in the recent candle window.

    Rules:
    - Bullish BOS: price breaks above the most recent swing high while
      structure is already bullish (higher highs / higher lows).
    - Bearish BOS: price breaks below the most recent swing low while
      structure is already bearish.
    - Bullish MSS: price breaks above a swing high while prior structure
      was bearish (shift from bearish → bullish).
    - Bearish MSS: price breaks below a swing low while prior structure
      was bullish (shift from bullish → bearish).

    An MSS is only valid when the candle that breaks is impulsive
    (displacement) — that flag is set later by the displacement engine.
    """
    breaks: list[StructureBreak] = []
    if not swing_highs or not swing_lows or len(candles) < 5:
        return breaks

    # Determine prior bias from recent swing sequence
    prior_bias = _infer_structure_bias(swing_highs, swing_lows)

    start_idx = max(0, len(candles) - lookback)

    for sh in reversed(swing_highs[-6:]):
        if sh.broken:
            continue
        for i in range(max(start_idx, sh.index + 1), len(candles)):
            if candles[i].close > sh.price:
                sh.broken = True
                kind = "BOS" if prior_bias == Bias.BULLISH else "MSS"
                breaks.append(StructureBreak(
                    kind=kind,
                    direction=Bias.BULLISH,
                    break_price=candles[i].close,
                    broken_swing=sh,
                    candle_idx=i,
                    timestamp=candles[i].timestamp,
                ))
                break

    for sl in reversed(swing_lows[-6:]):
        if sl.broken:
            continue
        for i in range(max(start_idx, sl.index + 1), len(candles)):
            if candles[i].close < sl.price:
                sl.broken = True
                kind = "BOS" if prior_bias == Bias.BEARISH else "MSS"
                breaks.append(StructureBreak(
                    kind=kind,
                    direction=Bias.BEARISH,
                    break_price=candles[i].close,
                    broken_swing=sl,
                    candle_idx=i,
                    timestamp=candles[i].timestamp,
                ))
                break

    return breaks


def _infer_structure_bias(
    highs: list[SwingPoint],
    lows: list[SwingPoint],
) -> Bias:
    """Infer bullish/bearish structure from the last few swing points."""
    if len(highs) < 2 or len(lows) < 2:
        return Bias.NEUTRAL

    hh = highs[-1].price > highs[-2].price
    hl = lows[-1].price > lows[-2].price
    lh = highs[-1].price < highs[-2].price
    ll = lows[-1].price < lows[-2].price

    if hh and hl:
        return Bias.BULLISH
    if lh and ll:
        return Bias.BEARISH
    return Bias.NEUTRAL


def build_dealing_range(
    swing_highs: list[SwingPoint],
    swing_lows: list[SwingPoint],
) -> DealingRange:
    """Build the active dealing range from the most recent significant
    swing high and swing low."""
    if not swing_highs or not swing_lows:
        return DealingRange()

    high = max(swing_highs[-3:], key=lambda s: s.price)
    low = min(swing_lows[-3:], key=lambda s: s.price)

    return DealingRange(
        high=high.price,
        low=low.price,
        timestamp=max(high.timestamp, low.timestamp),
    )


def get_structure_bias(
    swing_highs: list[SwingPoint],
    swing_lows: list[SwingPoint],
) -> Bias:
    """Public wrapper for structure bias inference."""
    return _infer_structure_bias(swing_highs, swing_lows)
