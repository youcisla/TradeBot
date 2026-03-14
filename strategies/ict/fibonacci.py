"""Fibonacci Engine — displacement-anchored retracement and Golden Zone.

Provides Fibonacci retracement levels anchored to valid displacement legs
(Rule #1), confluence detection with FVG CE and OB mean threshold (Rule #3),
liquidity target validation (Rule #2), and retracement depth invalidation
(Rule #8).

Fibonacci acts as a **confluence validator** — it never replaces the core
ICT pipeline (sweep → MSS → displacement → FVG/OB).  It only adds or
removes confidence via the scoring engine.

Supported levels: 0.382, 0.5, 0.618, 0.705, 0.786
Golden Zone:      0.618 – 0.705
"""

from __future__ import annotations

from typing import Optional

from models.market_data import Candle
from models.ict_models import (
    Bias,
    Displacement,
    FairValueGap,
    FibonacciLevel,
    FibonacciRetracement,
    LiquidityLevel,
    OrderBlock,
    SwingPoint,
)

# ── Constants ────────────────────────────────────────────────────────────

FIB_RATIOS = [0.382, 0.5, 0.618, 0.705, 0.786]
GZ_TOP_RATIO = 0.618
GZ_BOTTOM_RATIO = 0.705


# ── Public API ───────────────────────────────────────────────────────────

def detect_fib_levels(
    candles: list[Candle],
    displacements: list[Displacement],
    swing_highs: list[SwingPoint],
    swing_lows: list[SwingPoint],
    htf_bias: Bias = Bias.NEUTRAL,
) -> Optional[FibonacciRetracement]:
    """Detect Fibonacci retracement levels anchored to displacement.

    Rule #1: Only anchor Fibonacci to displacement legs — NOT random swings.

    Workflow:
    1. Find the most recent displacement matching (or aligned with) HTF bias.
    2. Identify the impulse leg:
       - Bullish displacement → leg from swing low → displacement high
       - Bearish displacement → leg from swing high → displacement low
    3. Calculate retracement levels.
    4. Identify Golden Zone (0.618 – 0.705).
    """
    if not displacements or not candles:
        return None

    # Pick the most recent displacement aligned with bias (or just most recent)
    disp = _pick_displacement(displacements, htf_bias)
    if disp is None:
        return None

    # Find anchor points for the impulse leg
    anchor = _find_impulse_leg(candles, disp, swing_highs, swing_lows)
    if anchor is None:
        return None

    anchor_low, anchor_high = anchor
    if anchor_high <= anchor_low:
        return None  # degenerate leg

    leg_range = anchor_high - anchor_low

    # Calculate retracement levels
    levels: list[FibonacciLevel] = []
    for ratio in FIB_RATIOS:
        if disp.direction == Bias.BULLISH:
            # Bullish: retracement = high - ratio × range (price pulling back down)
            price = anchor_high - ratio * leg_range
        else:
            # Bearish: retracement = low + ratio × range (price pulling back up)
            price = anchor_low + ratio * leg_range

        label = f"{ratio}"
        if ratio == GZ_TOP_RATIO:
            label = "0.618 (GZ top)"
        elif ratio == GZ_BOTTOM_RATIO:
            label = "0.705 (GZ bottom)"

        levels.append(FibonacciLevel(
            ratio=ratio,
            price=round(price, 6),
            label=label,
        ))

    # Golden Zone
    if disp.direction == Bias.BULLISH:
        gz_top = anchor_high - GZ_TOP_RATIO * leg_range
        gz_bottom = anchor_high - GZ_BOTTOM_RATIO * leg_range
        inval = anchor_high - 0.786 * leg_range
        ext_1_0 = anchor_high
        ext_neg_0_272 = anchor_high + 0.272 * leg_range
        ext_neg_0_618 = anchor_high + 0.618 * leg_range
    else:
        gz_top = anchor_low + GZ_TOP_RATIO * leg_range
        gz_bottom = anchor_low + GZ_BOTTOM_RATIO * leg_range
        inval = anchor_low + 0.786 * leg_range
        ext_1_0 = anchor_low
        ext_neg_0_272 = anchor_low - 0.272 * leg_range
        ext_neg_0_618 = anchor_low - 0.618 * leg_range

    return FibonacciRetracement(
        direction=disp.direction,
        anchor_low=round(anchor_low, 6),
        anchor_high=round(anchor_high, 6),
        levels=levels,
        golden_zone_top=round(max(gz_top, gz_bottom), 6),
        golden_zone_bottom=round(min(gz_top, gz_bottom), 6),
        golden_zone_mid=round((gz_top + gz_bottom) / 2.0, 6),
        invalidation_price=round(inval, 6),
        ext_1_000=round(ext_1_0, 6),
        ext_neg_0_272=round(ext_neg_0_272, 6),
        ext_neg_0_618=round(ext_neg_0_618, 6),
        anchor_displacement=disp,
        timestamp=disp.timestamp,
    )


def check_golden_zone_confluence(
    fib: FibonacciRetracement,
    active_fvgs: list[FairValueGap],
    active_obs: list[OrderBlock],
) -> None:
    """Rule #3: Check if Golden Zone overlaps FVG CE or OB mean threshold.

    Sets confluence flags on the FibonacciRetracement object.
    """
    gz_top = fib.golden_zone_top
    gz_bot = fib.golden_zone_bottom

    # FVG Consequent Encroachment confluence
    for fvg in active_fvgs:
        if fvg.failed:
            continue
        ce = fvg.ce
        if ce > 0 and gz_bot <= ce <= gz_top:
            fib.gz_fvg_confluence = True
            fib.gz_ce_confluence = True
            break

    # OB mean threshold confluence
    for ob in active_obs:
        if not ob.valid:
            continue
        mt = ob.mean_threshold
        if mt > 0 and gz_bot <= mt <= gz_top:
            fib.gz_ob_confluence = True
            break


