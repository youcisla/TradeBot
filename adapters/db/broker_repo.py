"""Broker repository — migrated from database/broker_repo.py."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

import psycopg2

from adapters.db.retry import with_retry

if TYPE_CHECKING:
    from adapters.db.pool import ConnectionPool


class BrokerRepo:
    """PostgreSQL broker account persistence layer."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def _conn(self) -> psycopg2.extensions.connection:
        return self._pool.get_conn()

    def _put(self, conn: psycopg2.extensions.connection) -> None:
        self._pool.put_conn(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_broker_accounts(self, user_id: int | None = None) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                if user_id is not None:
                    cur.execute(
                        "SELECT * FROM broker_accounts WHERE user_id = %s ORDER BY is_active DESC, name",
                        (user_id,),
                    )
                else:
                    cur.execute("SELECT * FROM broker_accounts ORDER BY is_active DESC, name")
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def add_broker_account(
        self,
        name: str,
        account_number: str,
        password: str,
        server: str,
        is_demo: bool = True,
        user_id: int | None = None,
    ) -> int:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO broker_accounts (
                        user_id, name, account_number, password,
                        server, is_demo, is_active
                    ) VALUES (%s, %s, %s, %s, %s, %s, FALSE)
                    ON CONFLICT (account_number) DO UPDATE SET
                        name     = EXCLUDED.name,
                        password = EXCLUDED.password,
                        server   = EXCLUDED.server,
                        is_demo  = EXCLUDED.is_demo
                    RETURNING id
                    """,
                    (user_id, name, account_number, password, server, is_demo),
                )
                row = cur.fetchone()
            conn.commit()
            return row[0] if row else 0
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def set_active_broker_account(self, account_id: int, user_id: int | None = None) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE broker_accounts SET is_active = FALSE")
                if user_id is not None:
                    cur.execute(
                        "UPDATE broker_accounts SET is_active = TRUE WHERE id = %s AND user_id = %s",
                        (account_id, user_id),
                    )
                else:
                    cur.execute(
                        "UPDATE broker_accounts SET is_active = TRUE WHERE id = %s",
                        (account_id,),
                    )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_symbol_faults(self) -> dict[str, int]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM symbol_fault WHERE disabled_until IS NOT NULL")
                cols = [desc[0] for desc in cur.description]
                return {row[0]: row[1] for row in cur.fetchall()}
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def increment_symbol_fault(self, symbol: str) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO symbol_fault (symbol, fail_count, disabled_until)
                    VALUES (%s, 1, %s)
                    ON CONFLICT (symbol) DO UPDATE SET
                        fail_count = symbol_fault.fail_count + 1
                    """,
                    (symbol, datetime.now() + timedelta(hours=1)),
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def clear_symbol_fault(self, symbol: str) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM symbol_fault WHERE symbol = %s",
                    (symbol,),
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def load_symbol_faults(self) -> dict[str, datetime]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT symbol, disabled_until FROM symbol_fault WHERE disabled_until IS NOT NULL"
                )
                return {row[0]: row[1] for row in cur.fetchall()}
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def is_symbol_faulty(self, symbol: str) -> bool:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT disabled_until FROM symbol_fault WHERE symbol = %s",
                    (symbol,),
                )
                row = cur.fetchone()
                if row is None:
                    return False
                if row[0] is None:
                    return False
                return row[0] > datetime.now()
        finally:
            self._put(conn)
