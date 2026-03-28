"""ICT Engine Orchestrator — runs all analysis layers and setup detection.

This is the single entry point for ICT analysis.  Given raw candles
(execution TF + HTF), it:

1. Detects swing points and market structure (BOS/MSS)
2. Maps liquidity levels and detects sweeps
3. Detects displacement (impulsive moves)
4. Detects fair value gaps
5. Detects order blocks
6. Resolves session/time context
7. Resolves HTF bias and regime
8. Builds complete ICTContext
9. Runs all 6 setup model detectors
10. Scores each candidate
11. Returns the best SetupCandidate (or None)
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Optional

from models.market_data import Candle
from models.ict_models import (
    ICTContext, SetupCandidate, SetupModel,
)
from strategies.ict.structure import (
    find_swing_points, detect_structure_breaks,
    build_dealing_range, get_structure_bias,
)
from strategies.ict.liquidity import (
    map_liquidity, detect_sweeps, infer_draw_on_liquidity,
)
from strategies.ict.displacement import detect_displacement
from strategies.ict.fvg import detect_fvgs, update_fvg_status, get_active_fvgs
from strategies.ict.orderblock import (
    detect_order_blocks, update_ob_status, mark_high_probability, get_active_obs,
)
from strategies.ict.session import build_session_info
from strategies.ict.bias import (
    resolve_htf_bias, detect_regime, build_htf_dealing_range,
    classify_premium_discount,
)
from strategies.ict.scoring import score_setup
from strategies.ict.setups import detect_all_setups
from strategies.ict.fibonacci import (
    detect_fib_levels, check_golden_zone_confluence,
    check_liquidity_target, validate_retracement_depth,
)

logger = logging.getLogger(__name__)


class ICTEngine:
    """Stateless ICT analysis orchestrator.

    Usage::

        engine = ICTEngine()
        ctx, best, rejected = engine.analyze(
            symbol="EURUSD",
            candles=h1_candles,
            htf_candles=h4_candles,
            current_price=1.08550,
            bid=1.08548, ask=1.08552,
            atr=0.00120,
        )
    """

    def __init__(self, min_confidence: float = 50.0,
                 range_min_confidence: float = 42.0) -> None:
        self.min_confidence = min_confidence
        self.range_min_confidence = range_min_confidence

    def analyze(
        self,
        symbol: str,
        candles: list[Candle],
        htf_candles: list[Candle],
        current_price: float,
        bid: float = 0.0,
        ask: float = 0.0,
        atr: float = 0.0,
        timeframe: str = "H1",
    ) -> tuple[ICTContext, Optional[SetupCandidate], Optional[SetupCandidate]]:
        """Run the full ICT analysis pipeline.

        Returns (ICTContext, best_setup_or_None, rejected_setup_or_None).
        The third element is populated when a setup was found but scored
        below *min_confidence*.
        """
        ctx = ICTContext(
            symbol=symbol,
            timestamp=datetime.now(UTC),
            current_price=current_price,
            bid=bid,
            ask=ask,
            spread=round(ask - bid, 6) if bid and ask else 0.0,
            atr=atr,
            candles=candles,
            htf_candles=htf_candles,
        )

        if len(candles) < 20:
            logger.debug("Not enough candles for ICT analysis on %s", symbol)
            return ctx, None, None

        # ── Layer A: HTF Bias & Regime ───────────────────────────────
        ctx.htf_bias = resolve_htf_bias(htf_candles)
        ctx.htf_regime = detect_regime(htf_candles, atr)
        htf_dr = build_htf_dealing_range(htf_candles)
        ctx.premium_discount = classify_premium_discount(current_price, htf_dr)

        # ── Layer B: Structure (execution TF) ────────────────────────
        highs, lows = find_swing_points(candles)
        ctx.swing_highs = highs
        ctx.swing_lows = lows
        ctx.structure_bias = get_structure_bias(highs, lows)

        breaks = detect_structure_breaks(candles, highs, lows)
        for brk in breaks:
            if brk.kind == "MSS":
                ctx.last_mss = brk
            else:
                ctx.last_bos = brk

        ctx.dealing_range = build_dealing_range(highs, lows)

        # ── Layer C: Session / Time ──────────────────────────────────
        ts = candles[-1].timestamp if candles else datetime.now(UTC)
        ctx.session_info = build_session_info(candles, ts)

        # ── Layer D: Liquidity ───────────────────────────────────────
        bsl, ssl = map_liquidity(highs, lows, ctx.session_info, current_price)
        ctx.bsl_levels = bsl
        ctx.ssl_levels = ssl

        # Nearest levels
        above = [l for l in bsl if l.price > current_price]
        below = [l for l in ssl if l.price < current_price]
        if above:
            ctx.nearest_bsl = min(above, key=lambda l: l.price)
        if below:
            ctx.nearest_ssl = max(below, key=lambda l: l.price)

        sweeps = detect_sweeps(candles, bsl, ssl)
        ctx.recent_sweeps = sweeps

        ctx.draw_on_liquidity = infer_draw_on_liquidity(
            bsl, ssl, ctx.structure_bias.value, current_price,
        )

        # ── Layer E: Displacement ────────────────────────────────────
        displacements = detect_displacement(candles)
        if displacements:
            ctx.recent_displacement = displacements[-1]
            # Active if within last 5 candles
            candles_ago = len(candles) - 1 - displacements[-1].candle_idx
            ctx.displacement_active = candles_ago <= 5

        # ── Layer F: FVG ─────────────────────────────────────────────
        fvgs = detect_fvgs(candles, ctx.dealing_range, timeframe)
        update_fvg_status(fvgs, candles)
        ctx.active_fvgs = get_active_fvgs(fvgs, current_price)

        # HTF FVGs
        if htf_candles:
            htf_fvgs = detect_fvgs(htf_candles, htf_dr, "H4")
            update_fvg_status(htf_fvgs, htf_candles)
            ctx.htf_fvgs = get_active_fvgs(htf_fvgs, current_price)

        # ── Layer G: Order Blocks ────────────────────────────────────
        obs = detect_order_blocks(candles, displacements, timeframe)
        update_ob_status(obs, candles)
        mark_high_probability(obs, sweeps, breaks, fvgs)
        ctx.active_obs = get_active_obs(obs)

        # HTF OBs
        if htf_candles:
            htf_disps = detect_displacement(htf_candles)
            htf_obs = detect_order_blocks(htf_candles, htf_disps, "H4")
            update_ob_status(htf_obs, htf_candles)
            ctx.htf_obs = get_active_obs(htf_obs)

        # ── Layer H: Fibonacci ──────────────────────────────────────────
        fib = detect_fib_levels(
            candles, displacements, highs, lows, ctx.htf_bias,
        )
        if fib:
            check_golden_zone_confluence(fib, ctx.active_fvgs, ctx.active_obs)
            check_liquidity_target(
                fib, ctx.bsl_levels, ctx.ssl_levels, current_price,
            )
            validate_retracement_depth(fib, current_price)
            ctx.fibonacci = fib

        # ── Setup Detection ──────────────────────────────────────────
        candidates = detect_all_setups(ctx)

        if not candidates:
            logger.debug("No ICT setups found on %s", symbol)
            return ctx, None, None

        # ── Score & Select Best ──────────────────────────────────────
        best: Optional[SetupCandidate] = None
        best_score: float = 0.0

        for setup in candidates:
            breakdown = score_setup(ctx, setup)
            setup.confidence = breakdown.total

            if breakdown.total > best_score:
                best_score = breakdown.total
                best = setup

        # Filter by minimum confidence (range models use a lower bar
        # since they inherently lack HTF-bias points)
        if best:
            _is_range = best.model in (SetupModel.RANGE_DEALING_LONG,
                                       SetupModel.RANGE_DEALING_SHORT)
            threshold = self.range_min_confidence if _is_range else self.min_confidence
            if best.confidence < threshold:
                logger.debug(
                    "Best ICT setup on %s scored %.1f (min=%.1f) — skipping",
                    symbol, best.confidence, threshold,
                )
                # Return the rejected setup as second element so callers can log it
                return ctx, None, best

        if best:
            logger.info(
                "ICT setup: %s %s %s @ %.5f (conf=%.1f, model=%s)",
                symbol, best.direction, best.entry_zone,
                best.entry_price, best.confidence, best.model.value,
            )

        return ctx, best, None