def check_liquidity_target(
    fib: FibonacciRetracement,
    bsl_levels: list[LiquidityLevel],
    ssl_levels: list[LiquidityLevel],
    current_price: float,
) -> None:
    """Rule #2: Verify that price has a clear target after retracement.

    For bullish: need BSL above current price for take-profit.
    For bearish: need SSL below current price for take-profit.
    """
    if fib.direction == Bias.BULLISH:
        fib.has_liquidity_target = any(
            l.price > current_price for l in bsl_levels
        )
    elif fib.direction == Bias.BEARISH:
        fib.has_liquidity_target = any(
            l.price < current_price for l in ssl_levels
        )


def validate_retracement_depth(
    fib: FibonacciRetracement,
    current_price: float,
) -> str:
    """Rule #8: Classify current price relative to Fibonacci levels.

    Returns and sets fib.retracement_depth to one of:
    - "too_shallow"  — above 0.382  (poor entry location)
    - "acceptable"   — 0.382–0.618  (decent but not GZ)
    - "golden_zone"  — 0.618–0.705  (optimal entry)
    - "deep"         — 0.705–0.786  (acceptable but risky)
    - "too_deep"     — below 0.786  (weak setup, likely to fail)
    - "outside"      — not within the leg range at all
    """
    if fib.anchor_high <= fib.anchor_low:
        fib.retracement_depth = "outside"
        return fib.retracement_depth

    leg = fib.anchor_high - fib.anchor_low

    if fib.direction == Bias.BULLISH:
        # Retracement ratio: how far price pulled back from high
        if current_price >= fib.anchor_high:
            fib.retracement_depth = "outside"
        elif current_price <= fib.anchor_low:
            fib.retracement_depth = "too_deep"
        else:
            ratio = (fib.anchor_high - current_price) / leg
            fib.retracement_depth = _classify_ratio(ratio)
    else:
        # Bearish: retracement ratio = how far price bounced from low
        if current_price <= fib.anchor_low:
            fib.retracement_depth = "outside"
        elif current_price >= fib.anchor_high:
            fib.retracement_depth = "too_deep"
        else:
            ratio = (current_price - fib.anchor_low) / leg
            fib.retracement_depth = _classify_ratio(ratio)

    return fib.retracement_depth


# ── Private helpers ──────────────────────────────────────────────────────

def _pick_displacement(
    displacements: list[Displacement],
    htf_bias: Bias,
) -> Optional[Displacement]:
    """Pick the best displacement to anchor Fibonacci to.

    Prefer: most recent displacement aligned with HTF bias.
    Fallback: most recent displacement of any direction.
    """
    # Walk from most recent backward
    for disp in reversed(displacements):
        if htf_bias == Bias.BULLISH and disp.direction == Bias.BULLISH:
            return disp
        if htf_bias == Bias.BEARISH and disp.direction == Bias.BEARISH:
            return disp

    # Fallback: most recent displacement
    return displacements[-1] if displacements else None


def _find_impulse_leg(
    candles: list[Candle],
    disp: Displacement,
    swing_highs: list[SwingPoint],
    swing_lows: list[SwingPoint],
) -> Optional[tuple[float, float]]:
    """Find the impulse leg anchored to a displacement candle.

    - Bullish displacement → leg from nearest swing low BEFORE disp → disp high
    - Bearish displacement → leg from nearest swing high BEFORE disp → disp low
    """
    disp_idx = disp.candle_idx
    if disp_idx < 0 or disp_idx >= len(candles):
        return None

    disp_candle = candles[disp_idx]

    if disp.direction == Bias.BULLISH:
        # Find the swing low before/at displacement
        anchor_low = _find_leg_anchor_low(candles, disp_idx, swing_lows)
        anchor_high = disp_candle.high
        if anchor_low is None:
            return None
        return (anchor_low, anchor_high)

    elif disp.direction == Bias.BEARISH:
        # Find the swing high before/at displacement
        anchor_high = _find_leg_anchor_high(candles, disp_idx, swing_highs)
        anchor_low = disp_candle.low
        if anchor_high is None:
            return None
        return (anchor_low, anchor_high)

    return None


def _find_leg_anchor_low(
    candles: list[Candle],
    before_idx: int,
    swing_lows: list[SwingPoint],
    max_lookback: int = 20,
) -> Optional[float]:
    """Find the lowest swing low before the displacement candle."""
    # First try swing points
    candidates = [
        sl for sl in swing_lows
        if sl.index < before_idx and before_idx - sl.index <= max_lookback
    ]
    if candidates:
        return min(c.price for c in candidates)

    # Fallback: lowest low in lookback window
    start = max(0, before_idx - max_lookback)
    if start >= before_idx:
        return None
    return min(candles[i].low for i in range(start, before_idx))


def _find_leg_anchor_high(
    candles: list[Candle],
    before_idx: int,
    swing_highs: list[SwingPoint],
    max_lookback: int = 20,
) -> Optional[float]:
    """Find the highest swing high before the displacement candle."""
    candidates = [
        sh for sh in swing_highs
        if sh.index < before_idx and before_idx - sh.index <= max_lookback
    ]
    if candidates:
        return max(c.price for c in candidates)

    start = max(0, before_idx - max_lookback)
    if start >= before_idx:
        return None
    return max(candles[i].high for i in range(start, before_idx))


def _classify_ratio(ratio: float) -> str:
    """Classify a retracement ratio into depth category."""
    if ratio < 0.382:
        return "too_shallow"
    if ratio < 0.618:
        return "acceptable"
    if ratio <= 0.705:
        return "golden_zone"
    if ratio <= 0.786:
        return "deep"
    return "too_deep"
