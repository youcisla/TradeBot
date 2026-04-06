"""Adaptive intraday stop — finds the most recent swing low in price action.

Alpaca Momentum-Trading-Example pattern: instead of a fixed ATR/A% stop,
scan recent candles for a local swing low and place the stop just below it.
This adapts to current market microstructure rather than using a static offset.

Usage::

    from utils.adaptive_stop import find_adaptive_stop
    sl = find_adaptive_stop(candles, direction, atr, pip_value, buffer_pips=2)
    if sl is not None:
        # use adaptive sl
    else:
        # fall back to ATR-based stop
"""

from __future__ import annotations

from models.market_data import Candle


def find_adaptive_stop(
    candles: list[Candle],
    direction: str,
    atr: float,
    pip_value: float,
    buffer_pips: float = 2.0,
    min_candles: int = 10,
) -> float | None:
    """Return an adaptive stop price below the most recent swing low, or None.

    The swing-low algorithm:
    1. Scan the last `lookback` candles for local minima — a candle whose
       low is lower than both its immediate neighbours.
    2. Among all minima found, pick the *most recent* one.
    3. Place the stop `buffer_pips` below that level (rounded to tick precision).

    Returns None when the market is too quiet or candles are insufficient.

    Parameters
    ----------
    candles    : list of M5 (or finer) candles, most-recent last.
    direction  : "BUY" or "SELL".
    atr        : current ATR for the symbol (used as fallback if no swing found).
    pip_value  : pip size for the symbol (e.g. 0.0001 for EURUSD, 0.01 for XAUUSD).
    buffer_pips: how many pips below the swing low to place the stop.
    min_candles: minimum candles needed before attempting swing detection.
    """
    if len(candles) < min_candles:
        return None

    # ── Step 1: find local minima in the last 20 candles ────────────────
    lookback = min(20, len(candles) - 1)  # need neighbours
    window = candles[-lookback - 1:]

    swing_lows: list[tuple[int, float]] = []  # (index from start of window, low)

    for i in range(1, len(window) - 1):
        prev_low = window[i - 1].low
        curr_low = window[i].low
        next_low = window[i + 1].low

        # Strict local minimum
        if curr_low < prev_low and curr_low < next_low:
            swing_lows.append((i, curr_low))

    if not swing_lows:
        return None

    # ── Step 2: most recent swing low ────────────────────────────────────
    # swing_lows is in chronological order; last entry = most recent
    most_recent_idx, swing_low = swing_lows[-1]

    # Weight the stop by how "deep" the swing is — deeper swings get more room.
    # Express depth in pips relative to the candles around it.
    depth_pips = (min(window[most_recent_idx - 1].low, window[most_recent_idx + 1].low)
                  - swing_low) / pip_value

    # Only use this swing if the dip is meaningful (> 1 pip).
    # Small noise dips shouldn't override the ATR-based stop.
    if depth_pips < 1.0:
        return None

    # ── Step 3: buffer below the swing low ───────────────────────────────
    # Use the larger of buffer_pips or 30% of ATR in pip terms.
    atr_pips = atr / pip_value
    effective_buffer = max(buffer_pips, atr_pips * 0.30)

    buffer_price = effective_buffer * pip_value
    if direction == "BUY":
        stop = swing_low - buffer_price
    else:
        stop = swing_low + buffer_price

    return round(stop, 5)
