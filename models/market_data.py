from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional, TYPE_CHECKING  # noqa: F401 – Optional used in annotation string

if TYPE_CHECKING:
    from filters.crucix_client import MacroContext


@dataclass
class Candle:
    """Single OHLCV candle."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    open: float = 0.0
    high: float = 0.0
    low: float = 0.0
    close: float = 0.0
    volume: float = 0.0


@dataclass
class MarketData:
    """Raw market snapshot returned by MarketAgent."""

    symbol: str = ""
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    volume: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    candles: list[Candle] = field(default_factory=list)
    # Multi-timeframe candles (empty = not fetched)
    # Analysis TFs: M30 bridge, H4 structure, D1 bias
    # Entry TFs:    M15 trigger
    m30_candles: list[Candle] = field(default_factory=list)
    m15_candles: list[Candle] = field(default_factory=list)
    h4_candles: list[Candle] = field(default_factory=list)
    d1_candles: list[Candle] = field(default_factory=list)
    # Ultra-short horizon microstructure features from MarketAgent tick memory.
    shock_detected: bool = False
    tick_drop_pct: float = 0.0
    tick_drop_window_seconds: int = 0

    @property
    def mid_price(self) -> float:
        return round((self.bid + self.ask) / 2, 5)


@dataclass
class MarketContext:
    """Interpreted market context produced by AnalysisAgent."""

    symbol: str = ""
    current_price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    volume: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))

    # Technical indicators
    sma_fast: float = 0.0
    sma_slow: float = 0.0
    prev_sma_fast: float = 0.0
    prev_sma_slow: float = 0.0
    rsi: float = 50.0
    atr: float = 0.0

    # Regime
    timeframe: str = ""
    regime: str = "unknown"  # trending / ranging / volatile
    trend_direction: str = "neutral"  # bullish / bearish / neutral
    is_trending: bool = False
    session: str = "unknown"  # London / NY / Asian / overlap
    day_of_week: str = ""
    near_news_event: bool = False

    # ``trend`` is an alias for ``trend_direction`` accepted by tests and
    # external callers.  Set it alongside or instead of ``trend_direction``
    # and __post_init__ will reconcile them so downstream code that reads
    # ``trend_direction`` always gets the right value.
    trend: str = ""

    # Macro world context from Crucix (None if Crucix not running)
    macro: "Optional[MacroContext]" = None

    candles: list[Candle] = field(default_factory=list)
    # Multi-timeframe candles (empty = not fetched)
    m30_candles: list[Candle] = field(default_factory=list)
    m15_candles: list[Candle] = field(default_factory=list)
    h4_candles: list[Candle] = field(default_factory=list)
    d1_candles: list[Candle] = field(default_factory=list)
    # ADX value computed by AnalysisAgent (used by NeuralStrategy regime gate)
    adx: float = 0.0
    # Per-timeframe trend directions (bullish / bearish / neutral)
    m30_trend: str = "neutral"
    h4_trend: str = "neutral"
    d1_trend: str = "neutral"
    # MTF alignment: fraction of analysis TFs agreeing with H1 (0.0–1.0)
    # and a label: "aligned_bull" | "aligned_bear" | "mixed" | "unknown"
    mtf_alignment: float = 0.0
    mtf_bias: str = "unknown"
    # Short-horizon shock state propagated from MarketAgent.
    shock_detected: bool = False
    tick_drop_pct: float = 0.0
    tick_drop_window_seconds: int = 0

    def __post_init__(self) -> None:
        # If caller passed ``trend`` but left ``trend_direction`` at its
        # default, copy the value so both attributes are consistent.
        if self.trend and self.trend_direction == "neutral":
            self.trend_direction = self.trend
