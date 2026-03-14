"""ICT / Smart Money Concepts data models.

Every data structure produced by the ICT engines lives here so that
strategies, the dashboard, and the learning system can share a single
vocabulary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Optional


# ── Enums ────────────────────────────────────────────────────────────────

class Bias(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class Regime(str, Enum):
    TRENDING = "trending"
    RANGING = "ranging"
    REVERSING = "reversing"
    VOLATILE = "volatile"
    UNKNOWN = "unknown"


class LiquidityType(str, Enum):
    BSL = "buy_side"   # equal highs / swing highs
    SSL = "sell_side"  # equal lows  / swing lows


class FVGType(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class OBType(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class SetupModel(str, Enum):
    TREND_CONTINUATION_LONG = "trend_continuation_long"
    TREND_CONTINUATION_SHORT = "trend_continuation_short"
    REVERSAL_AFTER_SWEEP = "reversal_after_sweep"
    RANGE_DEALING_LONG = "range_dealing_long"
    RANGE_DEALING_SHORT = "range_dealing_short"
    SESSION_SWEEP_REVERSAL = "session_sweep_reversal"


class SessionName(str, Enum):
    ASIAN = "asian"
    LONDON = "london"
    NEW_YORK = "new_york"
    OVERLAP = "overlap"
    OFF_HOURS = "off_hours"


# ── Swing Points ─────────────────────────────────────────────────────────

@dataclass
class SwingPoint:
    """A local high or low in price action."""
    index: int = 0                # candle index in the series
    price: float = 0.0
    is_high: bool = True          # True = swing high, False = swing low
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    broken: bool = False          # has price traded through this level?


# ── Liquidity ────────────────────────────────────────────────────────────

@dataclass
class LiquidityLevel:
    """A mapped liquidity pool (buy-side or sell-side)."""
    price: float = 0.0
    kind: LiquidityType = LiquidityType.BSL
    source: str = ""              # "swing_high", "equal_highs", "pdh", "session_high", …
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    swept: bool = False
    sweep_time: Optional[datetime] = None
    strength: int = 1             # how many touches / equal levels clustered


@dataclass
class LiquiditySweep:
    """Record of a completed liquidity sweep."""
    level: LiquidityLevel = field(default_factory=LiquidityLevel)
    sweep_price: float = 0.0
    sweep_candle_idx: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ── Market Structure ─────────────────────────────────────────────────────

@dataclass
class StructureBreak:
    """A break-of-structure (BOS) or market-structure-shift (MSS)."""
    kind: str = "BOS"             # "BOS" or "MSS"
    direction: Bias = Bias.NEUTRAL
    break_price: float = 0.0
    broken_swing: SwingPoint = field(default_factory=SwingPoint)
    candle_idx: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    displacement_confirmed: bool = False


@dataclass
class DealingRange:
    """A dealing range (Highs-to-Lows) used for premium/discount."""
    high: float = 0.0
    low: float = 0.0
    equilibrium: float = 0.0     # midpoint
    premium_start: float = 0.0   # above EQ
    discount_end: float = 0.0    # below EQ
    is_parent: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.high > 0 and self.low > 0:
            self.equilibrium = round((self.high + self.low) / 2, 5)
            self.premium_start = self.equilibrium
            self.discount_end = self.equilibrium

    def is_premium(self, price: float) -> bool:
        return price > self.equilibrium

    def is_discount(self, price: float) -> bool:
        return price < self.equilibrium

    def zone_label(self, price: float) -> str:
        if self.high == 0:
            return "unknown"
        if price > self.equilibrium:
            return "premium"
        return "discount"


# ── Displacement ─────────────────────────────────────────────────────────

@dataclass
class Displacement:
    """An impulsive candle / move that signals intent."""
    direction: Bias = Bias.NEUTRAL
    candle_idx: int = 0
    body_size: float = 0.0
    avg_body: float = 0.0        # recent average for comparison
    ratio: float = 0.0           # body_size / avg_body
    created_fvg: bool = False
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


# ── Fibonacci ────────────────────────────────────────────────────────────

@dataclass
class FibonacciLevel:
    """A single Fibonacci retracement level."""
    ratio: float = 0.0           # 0.382, 0.5, 0.618, 0.705, 0.786
    price: float = 0.0
    label: str = ""              # "0.382", "0.618 (GZ top)", etc.


@dataclass
class FibonacciRetracement:
    """Fibonacci retracement anchored to a displacement leg."""
    direction: Bias = Bias.NEUTRAL       # BULLISH = low→high leg
    anchor_low: float = 0.0              # leg low  (swing low)
    anchor_high: float = 0.0             # leg high (displacement candle)
    levels: list[FibonacciLevel] = field(default_factory=list)
    golden_zone_top: float = 0.0         # 0.618 retracement price
    golden_zone_bottom: float = 0.0      # 0.705 retracement price
    golden_zone_mid: float = 0.0         # midpoint of GZ (optimal entry)
    anchor_displacement: Optional[Displacement] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    # Confluence flags
    gz_fvg_confluence: bool = False       # Golden Zone overlaps FVG CE
    gz_ob_confluence: bool = False        # Golden Zone overlaps OB mean_threshold
    gz_ce_confluence: bool = False        # Golden Zone overlaps CE specifically
    has_liquidity_target: bool = False    # Clear target exists
    # Retracement depth
    retracement_depth: str = ""           # "too_shallow", "acceptable", "golden_zone", "too_deep"
    # Invalidation (0.786 level) — used for SL placement
    invalidation_price: float = 0.0      # 0.786 fib level price
    # Extension levels — used for TP targets
    ext_1_000: float = 0.0               # full leg target (displacement high/low)
    ext_neg_0_272: float = 0.0           # -0.272 extension
    ext_neg_0_618: float = 0.0           # -0.618 extension


# ── Fair Value Gap ───────────────────────────────────────────────────────

@dataclass
class FairValueGap:
    """An imbalance / fair value gap in price."""
    kind: FVGType = FVGType.BULLISH
    high: float = 0.0            # upper boundary
    low: float = 0.0             # lower boundary
    ce: float = 0.0              # consequent encroachment (midpoint)
    candle_idx: int = 0          # index of the middle candle
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    filled: bool = False
    fill_time: Optional[datetime] = None
    failed: bool = False         # body close through = invalidated
    timeframe: str = "H1"
    in_discount: bool = False    # was it formed in discount zone?
    in_premium: bool = False

    def __post_init__(self) -> None:
        if self.high > 0 and self.low > 0:
            self.ce = round((self.high + self.low) / 2, 5)

    def contains(self, price: float) -> bool:
        return self.low <= price <= self.high


# ── Order Block ──────────────────────────────────────────────────────────

@dataclass
class OrderBlock:
    """A supply/demand zone (order block)."""
    kind: OBType = OBType.BULLISH
    high: float = 0.0            # OB upper boundary
    low: float = 0.0             # OB lower boundary
    open_price: float = 0.0      # opening price of the OB candle
    mean_threshold: float = 0.0  # (high + low) / 2
    candle_idx: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    valid: bool = True
    mitigated: bool = False      # price returned and traded through
    high_probability: bool = False
    timeframe: str = "H1"
    has_fvg: bool = False        # FVG in same zone
    has_liquidity_sweep: bool = False
    has_displacement: bool = False
    has_mss: bool = False

    def __post_init__(self) -> None:
        if self.high > 0 and self.low > 0:
            self.mean_threshold = round((self.high + self.low) / 2, 5)

    def contains(self, price: float) -> bool:
        return self.low <= price <= self.high


# ── Session / Time ───────────────────────────────────────────────────────

@dataclass
class SessionInfo:
    """Current session and macro-window state."""
    session: SessionName = SessionName.OFF_HOURS
    in_killzone: bool = False
    in_macro: bool = False
    macro_name: str = ""          # e.g. "london_open", "ny_am", "ny_lunch"
    session_high: float = 0.0
    session_low: float = 0.0
    prev_day_high: float = 0.0
    prev_day_low: float = 0.0
    prev_week_high: float = 0.0
    prev_week_low: float = 0.0
    asian_high: float = 0.0
    asian_low: float = 0.0
    quality_score: float = 0.0   # 0-1, how good the current window is


# ── ICT Analysis Result ─────────────────────────────────────────────────

@dataclass
class ICTContext:
    """Complete ICT analysis output for one symbol at one point in time.

    This is the master object passed to the setup detector and the
    dashboard.  Every layer writes into it.
    """
    symbol: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Layer A — HTF Bias
    htf_bias: Bias = Bias.NEUTRAL
    htf_regime: Regime = Regime.UNKNOWN
    draw_on_liquidity: str = ""   # "buy_side" / "sell_side" / "unknown"
    premium_discount: str = ""    # "premium" / "discount" / "equilibrium"

    # Layer B — Liquidity
    bsl_levels: list[LiquidityLevel] = field(default_factory=list)
    ssl_levels: list[LiquidityLevel] = field(default_factory=list)
    recent_sweeps: list[LiquiditySweep] = field(default_factory=list)
    nearest_bsl: Optional[LiquidityLevel] = None
    nearest_ssl: Optional[LiquidityLevel] = None

    # Layer C — Structure
    structure_bias: Bias = Bias.NEUTRAL
    last_bos: Optional[StructureBreak] = None
    last_mss: Optional[StructureBreak] = None
    dealing_range: DealingRange = field(default_factory=DealingRange)
    swing_highs: list[SwingPoint] = field(default_factory=list)
    swing_lows: list[SwingPoint] = field(default_factory=list)

    # Layer D — Displacement
    recent_displacement: Optional[Displacement] = None
    displacement_active: bool = False

    # Layer H — Fibonacci
    fibonacci: Optional[FibonacciRetracement] = None

    # Layer E — FVG
    active_fvgs: list[FairValueGap] = field(default_factory=list)
    htf_fvgs: list[FairValueGap] = field(default_factory=list)

    # Layer F — Order Blocks
    active_obs: list[OrderBlock] = field(default_factory=list)
    htf_obs: list[OrderBlock] = field(default_factory=list)

    # Layer G — Session / Time
    session_info: SessionInfo = field(default_factory=SessionInfo)

    # Prices
    current_price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    atr: float = 0.0

    # Raw candles for sub-engines
    candles: list = field(default_factory=list)         # execution TF
    htf_candles: list = field(default_factory=list)     # higher TF


# ── Setup Candidate ──────────────────────────────────────────────────────

@dataclass
class SetupCandidate:
    """A fully formed trade setup candidate before risk check."""
    model: SetupModel = SetupModel.TREND_CONTINUATION_LONG
    symbol: str = ""
    direction: str = ""          # "BUY" / "SELL"
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit_1: float = 0.0
    take_profit_2: float = 0.0
    take_profit_3: float = 0.0
    confidence: float = 0.0      # 0-100
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Narrative
    reason: str = ""
    entry_zone: str = ""         # "fvg", "ob", "fvg+ob"
    sl_reason: str = ""
    tp_reason: str = ""

    # Confluences present
    htf_bias_aligned: bool = False
    premium_discount_aligned: bool = False
    liquidity_swept: bool = False
    mss_confirmed: bool = False
    displacement_present: bool = False
    fvg_present: bool = False
    ob_present: bool = False
    session_valid: bool = False
    rr_acceptable: bool = False
    fibonacci_aligned: bool = False
    in_golden_zone: bool = False

    # Missing confluences
    missing: list[str] = field(default_factory=list)

    # References
    sweep: Optional[LiquiditySweep] = None
    fvg: Optional[FairValueGap] = None
    ob: Optional[OrderBlock] = None
    mss: Optional[StructureBreak] = None
    displacement: Optional[Displacement] = None

    # Invalidation
    invalidation_price: float = 0.0
    invalidation_reason: str = ""


# ── Scoring Breakdown ────────────────────────────────────────────────────

@dataclass
class ConfidenceBreakdown:
    """Detailed breakdown of how an ICT confidence score was computed."""
    htf_bias: float = 0.0        # 0-15
    premium_discount: float = 0.0  # 0-12
    liquidity_sweep: float = 0.0  # 0-15
    mss_quality: float = 0.0     # 0-15
    displacement: float = 0.0    # 0-10
    fvg_quality: float = 0.0     # 0-8
    ob_quality: float = 0.0      # 0-8
    session_time: float = 0.0    # 0-7
    target_clarity: float = 0.0  # 0-5
    rr_quality: float = 0.0      # 0-5
    fibonacci_quality: float = 0.0  # 0-15  (Golden Zone + confluence)
    total: float = 0.0           # sum, 0-115

    def compute_total(self) -> float:
        self.total = round(
            self.htf_bias + self.premium_discount + self.liquidity_sweep
            + self.mss_quality + self.displacement + self.fvg_quality
            + self.ob_quality + self.session_time + self.target_clarity
            + self.rr_quality + self.fibonacci_quality, 1
        )
        return self.total
