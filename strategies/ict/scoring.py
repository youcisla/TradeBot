"""Scoring Engine — compute the 0-100 ICT confidence score.

Implements ConfidenceBreakdown with 10 weighted components:
  htf_bias        0-15   HTF directional alignment
  premium_discount 0-12  Correct zone for the direction
  liquidity_sweep  0-15  Sweep quality and recency
  mss_quality      0-15  Market structure shift confirmation
  displacement     0-10  Impulsive intent confirmation
  fvg_quality      0-8   Fair value gap presence and zone
  ob_quality       0-8   Order block confluence
  session_time     0-7   Trading during killzone / macro
  target_clarity   0-5   Clear opposing liquidity for TP
  rr_quality       0-5   Risk-reward ratio quality
                 -----
  Total             100
"""

from __future__ import annotations

from models.ict_models import (
    Bias, Regime, SessionName,
    ICTContext, SetupCandidate, ConfidenceBreakdown,
)


def score_setup(ctx: ICTContext, setup: SetupCandidate) -> ConfidenceBreakdown:
    """Score a SetupCandidate against the full ICTContext."""
    bd = ConfidenceBreakdown()

    bd.htf_bias = _score_htf_bias(ctx, setup)
    bd.premium_discount = _score_premium_discount(ctx, setup)
    bd.liquidity_sweep = _score_liquidity_sweep(ctx, setup)
    bd.mss_quality = _score_mss(ctx, setup)
    bd.displacement = _score_displacement(ctx, setup)
    bd.fvg_quality = _score_fvg(ctx, setup)
    bd.ob_quality = _score_ob(ctx, setup)
    bd.session_time = _score_session(ctx)
    bd.target_clarity = _score_target(ctx, setup)
    bd.rr_quality = _score_rr(setup)

    bd.compute_total()
    return bd


# ── Component scorers ────────────────────────────────────────────────────

def _score_htf_bias(ctx: ICTContext, setup: SetupCandidate) -> float:
    """0-15: How well does HTF bias align with the setup direction?"""
    if ctx.htf_bias == Bias.NEUTRAL:
        return 5.0  # neutral = partial credit

    aligned = (
        (setup.direction == "BUY" and ctx.htf_bias == Bias.BULLISH)
        or (setup.direction == "SELL" and ctx.htf_bias == Bias.BEARISH)
    )
    if aligned:
        # Bonus for trending regime
        if ctx.htf_regime == Regime.TRENDING:
            return 15.0
        return 12.0

    # Counter-trend
    return 2.0


def _score_premium_discount(ctx: ICTContext, setup: SetupCandidate) -> float:
    """0-12: Is price in the correct zone for the setup direction?"""
    zone = ctx.premium_discount

    if setup.direction == "BUY" and zone == "discount":
        return 12.0
    if setup.direction == "SELL" and zone == "premium":
        return 12.0
    if zone == "equilibrium":
        return 6.0

    # Wrong zone (buying in premium or selling in discount)
    return 2.0


def _score_liquidity_sweep(ctx: ICTContext, setup: SetupCandidate) -> float:
    """0-15: Was there a recent liquidity sweep supporting the direction?"""
    if not setup.liquidity_swept:
        return 0.0

    score = 10.0

    # Recency bonus: sweep in last 3 candles
    if setup.sweep and ctx.candles:
        candles_ago = len(ctx.candles) - 1 - setup.sweep.sweep_candle_idx
        if candles_ago <= 3:
            score += 3.0
        elif candles_ago <= 6:
            score += 1.0

    # Strength bonus: multi-touch level
    if setup.sweep and setup.sweep.level.strength >= 3:
        score += 2.0

    return min(score, 15.0)


