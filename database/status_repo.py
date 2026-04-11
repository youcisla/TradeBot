"""Bot-status repository — extracted from database/db.py."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.pool import ConnectionPool
from database.retry import with_retry


class StatusRepo:
    __slots__ = ("_pool",)

    def __init__(self, pool: "ConnectionPool") -> None:
        self._pool = pool

    def _conn(self):
        return self._pool.get_conn()

    def _put(self, conn):
        self._pool.put_conn(conn)

    @with_retry()
    def update_bot_status(
        self,
        state: str,
        equity: float,
        open_trades: int,
        daily_pnl: float,
        broker_account: str = "",
        broker_server: str = "",
        broker_name: str = "",
        balance: float = 0.0,
        leverage: int = 0,
        spread_condition: str = "unknown",
        current_session: str = "unknown",
        market_regime: str = "unknown",
        spread_pips: float = 0.0,
        vix: float = 0.0,
        daily_loss_pct: float = 0.0,
        equity_drawdown_pct: float = 0.0,
    ) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE bot_status SET
                               state = %s, last_tick = NOW(),
                               equity = %s, open_trades = %s, daily_pnl = %s,
                               broker_account = %s, broker_server = %s,
                               broker_name = %s, balance = %s, leverage = %s,
                               spread_condition = %s, current_session = %s,
                               market_regime = %s, spread_pips = %s,
                               vix = %s, daily_loss_pct = %s,
                               equity_drawdown_pct = %s
                           WHERE id = 1""",
                        (state, equity, open_trades, daily_pnl,
                         broker_account, broker_server, broker_name,
                         balance, leverage,
                         spread_condition, current_session, market_regime,
                         spread_pips, vix, daily_loss_pct, equity_drawdown_pct),
                    )
        finally:
            self._put(conn)

    def set_bot_uptime_start(self) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE bot_status SET uptime_start = NOW(), state = 'running' WHERE id = 1"
                    )
        finally:
            self._put(conn)

    def set_bot_stopped(self) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE bot_status SET state = 'stopped', last_tick = NOW() WHERE id = 1"
                    )
        finally:
            self._put(conn)
