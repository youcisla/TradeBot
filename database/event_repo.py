"""Event and command repository — extracted from database/db.py."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import psycopg2.extras

if TYPE_CHECKING:
    from database.pool import ConnectionPool
from database.retry import with_retry

logger = logging.getLogger(__name__)


class EventRepo:
    __slots__ = ("_pool",)

    def __init__(self, pool: "ConnectionPool") -> None:
        self._pool = pool

    def _conn(self):
        return self._pool.get_conn()

    def _put(self, conn):
        self._pool.put_conn(conn)

    # ── agent events ─────────────────────────────────────────────────────

    @with_retry()
    def log_agent_event(self, agent: str, level: str, message: str,
                        data: dict | None = None) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO agent_events (agent, level, message, data)
                           VALUES (%s, %s, %s, %s)""",
                        (agent, level, message,
                         json.dumps(data) if data else None),
                    )
        finally:
            self._put(conn)

    def log_event(self, level: str, source: str, message: str,
                  data: str | None = None) -> None:
        """Legacy event log — wraps log_agent_event for LoggingAgent compat."""
        self.log_agent_event(
            agent=source.lower(),
            level=level.lower(),
            message=message,
            data={"raw": data} if data else None,
        )

    # ── bot commands ─────────────────────────────────────────────────────

    def get_pending_commands(self) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM bot_commands
                       WHERE status = 'pending'
                       ORDER BY created_at ASC"""
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    def claim_pending_commands(self, limit: int = 25) -> list[dict]:
        """Atomically claim pending commands using FOR UPDATE SKIP LOCKED."""
        conn = self._conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        """
                        WITH claimed AS (
                            SELECT id
                            FROM bot_commands
                            WHERE status = 'pending'
                            ORDER BY created_at ASC
                            FOR UPDATE SKIP LOCKED
                            LIMIT %s
                        )
                        UPDATE bot_commands bc
                        SET status = 'running',
                            result = CONCAT('Started ', bc.command),
                            started_at = NOW(),
                            executed_at = NULL
                        FROM claimed
                        WHERE bc.id = claimed.id
                        RETURNING bc.*
                        """,
                        (max(1, limit),),
                    )
                    return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    def update_command(
        self,
        cmd_id: int,
        status: str,
        result: str | None = None,
        *,
        set_executed: bool = True,
    ) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    if set_executed:
                        cur.execute(
                            """UPDATE bot_commands
                               SET status = %s, result = %s, executed_at = NOW()
                               WHERE id = %s""",
                            (status, result, cmd_id),
                        )
                    else:
                        cur.execute(
                            """UPDATE bot_commands
                               SET status = %s, result = %s,
                                   started_at = NOW(), executed_at = NULL
                               WHERE id = %s""",
                            (status, result, cmd_id),
                        )
        finally:
            self._put(conn)

    def review_command(
        self,
        cmd_id: int,
        *,
        approved: bool,
        reviewer: str,
        reason: str,
    ) -> bool:
        """Approve or deny a command waiting for human confirmation."""
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT payload FROM bot_commands
                           WHERE id = %s AND status = 'pending_confirmation'""",
                        (cmd_id,),
                    )
                    row = cur.fetchone()
                    if row is None:
                        return False

                    payload = row[0] or {}
                    if not isinstance(payload, dict):
                        payload = {}

                    review_meta = payload.get("_review")
                    if not isinstance(review_meta, dict):
                        review_meta = {}

                    review_meta.update(
                        {
                            "reviewedBy": reviewer,
                            "reviewedAt": datetime.now(UTC).isoformat(),
                            "reason": reason,
                            "decision": "approved" if approved else "denied",
                        }
                    )
                    payload["_review"] = review_meta

                    next_status = "pending" if approved else "failed"
                    result_text = "Approved for execution" if approved else f"Denied: {reason}"

                    cur.execute(
                        """UPDATE bot_commands
                           SET status = %s,
                               result = %s,
                               payload = %s,
                               executed_at = CASE WHEN %s THEN NULL ELSE NOW() END
                           WHERE id = %s""",
                        (next_status, result_text, json.dumps(payload), approved, cmd_id),
                    )
                    return True
        finally:
            self._put(conn)

    # ── sessions ─────────────────────────────────────────────────────────

    def start_session(self, version: str = "") -> int:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO bot_sessions (version) VALUES (%s) RETURNING id",
                        (version,),
                    )
                    row = cur.fetchone()
                    return int(row[0]) if row else 0
        except Exception:
            logger.exception("start_session failed (non-fatal)")
            return 0
        finally:
            self._put(conn)

    def end_session(self, session_id: int, exit_reason: str = "normal") -> None:
        if not session_id:
            return
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE bot_sessions
                        SET ended_at = NOW(), exit_reason = %s
                        WHERE id = %s
                        """,
                        (exit_reason, session_id),
                    )
        except Exception:
            logger.exception("end_session failed (non-fatal)")
        finally:
            self._put(conn)
