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
    take_profit: float | None = None
    current_price: float = 0.0
    pnl: float = 0.0
    magic: int = 0
    comment: str = ""


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

    def get_contract_size(self, symbol: str) -> float:
        """Return the broker's actual contract size (units per 1 lot) for *symbol*.

        Defaults to the config lookup so mock/test connectors work without
        overriding.  MT5Connector overrides this with live symbol_info data
        to prevent hardcoded-vs-broker mismatches.
        """
        from config.symbols import contract_size as _cs
        return _cs(symbol)

    def get_tick_size(self, symbol: str) -> float:
        """Return the minimum price movement (tick size) for *symbol*.

        MT5Connector overrides this with symbol_info.trade_tick_size so the
        value matches the broker exactly.  The config pip_value is used as a
        fallback for mock/test connectors.
        """
        from config.symbols import pip_value as _pv
        return _pv(symbol)

    def get_tick_value(self, symbol: str) -> float:
        """Return the account-currency P&L per 1 tick move per 1 lot.

        MT5 calculates this in the account's own currency, automatically
        converting cross-currency instruments (e.g. BTCUSD on a EUR account
        returns a EUR value).  Using this instead of sl_distance × contract_size
        eliminates the account-currency / instrument-currency mismatch.

        MT5Connector overrides with symbol_info.trade_tick_value.
        The fallback estimate (pip × contract_size) is USD-based and only
        correct when account currency == instrument profit currency.
        """
        from config.symbols import pip_value as _pv, contract_size as _cs
        return _pv(symbol) * _cs(symbol)

    def get_closed_pnl(self, ticket: int) -> float | None:
        """Return the realised P&L for a closed position by broker ticket.

        Returns None if the broker doesn't support history queries (e.g. mock).
        MT5Connector overrides this with history_deals_get().
        """
        return None

    def get_daily_pnl(self) -> float:
        """Return today's realised P&L from the broker's own history.

        Sums the profit of all closed deals since midnight UTC.
        Falls back to 0.0 if the broker doesn't support history queries.
        """
        return 0.0

    # ── reconciliation ───────────────────────────────────────────────────

    @abstractmethod
    def reconcile(self) -> list[PositionInfo]:
        """Fetch the current broker positions for reconciliation.

        This is intentionally identical to ``get_open_positions``; it
        exists as a named semantic entry-point so call-sites make the
        intent clear.
        """
