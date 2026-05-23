"""User repository — migrated from database/user_repo.py."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import psycopg2

from adapters.db.retry import with_retry

if TYPE_CHECKING:
    from adapters.db.pool import ConnectionPool


class UserRepo:
    """PostgreSQL dashboard user persistence layer."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def _conn(self) -> psycopg2.extensions.connection:
        return self._pool.get_conn()

    def _put(self, conn: psycopg2.extensions.connection) -> None:
        self._pool.put_conn(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM dashboard_users WHERE username = %s",
                    (username,),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                cols = [desc[0] for desc in cur.description]
                return dict(zip(cols, row))
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def create_user(self, username: str, password_hash: str) -> int:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO dashboard_users (username, password_hash) VALUES (%s, %s) RETURNING id",
                    (username, password_hash),
                )
                row = cur.fetchone()
            conn.commit()
            return row[0] if row else 0
        finally:
            self._put(conn)
