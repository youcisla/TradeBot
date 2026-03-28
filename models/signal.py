from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class EntrySnapshot:
    """Immutable record of market conditions at signal time.

    Used by the learning system to objectively score trades as
    'clean' vs 'messy'.
    """

    spread: float = 0.0
    rsi_aligned: bool = False
    trend_aligned: bool = False
    volume_sufficient: bool = False
    near_news_event: bool = False
    market_condition: str = ""  # trending / ranging / volatile
    session: str = ""  # London / NY / Asian / overlap
    day_of_week: str = ""


@dataclass
class Signal:
    """A trade signal produced by a strategy."""

    strategy: str = ""
    symbol: str = ""
    direction: str = ""  # "BUY" or "SELL"
    entry_price: float = 0.0
    stop_loss: float = 0.0
    take_profit_1: float = 0.0
    take_profit_2: float = 0.0
    take_profit_3: float = 0.0
    take_profit_4: float = 0.0   # runner — HTF liquidity target (0 = not set)
    # Structural breakeven: price of the nearest protective swing low (BUY) or
    # swing high (SELL) below/above entry.  When > 0, trade_manager moves SL
    # here after TP1 instead of the default entry+spread formula.
    structural_be: float = 0.0
    confidence: float = 0.5
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    reason: str = ""
    entry_snapshot: EntrySnapshot = field(default_factory=EntrySnapshot)
