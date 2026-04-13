"""Setup Models — 6 ICT setup detectors.

Each function receives the full ICTContext and returns a SetupCandidate
(or None if the model doesn't match).

Models:
  1. Trend Continuation Long  — bullish bias + discount + sweep SSL + MSS + FVG/OB
  2. Trend Continuation Short — bearish bias + premium + sweep BSL + MSS + FVG/OB
  3. Reversal After Sweep     — sweep of major level + MSS + displacement + FVG/OB
  4. Range Dealing Long       — ranging + price at discount end + sweep + FVG/OB
  5. Range Dealing Short      — ranging + price at premium end + sweep + FVG/OB
  6. Session Sweep Reversal   — session-level sweep (Asian/PDH/PDL) + reversal
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Optional

from models.ict_models import (
    Bias, Regime, OBType, FVGType, SetupModel, ICTContext, SetupCandidate,
    LiquiditySweep, FairValueGap, OrderBlock, StructureBreak, Displacement,
)
from config import settings


def detect_all_setups(ctx: ICTContext) -> list[SetupCandidate]:
    """Run all 6 setup model detectors and return valid candidates."""
    detectors = [
        _trend_continuation_long,
        _trend_continuation_short,
        _reversal_after_sweep,
        _range_dealing_long,
        _range_dealing_short,
        _session_sweep_reversal,
    ]
    candidates: list[SetupCandidate] = []
    for fn in detectors:
        setup = fn(ctx)
        if setup is not None:
            candidates.append(setup)
    return candidates


# ── Helpers ──────────────────────────────────────────────────────────────

def _best_entry_zone(
    ctx: ICTContext,
    direction: str,
) -> tuple[Optional[FairValueGap], Optional[OrderBlock], str]:
    """Find the best entry zone (FVG and/or OB) for the direction."""
    best_fvg: Optional[FairValueGap] = None
    best_ob: Optional[OrderBlock] = None

    price = ctx.current_price

    # Find nearest FVG in the right direction
    for fvg in ctx.active_fvgs:
        if direction == "BUY" and fvg.kind == FVGType.BULLISH:
            # Price should be near or inside the FVG
            if fvg.low <= price <= fvg.high * 1.002:
                best_fvg = fvg
                break
        elif direction == "SELL" and fvg.kind == FVGType.BEARISH:
            if fvg.low * 0.998 <= price <= fvg.high:
                best_fvg = fvg
                break

    # Find nearest OB in the right direction
    for ob in ctx.active_obs:
        if direction == "BUY" and ob.kind == OBType.BULLISH:
            if ob.low <= price <= ob.high * 1.002:
                best_ob = ob
                break
        elif direction == "SELL" and ob.kind == OBType.BEARISH:
            if ob.low * 0.998 <= price <= ob.high:
                best_ob = ob
                break

    zone = ""
    if best_fvg and best_ob:
        zone = "fvg+ob"
    elif best_fvg:
        zone = "fvg"
    elif best_ob:
        zone = "ob"

    return best_fvg, best_ob, zone


def _recent_sweep(ctx: ICTContext, direction: str) -> Optional[LiquiditySweep]:
    """Find the most recent liquidity sweep aligned with the setup."""
    # For BUY: want a SSL sweep (sell-side swept = bullish intent)
    # For SELL: want a BSL sweep (buy-side swept = bearish intent)
    for sweep in reversed(ctx.recent_sweeps):
        if direction == "BUY" and sweep.level.kind.value == "sell_side":
            return sweep
        if direction == "SELL" and sweep.level.kind.value == "buy_side":
            return sweep
    return None


def _recent_mss(ctx: ICTContext, direction: str) -> Optional[StructureBreak]:
    """Find MSS aligned with direction."""
    if ctx.last_mss is None:
        return None
    mss = ctx.last_mss
    if direction == "BUY" and mss.direction == Bias.BULLISH:
        return mss
    if direction == "SELL" and mss.direction == Bias.BEARISH:
        return mss
    return None


def _calc_sl(
    ctx: ICTContext,
    direction: str,
    ob: Optional[OrderBlock] = None,
    fvg: Optional[FairValueGap] = None,
    sweep: Optional[LiquiditySweep] = None,
) -> tuple[float, str]:
    """Calculate stop loss — 0.786 Fib invalidation, or below OB/FVG/sweep + ATR buffer."""
    buffer = ctx.atr * 0.3 if ctx.atr > 0 else 0.0005  # small buffer

    # NEW: 0.786 Fibonacci invalidation (optimal strict risk logic)
    if ctx.fibonacci:
        aligned = (direction == "BUY" and ctx.fibonacci.direction == Bias.BULLISH) or \
                  (direction == "SELL" and ctx.fibonacci.direction == Bias.BEARISH)
        if aligned:
            if direction == "BUY":
                return round(ctx.fibonacci.invalidation_price - buffer, 5), "fib_invalidation"
            else:
                return round(ctx.fibonacci.invalidation_price + buffer, 5), "fib_invalidation"

    if direction == "BUY":
        candidates = []
        if ob:
            candidates.append(ob.low)
        if fvg:
            candidates.append(fvg.low)
        if sweep:
            candidates.append(sweep.sweep_price)
        if candidates:
            sl = min(candidates) - buffer
            return round(sl, 5), "below_entry_zone"
        # Fallback: 1.5× ATR
        return round(ctx.current_price - ctx.atr * 1.5, 5), "atr_fallback"

    else:  # SELL
        candidates = []
        if ob:
            candidates.append(ob.high)
        if fvg:
            candidates.append(fvg.high)
        if sweep:
            candidates.append(sweep.sweep_price)
        if candidates:
            sl = max(candidates) + buffer
            return round(sl, 5), "above_entry_zone"
        return round(ctx.current_price + ctx.atr * 1.5, 5), "atr_fallback"


def _calc_tps(
    ctx: ICTContext,
    entry: float,
    sl: float,
    direction: str,
) -> tuple[float, float, float, str]:
    """Calculate 3 take-profit levels using Fib extensions, opposing liquidity, or RR.

    ATR multipliers are regime-aware:
      Trending: TP1×1.5  TP2×2.5  TP3×4.0  (TP4/runner uses TP4×6.0 via settings)
      Ranging: TP1×0.8  TP2×1.5  TP3×2.5  (tighter — price tends to range within ATR)
      Unknown/Volatile: fallback 1.5/2.5/3.5
    """
    risk = abs(entry - sl)
    if risk == 0:
        risk = ctx.atr if ctx.atr > 0 else 0.001

    # ── Regime-aware ATR multipliers ──────────────────────────────────
    _regime = ctx.htf_regime
    if _regime == Regime.TRENDING:
        m1, m2, m3 = (
            settings.TP_TRENDING_TP1_MULT,   # 1.5
            settings.TP_TRENDING_TP2_MULT,   # 2.5
            settings.TP_TRENDING_TP3_MULT,   # 4.0
        )
    elif _regime == Regime.RANGING:
        m1, m2, m3 = (
            settings.TP_RANGING_TP1_MULT,   # 0.8
            settings.TP_RANGING_TP2_MULT,   # 1.5
            settings.TP_RANGING_TP3_MULT,   # 2.5
        )
    else:
        m1, m2, m3 = 1.5, 2.5, 3.5  # volatile / unknown fallback

    # NEW: 1.0, -0.272, -0.618 Fibonacci institutional targets
    if ctx.fibonacci:
        aligned = (direction == "BUY" and ctx.fibonacci.direction == Bias.BULLISH) or \
                  (direction == "SELL" and ctx.fibonacci.direction == Bias.BEARISH)
        if aligned:
            fib = ctx.fibonacci
            return round(fib.ext_1_000, 5), round(fib.ext_neg_0_272, 5), round(fib.ext_neg_0_618, 5), "fib_extensions"

    if direction == "BUY":
        # Try to use BSL levels as targets
        above = sorted(
            [l for l in ctx.bsl_levels if l.price > entry],
            key=lambda l: l.price,
        )
        if len(above) >= 2:
            tp1 = above[0].price
            tp2 = above[1].price if len(above) > 1 else entry + risk * m2
            tp3 = above[2].price if len(above) > 2 else entry + risk * m3
            reason = "bsl_targets"
        else:
            tp1 = round(entry + risk * m1, 5)
            tp2 = round(entry + risk * m2, 5)
            tp3 = round(entry + risk * m3, 5)
            reason = "rr_based"
    else:
        below = sorted(
            [l for l in ctx.ssl_levels if l.price < entry],
            key=lambda l: l.price,
            reverse=True,
        )
        if len(below) >= 2:
            tp1 = below[0].price
            tp2 = below[1].price if len(below) > 1 else entry - risk * m2
            tp3 = below[2].price if len(below) > 2 else entry - risk * m3
            reason = "ssl_targets"
        else:
            tp1 = round(entry - risk * m1, 5)
            tp2 = round(entry - risk * m2, 5)
            tp3 = round(entry - risk * m3, 5)
            reason = "rr_based"

    return round(tp1, 5), round(tp2, 5), round(tp3, 5), reason


def _build_candidate(
    ctx: ICTContext,
    model: SetupModel,
    direction: str,
    reason: str,
    fvg: Optional[FairValueGap],
    ob: Optional[OrderBlock],
    sweep: Optional[LiquiditySweep],
    mss: Optional[StructureBreak],
    disp: Optional[Displacement],
    zone: str,
    missing: list[str],
) -> SetupCandidate:
    """Build a fully populated SetupCandidate."""
    entry = ctx.current_price

    # 1. Refine entry price to Golden Zone midpoint for optimal positioning
    if ctx.fibonacci:
        aligned = (direction == "BUY" and ctx.fibonacci.direction == Bias.BULLISH) or \
                  (direction == "SELL" and ctx.fibonacci.direction == Bias.BEARISH)
        if aligned:
            entry = ctx.fibonacci.golden_zone_mid

    # 2. Strict 0.786 SL invalidation
    sl, sl_reason = _calc_sl(ctx, direction, ob, fvg, sweep)

    # 3. Institutional Fib extension targets
    tp1, tp2, tp3, tp_reason = _calc_tps(ctx, entry, sl, direction)

    return SetupCandidate(
        model=model,
        symbol=ctx.symbol,
        direction=direction,
        entry_price=entry,
        stop_loss=sl,
        take_profit_1=tp1,
        take_profit_2=tp2,
        take_profit_3=tp3,
        timestamp=datetime.now(UTC),
        reason=reason,
        entry_zone=zone,
        sl_reason=sl_reason,
        tp_reason=tp_reason,
        htf_bias_aligned=(
            (direction == "BUY" and ctx.htf_bias == Bias.BULLISH)
            or (direction == "SELL" and ctx.htf_bias == Bias.BEARISH)
        ),
        premium_discount_aligned=(
            (direction == "BUY" and ctx.premium_discount == "discount")
            or (direction == "SELL" and ctx.premium_discount == "premium")
        ),
        liquidity_swept=sweep is not None,
        mss_confirmed=mss is not None,
        displacement_present=disp is not None,
        fvg_present=fvg is not None,
        ob_present=ob is not None,
        session_valid=ctx.session_info.in_killzone,
        rr_acceptable=_rr_ok(entry, sl, tp2 if tp2 else tp1),
        fibonacci_aligned=_fib_aligned(ctx, direction),
        in_golden_zone=_in_gz(ctx, direction),
        missing=missing,
        sweep=sweep,
        fvg=fvg,
        ob=ob,
        mss=mss,
        displacement=disp,
        invalidation_price=sl,
        invalidation_reason=sl_reason,
    )


def _rr_ok(entry: float, sl: float, tp: float) -> bool:
    risk = abs(entry - sl)
    reward = abs(tp - entry)
    return reward >= risk * 1.5 if risk > 0 else False


def _fib_aligned(ctx: ICTContext, direction: str) -> bool:
    """Check if Fibonacci direction matches setup direction."""
    fib = ctx.fibonacci
    if fib is None:
        return False
    return (
        (direction == "BUY" and fib.direction == Bias.BULLISH)
        or (direction == "SELL" and fib.direction == Bias.BEARISH)
    )


def _in_gz(ctx: ICTContext, direction: str) -> bool:
    """Check if current price is in Golden Zone for the direction."""
    fib = ctx.fibonacci
    if fib is None or not _fib_aligned(ctx, direction):
        return False
    return fib.retracement_depth == "golden_zone"


# ══════════════════════════════════════════════════════════════════════════
# MODEL 1 — Trend Continuation Long
# ══════════════════════════════════════════════════════════════════════════

def _trend_continuation_long(ctx: ICTContext) -> Optional[SetupCandidate]:
    """Bullish bias + discount zone + SSL sweep + MSS + entry at FVG/OB."""
    missing: list[str] = []

    # Must have bullish HTF bias
    if ctx.htf_bias != Bias.BULLISH:
        return None

    # Should be in discount
    if ctx.premium_discount != "discount":
        missing.append("not_in_discount")

    # Liquidity sweep (SSL)
    sweep = _recent_sweep(ctx, "BUY")
    if not sweep:
        missing.append("no_ssl_sweep")

    # MSS (bullish)
    mss = _recent_mss(ctx, "BUY")
    if not mss:
        missing.append("no_bullish_mss")

    # Entry zone
    fvg, ob, zone = _best_entry_zone(ctx, "BUY")
    if not fvg and not ob:
        missing.append("no_entry_zone")

    # Displacement
    disp = ctx.recent_displacement if ctx.displacement_active else None

    # Minimum requirements: bias + (sweep OR mss) + (fvg OR ob)
    has_catalyst = sweep is not None or mss is not None
    has_entry = fvg is not None or ob is not None
    if not has_catalyst or not has_entry:
        return None

    return _build_candidate(
        ctx, SetupModel.TREND_CONTINUATION_LONG, "BUY",
        "Trend continuation long: bullish HTF + discount + sweep SSL → MSS → FVG/OB entry",
        fvg, ob, sweep, mss, disp, zone, missing,
    )


# ══════════════════════════════════════════════════════════════════════════
# MODEL 2 — Trend Continuation Short
# ══════════════════════════════════════════════════════════════════════════

def _trend_continuation_short(ctx: ICTContext) -> Optional[SetupCandidate]:
    """Bearish bias + premium zone + BSL sweep + MSS + entry at FVG/OB."""
    missing: list[str] = []

    if ctx.htf_bias != Bias.BEARISH:
        return None

    if ctx.premium_discount != "premium":
        missing.append("not_in_premium")

    sweep = _recent_sweep(ctx, "SELL")
    if not sweep:
        missing.append("no_bsl_sweep")

    mss = _recent_mss(ctx, "SELL")
    if not mss:
        missing.append("no_bearish_mss")

    fvg, ob, zone = _best_entry_zone(ctx, "SELL")
    if not fvg and not ob:
        missing.append("no_entry_zone")

    disp = ctx.recent_displacement if ctx.displacement_active else None

    has_catalyst = sweep is not None or mss is not None
    has_entry = fvg is not None or ob is not None
    if not has_catalyst or not has_entry:
        return None

    return _build_candidate(
        ctx, SetupModel.TREND_CONTINUATION_SHORT, "SELL",
        "Trend continuation short: bearish HTF + premium + sweep BSL → MSS → FVG/OB entry",
        fvg, ob, sweep, mss, disp, zone, missing,
    )


# ══════════════════════════════════════════════════════════════════════════
# MODEL 3 — Reversal After Sweep
# ══════════════════════════════════════════════════════════════════════════

def _reversal_after_sweep(ctx: ICTContext) -> Optional[SetupCandidate]:
    """Sweep of major liquidity + displacement reversal + MSS + FVG/OB."""
    if not ctx.recent_sweeps:
        return None

    # Find the most significant sweep
    sweep = ctx.recent_sweeps[-1]
    # Direction based on sweep: SSL sweep → BUY (reversal up), BSL sweep → SELL
    if sweep.level.kind.value == "sell_side":
        direction = "BUY"
    elif sweep.level.kind.value == "buy_side":
        direction = "SELL"
    else:
        return None

    missing: list[str] = []

    # Require MSS in the reversal direction
    mss = _recent_mss(ctx, direction)
    if not mss:
        missing.append("no_mss")

    # Require displacement
    disp = ctx.recent_displacement if ctx.displacement_active else None
    if not disp:
        missing.append("no_displacement")

    fvg, ob, zone = _best_entry_zone(ctx, direction)
    if not fvg and not ob:
        missing.append("no_entry_zone")

    # Must have MSS + (displacement or entry zone)
    if mss is None:
        return None
    if not disp and not fvg and not ob:
        return None

    return _build_candidate(
        ctx, SetupModel.REVERSAL_AFTER_SWEEP, direction,
        f"Reversal after sweep: {sweep.level.source} swept → MSS → {direction}",
        fvg, ob, sweep, mss, disp, zone, missing,
    )


# ══════════════════════════════════════════════════════════════════════════
# MODEL 4 — Range Dealing Long
# ══════════════════════════════════════════════════════════════════════════

def _range_dealing_long(ctx: ICTContext) -> Optional[SetupCandidate]:
    """Ranging regime + price at discount end + SSL sweep + entry at FVG/OB."""
    missing: list[str] = []

    # Prefer ranging regime (but don't require it strictly)
    if ctx.htf_regime not in (Regime.RANGING, Regime.UNKNOWN):
        if ctx.htf_bias != Bias.NEUTRAL:
            return None  # not ranging enough

    # Must be in discount
    if ctx.premium_discount != "discount":
        return None

    sweep = _recent_sweep(ctx, "BUY")
    if not sweep:
        missing.append("no_ssl_sweep")
        return None  # Sweep required for range model

    mss = _recent_mss(ctx, "BUY")
    if not mss:
        missing.append("no_mss")

    fvg, ob, zone = _best_entry_zone(ctx, "BUY")
    if not fvg and not ob:
        missing.append("no_entry_zone")
        return None

    disp = ctx.recent_displacement if ctx.displacement_active else None

    return _build_candidate(
        ctx, SetupModel.RANGE_DEALING_LONG, "BUY",
        "Range dealing long: discount zone + SSL sweep → FVG/OB entry → target premium",
        fvg, ob, sweep, mss, disp, zone, missing,
    )


# ══════════════════════════════════════════════════════════════════════════
# MODEL 5 — Range Dealing Short
# ══════════════════════════════════════════════════════════════════════════

def _range_dealing_short(ctx: ICTContext) -> Optional[SetupCandidate]:
    """Ranging regime + price at premium end + BSL sweep + entry at FVG/OB."""
    missing: list[str] = []

    if ctx.htf_regime not in (Regime.RANGING, Regime.UNKNOWN):
        if ctx.htf_bias != Bias.NEUTRAL:
            return None

    if ctx.premium_discount != "premium":
        return None

    sweep = _recent_sweep(ctx, "SELL")
    if not sweep:
        return None

    mss = _recent_mss(ctx, "SELL")
    if not mss:
        missing.append("no_mss")

    fvg, ob, zone = _best_entry_zone(ctx, "SELL")
    if not fvg and not ob:
        return None

    disp = ctx.recent_displacement if ctx.displacement_active else None

    return _build_candidate(
        ctx, SetupModel.RANGE_DEALING_SHORT, "SELL",
        "Range dealing short: premium zone + BSL sweep → FVG/OB entry → target discount",
        fvg, ob, sweep, mss, disp, zone, missing,
    )


# ══════════════════════════════════════════════════════════════════════════
# MODEL 6 — Session Sweep Reversal
# ══════════════════════════════════════════════════════════════════════════

def _session_sweep_reversal(ctx: ICTContext) -> Optional[SetupCandidate]:
    """Sweep of session level (Asian range, PDH/PDL) → reversal."""
    si = ctx.session_info

    # Must be in a killzone
    if not si.in_killzone:
        return None

    if not ctx.recent_sweeps:
        return None

    # Look for sweep of session-specific levels
    sweep = None
    direction = ""
    for s in reversed(ctx.recent_sweeps):
        source = s.level.source
        if source in ("pdh", "session_high", "asian_high", "pwh"):
            sweep = s
            direction = "SELL"  # Swept highs → expect reversal down
            break
        if source in ("pdl", "session_low", "asian_low", "pwl"):
            sweep = s
            direction = "BUY"  # Swept lows → expect reversal up
            break

    if sweep is None or not direction:
        return None

    missing: list[str] = []

    mss = _recent_mss(ctx, direction)
    if not mss:
        missing.append("no_mss")

    disp = ctx.recent_displacement if ctx.displacement_active else None
    if not disp:
        missing.append("no_displacement")

    fvg, ob, zone = _best_entry_zone(ctx, direction)
    if not fvg and not ob:
        missing.append("no_entry_zone")

    # Require at least MSS or displacement
    if mss is None and disp is None:
        return None

    return _build_candidate(
        ctx, SetupModel.SESSION_SWEEP_REVERSAL, direction,
        f"Session sweep reversal: {sweep.level.source} swept during {si.session.value} killzone",
        fvg, ob, sweep, mss, disp, zone, missing,
    )
