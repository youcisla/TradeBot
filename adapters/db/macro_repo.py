"""Macro repository — migrated from database/macro_repo.py."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import psycopg2

from adapters.db.retry import with_retry

if TYPE_CHECKING:
    from adapters.db.pool import ConnectionPool


class MacroRepo:
    """PostgreSQL macro/memory persistence layer."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def _conn(self) -> psycopg2.extensions.connection:
        return self._pool.get_conn()

    def _put(self, conn: psycopg2.extensions.connection) -> None:
        self._pool.put_conn(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def save_macro_snapshot(self, snapshot: dict[str, Any]) -> int:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO macro_snapshots (
                        snapshot_json, risk_tier, yield_inverted, usd_strength, gdelt_tone
                    ) VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        psycopg2.extras.Json(snapshot["snapshot_json"]),
                        snapshot.get("risk_tier", "normal"),
                        snapshot.get("yield_inverted", False),
                        snapshot.get("usd_strength", "neutral"),
                        snapshot.get("gdelt_tone"),
                    ),
                )
                row = cur.fetchone()
            conn.commit()
            return row[0] if row else 0
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_latest_macro_snapshot(self) -> dict[str, Any] | None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM macro_snapshots ORDER BY fetched_at DESC LIMIT 1"
                )
                row = cur.fetchone()
                if row is None:
                    return None
                cols = [desc[0] for desc in cur.description]
                return dict(zip(cols, row))
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def write_memory_block(self, block_name: str, content: str) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO bot_memory (block_name, content, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (block_name) DO UPDATE SET
                        content    = EXCLUDED.content,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (block_name, content, datetime.now()),
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def read_memory_block(self, block_name: str) -> str:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT content FROM bot_memory WHERE block_name = %s",
                    (block_name,),
                )
                row = cur.fetchone()
                return row[0] if row else ""
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def list_memory_blocks(self) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM bot_memory ORDER BY updated_at DESC")
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def upsert_setting_override(self, key: str, value: str) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO bot_settings_overrides (key, value, updated_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (key) DO UPDATE SET
                        value      = EXCLUDED.value,
                        updated_at = EXCLUDED.updated_at
                    """,
                    (key, value, datetime.now()),
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_setting_override(self, key: str) -> str | None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT value FROM bot_settings_overrides WHERE key = %s",
                    (key,),
                )
                row = cur.fetchone()
                return row[0] if row else None
        finally:
            self._put(conn)
