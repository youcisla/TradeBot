"""Dashboard user repository — extracted from database/broker_repo.py."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import psycopg2.extras

if TYPE_CHECKING:
    from database.pool import ConnectionPool

logger = logging.getLogger(__name__)


class UserRepo:
    __slots__ = ("_pool",)

    def __init__(self, pool: "ConnectionPool") -> None:
        self._pool = pool

    def _conn(self):
        return self._pool.get_conn()

    def _put(self, conn):
        self._pool.put_conn(conn)

    def get_user_by_username(self, username: str) -> dict | None:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM dashboard_users WHERE username = %s",
                    (username,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            self._put(conn)

    def get_user_by_id(self, user_id: int) -> dict | None:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, username, created_at FROM dashboard_users WHERE id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            self._put(conn)

    def create_user(self, username: str, password_hash: str) -> int:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO dashboard_users (username, password_hash)
                           VALUES (%s, %s) RETURNING id""",
                        (username, password_hash),
                    )
                    return cur.fetchone()[0]
        finally:
            self._put(conn)

    def update_user_password(self, user_id: int, password_hash: str) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE dashboard_users SET password_hash = %s WHERE id = %s",
                        (password_hash, user_id),
                    )
        finally:
            self._put(conn)

    def get_all_users(self) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, username, created_at FROM dashboard_users ORDER BY created_at"
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    def user_count(self) -> int:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM dashboard_users")
                return cur.fetchone()[0]
        finally:
            self._put(conn)
