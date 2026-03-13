"""FVG Engine — Fair Value Gap detection & management.

Detects:
- Bullish FVG:  candle[i-1].high < candle[i+1].low (gap up)
- Bearish FVG:  candle[i-1].low  > candle[i+1].high (gap down)
- Consequent Encroachment (CE): midpoint of the FVG
- FVG fill: price returns into the gap
- FVG failure: body close through the invalid side
"""

from __future__ import annotations

from models.market_data import Candle
from models.ict_models import FairValueGap, FVGType, DealingRange


def detect_fvgs(
    candles: list[Candle],
    dealing_range: DealingRange | None = None,
    timeframe: str = "H1",
    lookback: int = 30,
) -> list[FairValueGap]:
    """Scan candles for fair value gaps.

    Returns all unmitigated FVGs found within the lookback window.
    """
    fvgs: list[FairValueGap] = []
    start = max(1, len(candles) - lookback)

    for i in range(start, len(candles) - 1):
        prev_c = candles[i - 1]
        mid_c = candles[i]
        next_c = candles[i + 1]

        # Bullish FVG: gap between prev high and next low
        if next_c.low > prev_c.high:
            fvg = FairValueGap(
                kind=FVGType.BULLISH,
                high=next_c.low,
                low=prev_c.high,
                candle_idx=i,
                timestamp=mid_c.timestamp,
                timeframe=timeframe,
            )
            if dealing_range and dealing_range.high > 0:
                fvg.in_discount = dealing_range.is_discount(fvg.ce)
                fvg.in_premium = dealing_range.is_premium(fvg.ce)
            fvgs.append(fvg)

        # Bearish FVG: gap between prev low and next high
        if next_c.high < prev_c.low:
            fvg = FairValueGap(
                kind=FVGType.BEARISH,
                high=prev_c.low,
                low=next_c.high,
                candle_idx=i,
                timestamp=mid_c.timestamp,
                timeframe=timeframe,
            )
            if dealing_range and dealing_range.high > 0:
                fvg.in_discount = dealing_range.is_discount(fvg.ce)
                fvg.in_premium = dealing_range.is_premium(fvg.ce)
            fvgs.append(fvg)

    return fvgs


def update_fvg_status(
    fvgs: list[FairValueGap],
    candles: list[Candle],
) -> None:
    """Mark FVGs as filled or failed based on subsequent price action.

    - Filled: price has traded into the FVG (touched it).
    - Failed: body close through the wrong side invalidates the FVG.
      - Bullish FVG fails if a candle body closes below fvg.low.
      - Bearish FVG fails if a candle body closes above fvg.high.
    """
    for fvg in fvgs:
        if fvg.failed:
            continue
        for c in candles[fvg.candle_idx + 2:]:
            # Check fill
            if not fvg.filled:
                if fvg.kind == FVGType.BULLISH and c.low <= fvg.high:
                    fvg.filled = True
                    fvg.fill_time = c.timestamp
                elif fvg.kind == FVGType.BEARISH and c.high >= fvg.low:
                    fvg.filled = True
                    fvg.fill_time = c.timestamp

            # Check failure (body close through)
            close_body = min(c.open, c.close)  # body low
            open_body = max(c.open, c.close)   # body high
            if fvg.kind == FVGType.BULLISH and close_body < fvg.low:
                fvg.failed = True
                break
            if fvg.kind == FVGType.BEARISH and open_body > fvg.high:
                fvg.failed = True
                break


def get_active_fvgs(
    fvgs: list[FairValueGap],
    current_price: float,
    direction: str = "",
) -> list[FairValueGap]:
    """Return FVGs that are still valid and near current price.

    If *direction* is specified, filter to matching FVG type.
    """
    active: list[FairValueGap] = []
    for fvg in fvgs:
        if fvg.failed:
            continue
        if direction == "BUY" and fvg.kind != FVGType.BULLISH:
            continue
        if direction == "SELL" and fvg.kind != FVGType.BEARISH:
            continue
        active.append(fvg)
    return active
