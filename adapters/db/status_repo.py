"""Status repository — migrated from database/status_repo.py."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import psycopg2

from adapters.db.retry import with_retry

if TYPE_CHECKING:
    from adapters.db.pool import ConnectionPool


class StatusRepo:
    """PostgreSQL bot status persistence layer."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def _conn(self) -> psycopg2.extensions.connection:
        return self._pool.get_conn()

    def _put(self, conn: psycopg2.extensions.connection) -> None:
        self._pool.put_conn(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def update_bot_status(self, state: str, **kwargs: Any) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                fields = ["state = %s", "last_tick = %s"]
                values: list[Any] = [state, datetime.now()]
                for key, value in kwargs.items():
                    fields.append(f"{key} = %s")
                    values.append(value)
                values.append(1)  # WHERE id = 1
                cur.execute(
                    f"UPDATE bot_status SET {', '.join(fields)} WHERE id = %s",
                    values,
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_bot_status(self) -> dict[str, Any]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM bot_status WHERE id = 1")
                row = cur.fetchone()
                if row is None:
                    return {}
                cols = [desc[0] for desc in cur.description]
                return dict(zip(cols, row))
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def update_guard_status(self, guard_status: list[dict[str, Any]]) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE bot_status SET guard_status = %s WHERE id = 1",
                    (psycopg2.extras.Json(guard_status),),
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def upsert_broker_account(
        self,
        name: str,
        account_number: str,
        password: str,
        server: str,
        is_demo: bool = True,
        is_active: bool = False,
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
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (account_number) DO UPDATE SET
                        name      = EXCLUDED.name,
                        password  = EXCLUDED.password,
                        server    = EXCLUDED.server,
                        is_demo   = EXCLUDED.is_demo,
                        is_active = EXCLUDED.is_active
                    RETURNING id
                    """,
                    (user_id, name, account_number, password, server, is_demo, is_active),
                )
                row = cur.fetchone()
            conn.commit()
            return row[0] if row else 0
        finally:
            self._put(conn)

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
    def get_active_broker_account(self) -> dict[str, Any] | None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM broker_accounts WHERE is_active = TRUE LIMIT 1"
                )
                row = cur.fetchone()
                if row is None:
                    return None
                cols = [desc[0] for desc in cur.description]
                return dict(zip(cols, row))
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def set_active_broker_account(self, account_id: int) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("UPDATE broker_accounts SET is_active = FALSE")
                cur.execute(
                    "UPDATE broker_accounts SET is_active = TRUE WHERE id = %s",
                    (account_id,),
                )
            conn.commit()
        finally:
            self._put(conn)
