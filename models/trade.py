from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class Trade:
    """Represents a single trade managed by the bot."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    symbol: str = ""
    strategy: str = ""
    direction: str = ""  # "BUY" or "SELL"
    entry_price: float = 0.0
    lot_size: float = 0.0  # actual filled size
    stop_loss: float = 0.0
    take_profit_1: float = 0.0
    take_profit_2: float = 0.0
    take_profit_3: float = 0.0
    take_profit_4: float = 0.0   # runner — HTF liquidity target (0 = not set)
    tp1_lots: float = 0.0
    tp2_lots: float = 0.0
    tp3_lots: float = 0.0
    tp4_lots: float = 0.0        # lots held for the TP4 runner (0 = no runner)
    tp1_hit: bool = False
    tp2_hit: bool = False
    tp3_hit: bool = False
    tp4_hit: bool = False
    # Structural breakeven price stored at trade-open time.
    # 0 = not set; trade_manager falls back to entry+spread formula.
    structural_be: float = 0.0
    status: str = "OPEN"  # OPEN, PARTIAL, CLOSED
    open_time: datetime = field(default_factory=lambda: datetime.now(UTC))
    close_time: datetime | None = None
    pnl: float = 0.0
    current_price: float = 0.0   # latest broker price — updated every monitor cycle
    commission: float = 0.0   # round-trip commission charged by broker (deducted from pnl)
    expected_edge_pct: float = 0.0
    expected_pnl: float = 0.0
    close_reason: str = ""  # TP1, TP2, TP3, SL, MANUAL, EMERGENCY
    broker_ticket: int = 0
    spread_at_entry: float = 0.0

    # Entry snapshot fields (flattened for DB storage)
    snap_rsi_aligned: bool = False
    snap_trend_aligned: bool = False
    snap_volume_sufficient: bool = False
    snap_near_news_event: bool = False
    snap_market_condition: str = ""
    snap_session: str = ""
    snap_day_of_week: str = ""

    def is_open(self) -> bool:
        return self.status in ("OPEN", "PARTIAL")

    def remaining_lots(self) -> float:
        closed = 0.0
        if self.tp1_hit:
            closed += self.tp1_lots
        if self.tp2_hit:
            closed += self.tp2_lots
        if self.tp3_hit:
            closed += self.tp3_lots
        if self.tp4_hit:
            closed += self.tp4_lots
        return round(self.lot_size - closed, 2)
