"""Broker accounts and symbol-faults repository — extracted from database/db.py.

Handles encrypted broker credentials and per-symbol fault tracking.
All other domains (users, signals, social, macro) have been moved to dedicated repos.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import psycopg2.extras

if TYPE_CHECKING:
    from database.pool import ConnectionPool

logger = logging.getLogger(__name__)


class BrokerRepo:
    __slots__ = ("_pool",)

    def __init__(self, pool: "ConnectionPool") -> None:
        self._pool = pool

    def _conn(self):
        return self._pool.get_conn()

    def _put(self, conn):
        self._pool.put_conn(conn)

    # ── broker accounts ──────────────────────────────────────────────────

    def get_broker_accounts(self, user_id: int | None = None) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if user_id:
                    cur.execute(
                        """SELECT id, user_id, name, account_number, server,
                                  is_demo, is_active, created_at, last_connected
                           FROM broker_accounts WHERE user_id = %s
                           ORDER BY created_at DESC""",
                        (user_id,),
                    )
                else:
                    cur.execute(
                        """SELECT id, user_id, name, account_number, server,
                                  is_demo, is_active, created_at, last_connected
                           FROM broker_accounts ORDER BY created_at DESC"""
                    )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    def get_active_broker_account(self) -> dict | None:
        from utils.crypto import decrypt

        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM broker_accounts WHERE is_active = TRUE LIMIT 1"
                )
                row = cur.fetchone()
                if not row:
                    return None
                result = dict(row)
                result["password"] = decrypt(result["password"])
                return result
        finally:
            self._put(conn)

    def add_broker_account(
        self,
        name: str,
        account_number: str,
        password: str,
        server: str,
        is_demo: bool = True,
        user_id: int | None = None,
    ) -> int:
        from utils.crypto import encrypt

        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO broker_accounts
                           (user_id, name, account_number, password, server, is_demo)
                           VALUES (%s, %s, %s, %s, %s, %s)
                           RETURNING id""",
                        (user_id, name, account_number,
                         encrypt(password), server, is_demo),
                    )
                    return cur.fetchone()[0]
        finally:
            self._put(conn)

    def update_broker_account(
        self,
        account_id: int,
        name: str,
        account_number: str,
        password: str | None,
        server: str,
        is_demo: bool,
    ) -> None:
        from utils.crypto import encrypt

        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    if password:
                        cur.execute(
                            """UPDATE broker_accounts SET
                                   name=%s, account_number=%s, password=%s,
                                   server=%s, is_demo=%s
                               WHERE id=%s""",
                            (name, account_number, encrypt(password),
                             server, is_demo, account_id),
                        )
                    else:
                        cur.execute(
                            """UPDATE broker_accounts SET
                                   name=%s, account_number=%s,
                                   server=%s, is_demo=%s
                               WHERE id=%s""",
                            (name, account_number, server, is_demo, account_id),
                        )
        finally:
            self._put(conn)

    def delete_broker_account(self, account_id: int) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM broker_accounts WHERE id = %s",
                                (account_id,))
        finally:
            self._put(conn)

    def activate_broker_account(self, account_id: int) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE broker_accounts SET is_active = FALSE")
                    cur.execute(
                        "UPDATE broker_accounts SET is_active = TRUE WHERE id = %s",
                        (account_id,),
                    )
        finally:
            self._put(conn)

    def mark_broker_connected(self, account_id: int) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE broker_accounts SET last_connected = NOW() WHERE id = %s",
                        (account_id,),
                    )
        finally:
            self._put(conn)

    # ── symbol faults ─────────────────────────────────────────────────────

    def load_symbol_faults(self) -> dict[str, dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT symbol, fail_count, disabled_until FROM symbol_fault")
                return {r["symbol"]: {"fail_count": r["fail_count"],
                                      "disabled_until": r["disabled_until"]}
                        for r in cur.fetchall()}
        finally:
            self._put(conn)

    def save_symbol_fault(
        self,
        symbol: str,
        fail_count: int,
        disabled_until: datetime | None,
    ) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    if fail_count == 0 and disabled_until is None:
                        cur.execute(
                            "DELETE FROM symbol_fault WHERE symbol = %s", (symbol,))
                    else:
                        cur.execute(
                            """INSERT INTO symbol_fault (symbol, fail_count, disabled_until)
                               VALUES (%s, %s, %s)
                               ON CONFLICT (symbol) DO UPDATE SET
                                   fail_count = EXCLUDED.fail_count,
                                   disabled_until = EXCLUDED.disabled_until""",
                            (symbol, fail_count, disabled_until),
                        )
        finally:
            self._put(conn)