def _score_mss(ctx: ICTContext, setup: SetupCandidate) -> float:
    """0-15: Quality of market structure shift."""
    if not setup.mss_confirmed:
        return 0.0

    score = 8.0

    if setup.mss:
        # Displacement confirmed MSS is stronger
        if setup.mss.displacement_confirmed:
            score += 5.0

        # MSS aligned with setup direction
        aligned = (
            (setup.direction == "BUY" and setup.mss.direction == Bias.BULLISH)
            or (setup.direction == "SELL" and setup.mss.direction == Bias.BEARISH)
        )
        if aligned:
            score += 2.0

    return min(score, 15.0)


def _score_displacement(ctx: ICTContext, setup: SetupCandidate) -> float:
    """0-10: Displacement quality."""
    if not setup.displacement_present:
        return 0.0

    score = 5.0

    if setup.displacement:
        # Higher ratio = stronger displacement
        if setup.displacement.ratio >= 3.0:
            score += 3.0
        elif setup.displacement.ratio >= 2.0:
            score += 1.5

        # Created FVG = very strong
        if setup.displacement.created_fvg:
            score += 2.0

    return min(score, 10.0)


def _score_fvg(ctx: ICTContext, setup: SetupCandidate) -> float:
    """0-8: FVG quality and zone alignment."""
    if not setup.fvg_present:
        return 0.0

    score = 4.0

    if setup.fvg:
        # FVG in correct zone
        if setup.direction == "BUY" and setup.fvg.in_discount:
            score += 2.0
        elif setup.direction == "SELL" and setup.fvg.in_premium:
            score += 2.0

        # HTF FVG alignment
        htf_aligned = any(
            (setup.direction == "BUY" and f.kind.value == "bullish")
            or (setup.direction == "SELL" and f.kind.value == "bearish")
            for f in ctx.htf_fvgs
        )
        if htf_aligned:
            score += 2.0

    return min(score, 8.0)


def _score_ob(ctx: ICTContext, setup: SetupCandidate) -> float:
    """0-8: Order block quality."""
    if not setup.ob_present:
        return 0.0

    score = 4.0

    if setup.ob:
        if setup.ob.high_probability:
            score += 4.0
        else:
            # Partial confluence bonus
            if setup.ob.has_fvg:
                score += 1.0
            if setup.ob.has_displacement:
                score += 1.0

    return min(score, 8.0)


def _score_session(ctx: ICTContext) -> float:
    """0-7: Session/time quality."""
    si = ctx.session_info

    if si.session == SessionName.OFF_HOURS:
        return 0.0

    score = 2.0  # Base credit for being in a session

    if si.in_killzone:
        score += 3.0
    if si.in_macro:
        score += 1.5
    if si.session == SessionName.OVERLAP:
        score += 0.5

    return min(score, 7.0)


def _score_target(ctx: ICTContext, setup: SetupCandidate) -> float:
    """0-5: Clarity of take-profit target (opposing liquidity)."""
    if setup.direction == "BUY":
        # Check if there's clear BSL above for targets
        if ctx.nearest_bsl and ctx.nearest_bsl.price > ctx.current_price:
            return 5.0
        if ctx.bsl_levels:
            return 3.0
    elif setup.direction == "SELL":
        if ctx.nearest_ssl and ctx.nearest_ssl.price < ctx.current_price:
            return 5.0
        if ctx.ssl_levels:
            return 3.0

    return 1.0


def _score_rr(setup: SetupCandidate) -> float:
    """0-5: Risk-reward ratio quality."""
    if setup.entry_price == 0 or setup.stop_loss == 0 or setup.take_profit_1 == 0:
        return 0.0

    risk = abs(setup.entry_price - setup.stop_loss)
    if risk == 0:
        return 0.0

    reward = abs(setup.take_profit_2 - setup.entry_price) if setup.take_profit_2 else abs(setup.take_profit_1 - setup.entry_price)
    rr = reward / risk

    if rr >= 3.0:
        return 5.0
    if rr >= 2.0:
        return 4.0
    if rr >= 1.5:
        return 3.0
    if rr >= 1.0:
        return 2.0
    return 0.0
