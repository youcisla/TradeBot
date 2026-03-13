"""Order Block Engine — OB detection, validation, and ranking.

Detects:
- Bullish OB: last bearish candle before a bullish displacement
- Bearish OB: last bullish candle before a bearish displacement
- Mean threshold: midpoint of OB for refined entries
- High-probability OBs: OB + sweep + displacement + MSS + FVG confluence
"""

from __future__ import annotations

from models.market_data import Candle
from models.ict_models import (
    OrderBlock, OBType, Displacement, StructureBreak,
    FairValueGap, LiquiditySweep, Bias,
)


def detect_order_blocks(
    candles: list[Candle],
    displacements: list[Displacement],
    timeframe: str = "H1",
    lookback: int = 30,
) -> list[OrderBlock]:
    """Detect order blocks based on displacement candles.

    A bullish OB is the last bearish candle before a bullish displacement.
    A bearish OB is the last bullish candle before a bearish displacement.
    """
    obs: list[OrderBlock] = []
    if len(candles) < 3:
        return obs

    for disp in displacements:
        idx = disp.candle_idx
        if idx < 1:
            continue

        if disp.direction == Bias.BULLISH:
            # Find the last bearish candle before the displacement
            ob_idx = _find_last_opposite(candles, idx, bearish=True)
            if ob_idx is not None:
                c = candles[ob_idx]
                obs.append(OrderBlock(
                    kind=OBType.BULLISH,
                    high=c.high,
                    low=c.low,
                    open_price=c.open,
                    candle_idx=ob_idx,
                    timestamp=c.timestamp,
                    timeframe=timeframe,
                    has_displacement=True,
                ))

        elif disp.direction == Bias.BEARISH:
            ob_idx = _find_last_opposite(candles, idx, bearish=False)
            if ob_idx is not None:
                c = candles[ob_idx]
                obs.append(OrderBlock(
                    kind=OBType.BEARISH,
                    high=c.high,
                    low=c.low,
                    open_price=c.open,
                    candle_idx=ob_idx,
                    timestamp=c.timestamp,
                    timeframe=timeframe,
                    has_displacement=True,
                ))

    return obs


def _find_last_opposite(
    candles: list[Candle],
    before_idx: int,
    bearish: bool,
    max_lookback: int = 5,
) -> int | None:
    """Walk backward from *before_idx* to find the last candle of the
    opposite color."""
    for i in range(before_idx - 1, max(before_idx - max_lookback - 1, -1), -1):
        c = candles[i]
        is_bearish = c.close < c.open
        if bearish and is_bearish:
            return i
        if not bearish and not is_bearish:
            return i
    return None


def update_ob_status(
    obs: list[OrderBlock],
    candles: list[Candle],
) -> None:
    """Mark OBs as mitigated or invalid.

    - Bullish OB invalid: body close below OB low
    - Bearish OB invalid: body close above OB high
    - Mitigated: price returned into the OB zone
    """
    for ob in obs:
        if not ob.valid:
            continue
        for c in candles[ob.candle_idx + 1:]:
            # Mitigation check
            if not ob.mitigated:
                if ob.kind == OBType.BULLISH and c.low <= ob.high:
                    ob.mitigated = True
                elif ob.kind == OBType.BEARISH and c.high >= ob.low:
                    ob.mitigated = True

            # Invalidation: body close through mean threshold
            close_body_low = min(c.open, c.close)
            close_body_high = max(c.open, c.close)
            if ob.kind == OBType.BULLISH and close_body_low < ob.mean_threshold:
                ob.valid = False
                break
            if ob.kind == OBType.BEARISH and close_body_high > ob.mean_threshold:
                ob.valid = False
                break


def mark_high_probability(
    obs: list[OrderBlock],
    sweeps: list[LiquiditySweep],
    breaks: list[StructureBreak],
    fvgs: list[FairValueGap],
) -> None:
    """Upgrade OBs that have confluence with sweep + MSS + FVG."""
    for ob in obs:
        if not ob.valid:
            continue

        # Check nearby sweep (within 5 candles before OB)
        for sw in sweeps:
            if abs(sw.sweep_candle_idx - ob.candle_idx) <= 5:
                ob.has_liquidity_sweep = True
                break

        # Check nearby MSS
        for brk in breaks:
            if brk.kind == "MSS" and abs(brk.candle_idx - ob.candle_idx) <= 3:
                ob.has_mss = True
                if brk.displacement_confirmed:
                    ob.has_displacement = True
                break

        # Check overlapping FVG
        for fvg in fvgs:
            if fvg.failed:
                continue
            # FVG overlaps OB zone
            if fvg.low <= ob.high and fvg.high >= ob.low:
                ob.has_fvg = True
                break

        # High-probability = sweep + displacement + (MSS or FVG)
        ob.high_probability = (
            ob.has_liquidity_sweep
            and ob.has_displacement
            and (ob.has_mss or ob.has_fvg)
        )


def get_active_obs(
    obs: list[OrderBlock],
    direction: str = "",
) -> list[OrderBlock]:
    """Return valid, un-mitigated OBs, optionally filtered by direction."""
    active: list[OrderBlock] = []
    for ob in obs:
        if not ob.valid:
            continue
        if direction == "BUY" and ob.kind != OBType.BULLISH:
            continue
        if direction == "SELL" and ob.kind != OBType.BEARISH:
            continue
        active.append(ob)
    return active
