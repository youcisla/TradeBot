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
    # ICT/SMC enrichment fields (populated by DeepSeekStrategy when using ICT prompt)
    ict_score: int = 0          # 0-70 ICT confluence score
    smc_confirmed: bool = False  # SMC secondary confirmed
    confluence_flags: list[str] = field(default_factory=list)  # ["FVG", "OB", "BOS", ...]


class SignalIntent:
    """Distinguishes discussion-grade signals from execution-grade ones.

    Mirrors AI-Trader's three-message-type model adapted for a single-bot:
      DISCUSSION  – market analysis / thesis with no execution intent.
                   Council/debate agents may respond; execution MUST NOT act.
      STRATEGY   – actionable trade idea after debate/gate. Council or human
                   review is still recommended before execution.
      EXECUTION  – ready to trade. RiskAgent and ExecutionAgent should act on it
                   without further review (subject to RISK_VALIDATION_PROFILE).
    """
    DISCUSSION = "DISCUSSION"
    STRATEGY  = "STRATEGY"
    EXECUTION = "EXECUTION"


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
    # Expected edge metadata (filled by strategy/execution pipeline).
    expected_edge_pct: float = 0.0
    expected_pnl: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    reason: str = ""
    entry_snapshot: EntrySnapshot = field(default_factory=EntrySnapshot)
    # Bull/Bear Debate Agent output — populated by BullBearDebateAgent.evaluate().
    # Stored in trade_theses by ExecutionAgent when the trade is opened.
    bull_case: str = ""
    bear_case: str = ""
    # Signal intent: DISCUSSION / STRATEGY / EXECUTION (see SignalIntent).
    # Controls whether ExecutionAgent may act on this signal without further review.
    signal_intent: str = SignalIntent.EXECUTION
