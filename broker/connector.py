"""Abstract broker connector interface.

Every concrete broker (MT5, REST API, Mock) must implement this ABC.
Agents only depend on the abstract interface so implementations can be
swapped without touching agent code.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from models.market_data import Candle


@dataclass
class OrderResult:
    """Result returned by place_order."""
    success: bool
    order_id: str = ""
    broker_ticket: int = 0
    filled_lots: float = 0.0
    fill_price: float = 0.0
    message: str = ""


@dataclass
class PositionInfo:
    """Represents a single open position as reported by the broker."""
    ticket: int
    symbol: str
    direction: str  # "BUY" or "SELL"
    lot_size: float
    entry_price: float
    stop_loss: float
    current_price: float
    pnl: float


class BrokerConnector(ABC):
    """Abstract interface that every broker implementation must follow."""

    # ── account ──────────────────────────────────────────────────────────

    @abstractmethod
    def connect(self) -> bool:
        """Establish connection. Return True on success."""

    @abstractmethod
    def disconnect(self) -> None:
        """Clean shutdown."""

    @abstractmethod
    def get_balance(self) -> float:
        """Current account balance."""

    @abstractmethod
    def get_equity(self) -> float:
        """Current account equity (balance + floating P&L)."""

    # ── market data ──────────────────────────────────────────────────────

    @abstractmethod
    def get_tick(self, symbol: str) -> dict[str, float]:
        """Return ``{'bid': …, 'ask': …, 'spread': …, 'volume': …}``."""

    @abstractmethod
    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        """Return the last *count* candles."""

    # ── order management ─────────────────────────────────────────────────

    @abstractmethod
    def place_order(self, symbol: str, direction: str, lot_size: float,
                    sl: float, tp: float | None = None,
                    comment: str = "") -> OrderResult:
        """Place a market order. Returns an OrderResult."""

    @abstractmethod
    def modify_order(self, ticket: int, sl: float | None = None,
                     tp: float | None = None) -> bool:
        """Modify the SL/TP of an existing position."""

    @abstractmethod
    def close_partial(self, ticket: int, symbol: str, lot_size: float,
                      direction: str) -> bool:
        """Partially close a position by the given lot_size."""

    @abstractmethod
    def close_order(self, ticket: int, symbol: str, direction: str) -> bool:
        """Fully close a position."""

    @abstractmethod
    def get_open_positions(self) -> list[PositionInfo]:
        """Return all open positions from the broker."""

    @abstractmethod
    def get_fill_size(self, order_id: str) -> float:
        """Return actual filled lot size for an order."""

    # ── reconciliation ───────────────────────────────────────────────────

    @abstractmethod
    def reconcile(self) -> list[PositionInfo]:
        """Fetch the current broker positions for reconciliation.

        This is intentionally identical to ``get_open_positions``; it
        exists as a named semantic entry-point so call-sites make the
        intent clear.
        """
