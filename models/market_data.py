from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Optional, TYPE_CHECKING

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
    regime: str = "unknown"  # trending / ranging / volatile
    trend_direction: str = "neutral"  # bullish / bearish / neutral
    session: str = "unknown"  # London / NY / Asian / overlap
    day_of_week: str = ""
    near_news_event: bool = False

    # Macro world context from Crucix (None if Crucix not running)
    macro: "Optional[MacroContext]" = None

    candles: list[Candle] = field(default_factory=list)
