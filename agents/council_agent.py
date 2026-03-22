"""Trading Council Agent — pure-code multi-expert quality gate.

Three distinct algorithmic trading experts independently analyse every signal
using their own methodology.  Their scores are averaged and the trade is
approved only if the combined confidence reaches the configured threshold
(default 80 %).

Experts
-------
1. ICT Expert       — FVGs, Order Blocks, liquidity sweeps, killzones
2. DanialFX Expert  — Fibonacci golden zone, S/D zones, AO momentum, BBMA
3. Traditional Expert — RSI, SMA alignment, HH/HL structure, volume

Integration point: between strategy signal ranking and risk validation.
If COUNCIL_ENABLED=False (default), signals pass through unchanged.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from config import settings
from models.signal import Signal

if TYPE_CHECKING:
    from models.market_data import Candle, MarketContext

logger = logging.getLogger(__name__)


# ── Result dataclasses ───────────────────────────────────────────────────────

@dataclass
class ExpertVerdict:
    score: float                          # 0.0 – 1.0
    reasons_for: list[str] = field(default_factory=list)
    reasons_against: list[str] = field(default_factory=list)


@dataclass
class CouncilVerdict:
    approved: bool
    confidence: float                     # 0.0 – 1.0
    direction: str = ""
    ict_score: float = 0.0
    danial_score: float = 0.0
    traditional_score: float = 0.0
    reasons_for: list[str] = field(default_factory=list)
    reasons_against: list[str] = field(default_factory=list)
    reasoning: str = ""


# ── Helper utilities ─────────────────────────────────────────────────────────

def _recent(candles: list["Candle"], n: int) -> list["Candle"]:
    return candles[-n:] if len(candles) >= n else candles


# ══════════════════════════════════════════════════════════════════════════════
# Expert 1 — ICT (Inner Circle Trader)
# Methodology: FVGs, Order Blocks, liquidity sweeps, killzones, MSS
# ══════════════════════════════════════════════════════════════════════════════

class ICTExpert:
    """ICT methodology: market manipulation via time, price, and liquidity."""

    # UTC hour ranges for high-probability ICT killzones
    _KILLZONES = [
        (7, 10),   # London open
        (12, 16),  # New York open / overlap
        (20, 22),  # New York close / Asian setup
    ]

    def analyse(self, signal: Signal, context: "MarketContext") -> ExpertVerdict:
        verdict = ExpertVerdict(score=0.0)
        passed = 0

        # 1. Killzone timing
        if self._in_killzone():
            passed += 1
            verdict.reasons_for.append("Entry is within an ICT killzone")
        else:
            verdict.reasons_against.append("Entry is outside ICT killzones")

        # 2. Fair Value Gap near entry
        if self._fvg_near_entry(signal, context):
            passed += 1
            verdict.reasons_for.append("Fair Value Gap present near entry price")
        else:
            verdict.reasons_against.append("No Fair Value Gap detected near entry")

        # 3. Order Block near entry
        if self._order_block_near_entry(signal, context):
            passed += 1
            verdict.reasons_for.append("Order Block aligns with entry zone")
        else:
            verdict.reasons_against.append("No Order Block confluence at entry")

        # 4. Liquidity sweep before the move
        if self._liquidity_swept(signal, context):
            passed += 1
            verdict.reasons_for.append("Liquidity sweep confirms entry direction")
        else:
            verdict.reasons_against.append("No prior liquidity sweep detected")

        verdict.score = passed / 4
        return verdict

    # ── private checks ────────────────────────────────────────────────────

    def _in_killzone(self) -> bool:
        hour = datetime.now(UTC).hour
        return any(start <= hour < end for start, end in self._KILLZONES)

    def _tolerance(self, signal: Signal, context: "MarketContext",
                   atr_multiplier: float = 2.0) -> float:
        atr = context.atr
        if atr and atr > 0:
            return atr * atr_multiplier
        return abs(signal.entry_price - signal.stop_loss)

    def _fvg_near_entry(self, signal: Signal, context: "MarketContext") -> bool:
        """Fair Value Gap: 3-candle pattern where candle[i-2] and candle[i] do not overlap."""
        candles = context.candles
        if len(candles) < 3:
            return False
        tol = self._tolerance(signal, context, 2.0)

        for i in range(2, len(candles)):
            c0, c2 = candles[i - 2], candles[i]
            if signal.direction == "BUY":
                # Bullish FVG: gap between c0.high and c2.low (price must fill it going down)
                if c2.low > c0.high:
                    fvg_mid = (c0.high + c2.low) / 2
                    if abs(signal.entry_price - fvg_mid) <= tol:
                        return True
            else:
                # Bearish FVG: gap between c0.low and c2.high
                if c2.high < c0.low:
                    fvg_mid = (c0.low + c2.high) / 2
                    if abs(signal.entry_price - fvg_mid) <= tol:
                        return True
        return False

    def _order_block_near_entry(self, signal: Signal,
                                context: "MarketContext") -> bool:
        """Order Block: last opposing candle before a strong impulsive move."""
        candles = context.candles
        if len(candles) < 5:
            return False
        tol = self._tolerance(signal, context, 1.5)
        recent = _recent(candles, 20)

        for i in range(len(recent) - 3):
            c = recent[i]
            follow = recent[i + 1: i + 4]
            if signal.direction == "BUY":
                # Bullish OB: bearish candle followed by 3 closes above its high
                if c.close < c.open and all(
                    f.close > c.high for f in follow
                ):
                    ob_mid = (c.high + c.low) / 2
                    if abs(signal.entry_price - ob_mid) <= tol:
                        return True
            else:
                # Bearish OB: bullish candle followed by 3 closes below its low
                if c.close > c.open and all(
                    f.close < c.low for f in follow
                ):
                    ob_mid = (c.high + c.low) / 2
                    if abs(signal.entry_price - ob_mid) <= tol:
                        return True
        return False

    def _liquidity_swept(self, signal: Signal, context: "MarketContext") -> bool:
        """Liquidity sweep: price broke a prior swing extreme then reversed."""
        candles = context.candles
        if len(candles) < 20:
            return False

        prior = _recent(candles[:-10], 10)   # candles[-20:-10]
        recent = candles[-10:]
        if not prior:
            return False

        if signal.direction == "BUY":
            prior_low = min(c.low for c in prior)
            swept = any(c.low < prior_low for c in recent)
            recovered = recent[-1].close > prior_low
            return swept and recovered
        else:
            prior_high = max(c.high for c in prior)
            swept = any(c.high > prior_high for c in recent)
            recovered = recent[-1].close < prior_high
            return swept and recovered


# ══════════════════════════════════════════════════════════════════════════════
# Expert 2 — DanialFX (Ahmad Danial methodology)
# Methodology: Fibonacci golden zone, S/D zones, AO momentum, BBMA
# ══════════════════════════════════════════════════════════════════════════════

class DanialFXExpert:
    """DanialFX: high-probability entries at structural extremes with momentum."""

    _FIBO_LOW = 0.618   # golden zone lower bound
    _FIBO_HIGH = 0.705  # golden zone upper bound

    def analyse(self, signal: Signal, context: "MarketContext") -> ExpertVerdict:
        verdict = ExpertVerdict(score=0.0)
        passed = 0

        # 1. Fibonacci golden zone (61.8% – 70.5% retracement)
        if self._in_fibo_golden_zone(signal, context):
            passed += 1
            verdict.reasons_for.append(
                "Entry within Fibonacci 61.8%–70.5% golden zone"
            )
        else:
            verdict.reasons_against.append("Entry not in Fibonacci golden zone")

        # 2. Supply / Demand zone alignment
        if self._sd_zone_aligned(signal, context):
            passed += 1
            verdict.reasons_for.append("Supply/Demand zone aligns with entry")
        else:
            verdict.reasons_against.append("No S/D zone confluence at entry")

        # 3. Awesome Oscillator momentum (5-bar vs 34-bar midprice SMA)
        if self._ao_momentum_aligned(signal, context):
            passed += 1
            verdict.reasons_for.append("AO momentum supports entry direction")
        else:
            verdict.reasons_against.append(
                "AO momentum does not support entry direction"
            )

        # 4. BBMA: price interacting with the slow MA in entry direction
        if self._bbma_aligned(signal, context):
            passed += 1
            verdict.reasons_for.append(
                "BBMA: price interacting with MA as dynamic S/R"
            )
        else:
            verdict.reasons_against.append("BBMA: price not in BBMA entry zone")

        verdict.score = passed / 4
        return verdict

    # ── private checks ────────────────────────────────────────────────────

    def _in_fibo_golden_zone(self, signal: Signal,
                             context: "MarketContext") -> bool:
        candles = context.candles
        if len(candles) < 10:
            return False
        recent = _recent(candles, 40)
        swing_high = max(c.high for c in recent)
        swing_low = min(c.low for c in recent)
        rng = swing_high - swing_low
        if rng <= 0:
            return False

        if signal.direction == "BUY":
            # Retracement from high: golden zone sits between 61.8% and 70.5%
            # measured from the top downward
            fib_top = swing_high - rng * self._FIBO_LOW    # higher price
            fib_bot = swing_high - rng * self._FIBO_HIGH   # lower price
            return fib_bot <= signal.entry_price <= fib_top
        else:
            # Retracement from low
            fib_bot = swing_low + rng * self._FIBO_LOW
            fib_top = swing_low + rng * self._FIBO_HIGH
            return fib_bot <= signal.entry_price <= fib_top

    def _sd_zone_aligned(self, signal: Signal, context: "MarketContext") -> bool:
        """Supply/Demand zone: 3+ candles with small bodies (consolidation)
        that the entry price falls within."""
        candles = context.candles
        if len(candles) < 6:
            return False
        atr = context.atr
        if not atr or atr <= 0:
            return False
        recent = _recent(candles, 30)

        for i in range(len(recent) - 3):
            group = recent[i:i + 3]
            # Consolidation: body < 30 % of ATR
            if all(abs(c.close - c.open) < atr * 0.30 for c in group):
                zone_high = max(c.high for c in group)
                zone_low = min(c.low for c in group)
                if zone_low <= signal.entry_price <= zone_high:
                    return True
        return False

    def _ao_momentum_aligned(self, signal: Signal,
                             context: "MarketContext") -> bool:
        """AO = (5-bar midprice SMA) − (34-bar midprice SMA).
        Positive → bullish momentum; negative → bearish momentum."""
        candles = context.candles
        if len(candles) < 34:
            return False
        mids = [(c.high + c.low) / 2 for c in candles]
        ao_fast = sum(mids[-5:]) / 5
        ao_slow = sum(mids[-34:]) / 34
        ao = ao_fast - ao_slow
        return ao > 0 if signal.direction == "BUY" else ao < 0

    def _bbma_aligned(self, signal: Signal, context: "MarketContext") -> bool:
        """BBMA: price near the slow SMA (dynamic support/resistance),
        approaching from the correct side."""
        sma_slow = context.sma_slow
        if not sma_slow or sma_slow <= 0:
            return False
        atr = context.atr or 0.0
        tol = atr if atr > 0 else abs(signal.entry_price - signal.stop_loss) * 0.5

        near_ma = abs(signal.entry_price - sma_slow) <= tol
        if signal.direction == "BUY":
            return near_ma and signal.entry_price >= sma_slow
        else:
            return near_ma and signal.entry_price <= sma_slow


# ══════════════════════════════════════════════════════════════════════════════
# Expert 3 — Traditional (The Anchor)
# Methodology: RSI, SMA alignment, HH/HL price structure, volume
# ══════════════════════════════════════════════════════════════════════════════

class TraditionalExpert:
    """Traditional methodology: trend-following with classical indicators."""

    def analyse(self, signal: Signal, context: "MarketContext") -> ExpertVerdict:
        verdict = ExpertVerdict(score=0.0)
        passed = 0

        # 1. RSI alignment
        if self._rsi_aligned(signal, context):
            passed += 1
            verdict.reasons_for.append(
                f"RSI {context.rsi:.1f} aligned with {signal.direction}"
            )
        else:
            verdict.reasons_against.append(
                f"RSI {context.rsi:.1f} contradicts {signal.direction}"
            )

        # 2. Fast/slow SMA alignment
        if self._sma_aligned(signal, context):
            passed += 1
            verdict.reasons_for.append("SMA fast/slow alignment supports direction")
        else:
            verdict.reasons_against.append("SMA alignment contradicts direction")

        # 3. Price structure (HH/HL for BUY, LH/LL for SELL)
        if self._structure_aligned(signal, context):
            passed += 1
            verdict.reasons_for.append("Price structure (HH/HL or LH/LL) aligned")
        else:
            verdict.reasons_against.append(
                "Price structure does not support direction"
            )

        # 4. Volume sufficient (from entry snapshot flag)
        if signal.entry_snapshot.volume_sufficient:
            passed += 1
            verdict.reasons_for.append("Volume is sufficient — strong conviction")
        else:
            verdict.reasons_against.append(
                "Volume is insufficient — weak conviction"
            )

        verdict.score = passed / 4
        return verdict

    # ── private checks ────────────────────────────────────────────────────

    def _rsi_aligned(self, signal: Signal, context: "MarketContext") -> bool:
        rsi = context.rsi
        if signal.direction == "BUY":
            return 40.0 <= rsi <= 70.0   # above midpoint, not overbought
        else:
            return 30.0 <= rsi <= 60.0   # below midpoint, not oversold

    def _sma_aligned(self, signal: Signal, context: "MarketContext") -> bool:
        fast, slow = context.sma_fast, context.sma_slow
        if fast <= 0 or slow <= 0:
            return False
        return fast > slow if signal.direction == "BUY" else fast < slow

    def _structure_aligned(self, signal: Signal,
                           context: "MarketContext") -> bool:
        """HH/HL = bullish structure; LH/LL = bearish structure.
        Uses candle splits if enough data, otherwise falls back to
        the trend_direction field."""
        candles = context.candles
        if len(candles) < 6:
            if signal.direction == "BUY":
                return context.trend_direction == "bullish"
            return context.trend_direction == "bearish"

        recent = _recent(candles, 20)
        mid = len(recent) // 2
        first_highs = [c.high for c in recent[:mid]]
        second_highs = [c.high for c in recent[mid:]]
        first_lows = [c.low for c in recent[:mid]]
        second_lows = [c.low for c in recent[mid:]]

        if signal.direction == "BUY":
            return (max(second_highs) > max(first_highs)
                    and min(second_lows) > min(first_lows))
        else:
            return (max(second_highs) < max(first_highs)
                    and min(second_lows) < min(first_lows))


# ══════════════════════════════════════════════════════════════════════════════
# Council Agent — synthesises all three expert verdicts
# ══════════════════════════════════════════════════════════════════════════════

class CouncilAgent:
    """Runs three algorithmic trading experts and returns a combined verdict."""

    def __init__(self) -> None:
        self._ict = ICTExpert()
        self._danial = DanialFXExpert()
        self._traditional = TraditionalExpert()

    def review(self, signal: Signal, context: "MarketContext") -> CouncilVerdict:
        """Debate a signal and return a council verdict.

        Fails open on unexpected errors so trading is never blocked by a bug.
        """
        try:
            return self._run_council(signal, context)
        except Exception:
            logger.exception("Council unexpected error — failing open")
            return CouncilVerdict(
                approved=True,
                confidence=0.0,
                direction=signal.direction,
                reasoning="Council error — signal passed through unreviewed.",
            )

    def _run_council(self, signal: Signal,
                     context: "MarketContext") -> CouncilVerdict:
        ict = self._ict.analyse(signal, context)
        danial = self._danial.analyse(signal, context)
        traditional = self._traditional.analyse(signal, context)

        confidence = (ict.score + danial.score + traditional.score) / 3

        reasons_for = (
            ict.reasons_for + danial.reasons_for + traditional.reasons_for
        )
        reasons_against = (
            ict.reasons_against + danial.reasons_against
            + traditional.reasons_against
        )

        approved = confidence >= settings.COUNCIL_MIN_CONFIDENCE

        if approved:
            top_reasons = "; ".join(reasons_for[:3]) or "multiple confluences"
            reasoning = (
                f"ICT={ict.score:.0%} DanialFX={danial.score:.0%} "
                f"Traditional={traditional.score:.0%} → {confidence:.0%} — "
                f"APPROVED. Key confluences: {top_reasons}."
            )
        else:
            top_issues = "; ".join(reasons_against[:3]) or "insufficient confluences"
            reasoning = (
                f"ICT={ict.score:.0%} DanialFX={danial.score:.0%} "
                f"Traditional={traditional.score:.0%} → {confidence:.0%} — "
                f"REJECTED. Main issues: {top_issues}."
            )

        logger.info(
            "Council verdict for %s %s: ICT=%.0f%% DanialFX=%.0f%% "
            "Traditional=%.0f%% → %.0f%% → %s",
            signal.symbol, signal.direction,
            ict.score * 100, danial.score * 100, traditional.score * 100,
            confidence * 100,
            "APPROVED" if approved else "REJECTED",
        )

        return CouncilVerdict(
            approved=approved,
            confidence=confidence,
            direction=signal.direction,
            ict_score=ict.score,
            danial_score=danial.score,
            traditional_score=traditional.score,
            reasons_for=reasons_for,
            reasons_against=reasons_against,
            reasoning=reasoning,
        )
