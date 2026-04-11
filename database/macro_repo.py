"""Macro snapshot and agent memory repository — extracted from database/broker_repo.py."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.pool import ConnectionPool

logger = logging.getLogger(__name__)


class MacroRepo:
    __slots__ = ("_pool",)

    def __init__(self, pool: "ConnectionPool") -> None:
        self._pool = pool

    def _conn(self):
        return self._pool.get_conn()

    def _put(self, conn):
        self._pool.put_conn(conn)

    # ── macro snapshots ───────────────────────────────────────────────────

    def save_macro_snapshot(self, snapshot_data: dict) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO macro_snapshots
                           (snapshot_json, risk_tier, yield_inverted, usd_strength, gdelt_tone, fetched_at)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (
                            json.dumps(snapshot_data),
                            snapshot_data.get("risk_tier", "normal"),
                            snapshot_data.get("yield_curve_inverted", False),
                            snapshot_data.get("usd_strength", "neutral"),
                            snapshot_data.get("gdelt_risk_tone"),
                            datetime.now(UTC),
                        ),
                    )
        finally:
            self._put(conn)

    def get_macro_snapshots(
        self,
        lookback_hours: int = 24,
        risk_tier: str | None = None,
        limit: int = 100,
    ) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                conditions = [
                    "fetched_at >= NOW() - (%s || ' hours')::interval"
                ]
                params: list = [str(max(1, lookback_hours))]
                if risk_tier:
                    conditions.append("risk_tier = %s")
                    params.append(risk_tier)
                params.append(max(1, limit))
                cur.execute(
                    f"""SELECT id, snapshot_json, risk_tier, yield_inverted,
                              usd_strength, gdelt_tone, fetched_at
                       FROM macro_snapshots
                       WHERE {' AND '.join(conditions)}
                       ORDER BY fetched_at DESC
                       LIMIT %s""",
                    params,
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    def prune_macro_snapshots(self, keep_hours: int = 168) -> int:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """DELETE FROM macro_snapshots
                           WHERE fetched_at < NOW() - (%s || ' hours')::interval""",
                        (str(max(1, keep_hours)),),
                    )
                    return cur.rowcount
        finally:
            self._put(conn)

    # ── persistent agent memory ──────────────────────────────────────────

    def write_memory_block(self, block_name: str, content: str) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO bot_memory (block_name, content, updated_at)
                           VALUES (%s, %s, NOW())
                           ON CONFLICT (block_name)
                           DO UPDATE SET content = EXCLUDED.content,
                                         updated_at = NOW()""",
                        (block_name, content),
                    )
        finally:
            self._put(conn)

    def read_memory_block(self, block_name: str) -> str | None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT content FROM bot_memory WHERE block_name = %s",
                    (block_name,),
                )
                row = cur.fetchone()
                return row[0] if row else None
        finally:
            self._put(conn)
