"""MetaTrader 5 connection lifecycle.

Handles connect/disconnect/reconnect with retry logic, account info caching,
balance/equity reads, and the IPC backoff mechanism for symbol-level error
throttling.
"""

from __future__ import annotations

import logging
import time
from typing import Any, cast

import MetaTrader5 as _mt5

mt5 = cast(Any, _mt5)

from config import settings

logger = logging.getLogger(__name__)

# ── Timeframe mapping ────────────────────────────────────────────────────

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


class MT5Connector:
    """MetaTrader 5 connection lifecycle.

    Deliberately NOT a ``BrokerConnector`` subclass: the order-entry, position
    and symbol methods live as module-level functions in ``order_executor`` and
    ``symbol_resolver``, and the public ``BrokerConnector`` is the facade in
    ``broker/mt5_connector.py``.  Inheriting the ABC made this class abstract
    and therefore impossible to instantiate, which broke every live MT5 code
    path (the bot could not construct its broker at all).
    """

    def __init__(
        self,
        account: str | None = None,
        password: str | None = None,
        server: str | None = None,
    ) -> None:
        self._connected = False
        self._account = account or settings.BROKER_ACCOUNT
        self._password = password or settings.BROKER_PASSWORD
        self._server = server or settings.BROKER_SERVER
        self.account_info_cache: dict | None = None
        # Per-symbol backoff after IPC errors — avoids tight retry loops on
        # "Terminal: Call failed" where MT5 is temporarily swamped.
        self._ipc_backoff_until: dict[str, float] = {}
        self._ipc_backoff_secs: float = 30.0
        # MT5 connection lifecycle counter — increments each time connect() succeeds.
        self.connection_count: int = 0

    # ── connection ────────────────────────────────────────────────────────

    def connect(self) -> bool:
        max_retries = 3
        base_delay = 5.0
        last_error_msg = ""

        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                delay = base_delay * (2 ** (attempt - 2))
                logger.warning(
                    "MT5 connect attempt %d/%d — waiting %.1fs before retry",
                    attempt,
                    max_retries,
                    delay,
                )
                time.sleep(delay)

            if not _mt5.initialize():
                last_error_msg = str(_mt5.last_error())
                logger.warning(
                    "MT5 initialize failed (attempt %d/%d): %s",
                    attempt,
                    max_retries,
                    last_error_msg,
                )
                _mt5.shutdown()
                continue

            try:
                account = int(self._account)
            except (TypeError, ValueError):
                logger.error(
                    "Invalid BROKER_ACCOUNT value %r — must be a numeric account number",
                    self._account,
                )
                _mt5.shutdown()
                return False

            authorized = _mt5.login(
                account,
                password=self._password,
                server=self._server,
            )
            if not authorized:
                last_error_msg = str(_mt5.last_error())
                logger.warning(
                    "MT5 login failed (attempt %d/%d): %s",
                    attempt,
                    max_retries,
                    last_error_msg,
                )
                _mt5.shutdown()
                continue

            info = _mt5.account_info()
            logger.info(
                "MT5 connected: account=%d  server=%s  balance=%.2f  leverage=%d",
                info.login, info.server, info.balance, info.leverage,
            )
            self.account_info_cache = {
                "login": info.login,
                "server": info.server,
                "balance": info.balance,
                "equity": info.equity,
                "leverage": info.leverage,
                "name": info.name,
                "company": info.company,
            }
            self._connected = True
            self.connection_count += 1
            logger.info("MT5 connected (connection_count=%d)", self.connection_count)
            return True

        logger.error("MT5 connection failed after %d attempts: %s", max_retries, last_error_msg)
        return False

    def disconnect(self) -> None:
        if self._connected:
            mt5.shutdown()
            self._connected = False
            logger.info("MT5 disconnected")

    def reconnect(self) -> bool:
        """Explicitly disconnect and reconnect the MT5 session."""
        logger.info("MT5 reconnect requested")
        if self._connected:
            try:
                mt5.shutdown()
            except Exception:
                pass
            self._connected = False
        return self.connect()

    def is_live(self) -> bool:
        """Return True when MT5 is connected and responsive."""
        if not self._connected:
            return False
        try:
            info = mt5.account_info()
            return info is not None
        except Exception:
            return False

    # ── account data ─────────────────────────────────────────────────────

    def get_balance(self) -> float:
        info = mt5.account_info()
        if info is not None:
            val = float(info.balance)
            if val > 0.0:
                if self.account_info_cache is not None:
                    self.account_info_cache["balance"] = val
                return val
            if self.account_info_cache is not None:
                cached = float(self.account_info_cache.get("balance", 0.0))
                if cached > 0.0:
                    return cached
            return val
        if self.account_info_cache is not None:
            return float(self.account_info_cache.get("balance", 0.0))
        return 0.0

    def get_equity(self) -> float:
        info = mt5.account_info()
        if info is not None:
            val = float(info.equity)
            if val > 0.0:
                if self.account_info_cache is not None:
                    self.account_info_cache["equity"] = val
                return val
            if self.account_info_cache is not None:
                cached = float(self.account_info_cache.get("equity", 0.0))
                if cached > 0.0:
                    return cached
            return val
        if self.account_info_cache is not None:
            return float(self.account_info_cache.get("equity", 0.0))
        return 0.0

    def get_spread(self, symbol: str) -> float:
        broker_sym = self.resolve(symbol)
        info = mt5.symbol_info(broker_sym)
        if info is not None:
            return float(info.spread)
        return 0.0
