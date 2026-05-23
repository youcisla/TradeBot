"""MetaTrader 5 broker connector.

Thin facade that delegates to adapters/mt5/.  All heavy lifting lives in:
  connectors   → adapters/mt5/connector.py      (connection lifecycle)
  order exec  → adapters/mt5/order_executor.py  (place/modify/close orders)
  symbol map  → adapters/mt5/symbol_resolver.py (resolve/get_contract_size/...)
  reconnect   → adapters/mt5/reconnect.py      (IPC backoff helpers)
"""

from __future__ import annotations

import logging
import time as _time
from datetime import UTC, datetime
from typing import Any, cast

import MetaTrader5 as _mt5

mt5 = cast(Any, _mt5)

from broker.connector import BrokerConnector, OrderResult, PositionInfo
from config import settings
from models.market_data import Candle

from adapters.mt5.connector import MT5Connector as _MT5Impl
from adapters.mt5 import order_executor as _oe
from adapters.mt5 import symbol_resolver as _sr
from adapters.mt5 import reconnect as _rc

logger = logging.getLogger(__name__)

_TF_MAP: dict[str, int] = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30,
    "H1": mt5.TIMEFRAME_H1,
    "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
    "W1": mt5.TIMEFRAME_W1,
    "MN1": mt5.TIMEFRAME_MN1,
}


class MT5Connector(BrokerConnector):
    """Real MetaTrader 5 broker connection (facade)."""

    def __init__(
        self,
        account: str | None = None,
        password: str | None = None,
        server: str | None = None,
    ) -> None:
        # Delegate to the core adapter (holds connection state + IPC backoff)
        self._impl = _MT5Impl(account=account, password=password, server=server)

    # ── passthrough helpers so callers can reach adapter internals ─────────

    @property
    def _connected(self) -> bool:
        return self._impl._connected

    @_connected.setter
    def _connected(self, v: bool) -> None:
        self._impl._connected = v

    @property
    def symbol_map(self) -> dict[str, str]:
        return getattr(self._impl, "symbol_map", {})

    @symbol_map.setter
    def symbol_map(self, v: dict[str, str]) -> None:
        self._impl.symbol_map = v

    @property
    def _reverse_map(self) -> dict[str, str]:
        return getattr(self._impl, "_reverse_map", {})

    @_reverse_map.setter
    def _reverse_map(self, v: dict[str, str]) -> None:
        self._impl._reverse_map = v

    @property
    def account_info_cache(self) -> dict | None:
        return self._impl.account_info_cache

    @account_info_cache.setter
    def account_info_cache(self, v: dict) -> None:
        self._impl.account_info_cache = v

    @property
    def _ipc_backoff_until(self) -> dict[str, float]:
        return self._impl._ipc_backoff_until

    @_ipc_backoff_until.setter
    def _ipc_backoff_until(self, v: dict[str, float]) -> None:
        self._impl._ipc_backoff_until = v

    @property
    def _ipc_backoff_secs(self) -> float:
        return self._impl._ipc_backoff_secs

    @_ipc_backoff_secs.setter
    def _ipc_backoff_secs(self, v: float) -> None:
        self._impl._ipc_backoff_secs = v

    @property
    def connection_count(self) -> int:
        return self._impl.connection_count

    @connection_count.setter
    def connection_count(self, v: int) -> None:
        self._impl.connection_count = v

    # ── connection ─────────────────────────────────────────────────────────

    def connect(self) -> bool:
        return self._impl.connect()

    def disconnect(self) -> None:
        return self._impl.disconnect()

    def reconnect(self) -> bool:
        return self._impl.reconnect()

    def is_live(self) -> bool:
        return self._impl.is_live()

    # ── account data ─────────────────────────────────────────────────────

    def get_balance(self) -> float:
        return self._impl.get_balance()

    def get_equity(self) -> float:
        return self._impl.get_equity()

    def get_spread(self, symbol: str) -> float:
        return self._impl.get_spread(symbol)

    # ── symbol resolution ───────────────────────────────────────────────

    def resolve(self, symbol: str) -> str:
        return _sr.resolve_broker_symbol(self, symbol)

    def get_available_symbols(self, candidates: list[str]) -> list[str]:
        return _sr.get_available_symbols(self, candidates)

    def get_contract_size(self, symbol: str) -> float:
        return _sr.get_contract_size(self.resolve(symbol))

    def get_tick_size(self, symbol: str) -> float:
        return _sr.get_tick_size(self.resolve(symbol))

    def get_tick_value(self, symbol: str) -> float:
        return _sr.get_tick_value(self.resolve(symbol))

    # ── market data ───────────────────────────────────────────────────────

    def get_tick(self, symbol: str) -> dict[str, float]:
        broker_sym = self.resolve(symbol)

        # ── IPC backoff check ─────────────────────────────────────────
        try:
            _rc.check_ipc_backoff(self, broker_sym)
        except RuntimeError:
            raise

        tick = mt5.symbol_info_tick(broker_sym)
        if tick is None:
            mt5.symbol_select(broker_sym, True)
            tick = mt5.symbol_info_tick(broker_sym)
        if tick is None:
            err = mt5.last_error()
            err_str = str(err)
            _rc.apply_ipc_error(self, broker_sym, err_str)
            raise RuntimeError(f"No tick data for {symbol}: {err}")

        spread = tick.ask - tick.bid
        return {
            "bid": tick.bid,
            "ask": tick.ask,
            "spread": round(spread, 6),
            "volume": float(tick.volume),
        }

    def get_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        broker_sym = self.resolve(symbol)
        tf = _TF_MAP.get(timeframe, mt5.TIMEFRAME_H1)

        mt5.symbol_select(broker_sym, True)
        rates = mt5.copy_rates_from_pos(broker_sym, tf, 0, count)
        if rates is None:
            logger.warning(
                "No candle data for %s (%s) %s: %s",
                symbol, broker_sym, timeframe, mt5.last_error(),
            )
            return []
        if len(rates) < count:
            logger.warning(
                "MT5 returned %d/%d candles for %s %s — open the symbol chart in MT5 to load more history",
                len(rates), count, symbol, timeframe,
            )

        candles: list[Candle] = []
        for r in rates:
            candles.append(
                Candle(
                    timestamp=datetime.fromtimestamp(r["time"], tz=UTC),
                    open=float(r["open"]),
                    high=float(r["high"]),
                    low=float(r["low"]),
                    close=float(r["close"]),
                    volume=float(r["tick_volume"]),
                )
            )
        return candles

    # ── order management ────────────────────────────────────────────────

    def place_order(
        self,
        symbol: str,
        direction: str,
        lot_size: float,
        sl: float,
        tp: float | None = None,
        comment: str = "",
    ) -> OrderResult:
        broker_sym = self.resolve(symbol)
        result = _oe.place_order(self, symbol, direction, lot_size, sl, tp, comment)
        if result.success:
            _rc.reset_ipc_backoff(self, broker_sym)
        return result

    def modify_order(self, ticket: int, sl: float | None = None,
                     tp: float | None = None) -> bool:
        return _oe.modify_order(self, ticket, sl, tp)

    def close_partial(self, ticket: int, symbol: str, lot_size: float,
                      direction: str) -> bool:
        return _oe.close_partial(self, ticket, symbol, lot_size, direction)

    def close_order(self, ticket: int, symbol: str, direction: str) -> bool:
        return _oe.close_order(self, ticket, symbol, direction)

    def get_open_positions(self) -> list[PositionInfo]:
        return _oe.get_open_positions()

    def get_fill_size(self, order_id: str) -> float:
        return _oe.get_fill_size(order_id)

    def get_closed_pnl(self, ticket: int) -> float | None:
        """Sum profit of all deals belonging to this position ticket."""
        try:
            deals = mt5.history_deals_get(position=ticket)
            if deals:
                return float(sum(d.profit for d in deals))
        except Exception:
            logger.debug("history_deals_get failed for ticket %d", ticket)
        return None

    def get_closed_swap(self, ticket: int) -> float | None:
        """Sum swap of all deals belonging to this position ticket."""
        try:
            deals = mt5.history_deals_get(position=ticket)
            if deals:
                return float(sum(d.swap for d in deals))
        except Exception:
            logger.debug("history_deals_get failed for ticket %d", ticket)
        return None

    def get_daily_pnl(self) -> float:
        """Return today's realised P&L from MT5 deal history (midnight UTC → now)."""
        try:
            now = datetime.now(UTC)
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            deals = mt5.history_deals_get(start, now)
            if deals:
                return float(sum(d.profit for d in deals))
        except Exception as exc:
            logger.debug("get_daily_pnl failed: %s", exc)
        return 0.0

    def reconcile(self) -> list[PositionInfo]:
        return self.get_open_positions()
