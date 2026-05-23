"""Event repository — migrated from database/event_repo.py."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import psycopg2

from adapters.db.retry import with_retry

if TYPE_CHECKING:
    from adapters.db.pool import ConnectionPool


class EventRepo:
    """PostgreSQL agent event persistence layer."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def _conn(self) -> psycopg2.extensions.connection:
        return self._pool.get_conn()

    def _put(self, conn: psycopg2.extensions.connection) -> None:
        self._pool.put_conn(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def log_agent_event(
        self,
        agent: str,
        level: str,
        message: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_events (agent, level, message, data)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (agent, level, message, psycopg2.extras.Json(data) if data else None),
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_events(
        self,
        agent: str | None = None,
        level: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                query = "SELECT * FROM agent_events"
                params: list[Any] = []
                if agent:
                    query += " WHERE agent = %s"
                    params.append(agent)
                    if level:
                        query += " AND level = %s"
                        params.append(level)
                elif level:
                    query += " WHERE level = %s"
                    params.append(level)
                query += " ORDER BY created_at DESC LIMIT %s"
                params.append(limit)
                cur.execute(query, params)
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def claim_pending_command(self) -> dict[str, Any] | None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM bot_commands
                    WHERE status = 'pending'
                    ORDER BY created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                    """
                )
                row = cur.fetchone()
                if row is None:
                    return None
                cols = [desc[0] for desc in cur.description]
                result = dict(zip(cols, row))
                cur.execute(
                    "UPDATE bot_commands SET status = 'claimed' WHERE id = %s",
                    (result["id"],),
                )
            conn.commit()
            return result
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def claim_pending_confirmation(self) -> dict[str, Any] | None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM bot_commands
                    WHERE status = 'pending_confirmation'
                    ORDER BY created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                    """
                )
                row = cur.fetchone()
                if row is None:
                    return None
                cols = [desc[0] for desc in cur.description]
                result = dict(zip(cols, row))
                cur.execute(
                    "UPDATE bot_commands SET status = 'claimed' WHERE id = %s",
                    (result["id"],),
                )
            conn.commit()
            return result
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def update_command_result(self, command_id: int, result: str, status: str = "done") -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE bot_commands
                    SET status = %s, result = %s, executed_at = %s
                    WHERE id = %s
                    """,
                    (status, result, datetime.now(), command_id),
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def start_session(self, version: str = "") -> int:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO bot_sessions (version) VALUES (%s) RETURNING id",
                    (version,),
                )
                row = cur.fetchone()
            conn.commit()
            return row[0] if row else 0
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def end_session(self, session_id: int, reason: str = "normal") -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE bot_sessions SET ended_at = %s, exit_reason = %s WHERE id = %s",
                    (datetime.now(), reason, session_id),
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def log_signal(self, signal: dict[str, Any]) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO signals (
                        signal_intent, signal_type, strategy, symbol,
                        direction, entry_price, stop_loss, take_profit_1,
                        confidence, reason, bull_case, bear_case,
                        author, tags, points_awarded, follower_score,
                        source, hku_signal_id
                    ) VALUES (
                        %(signal_intent)s, %(signal_type)s, %(strategy)s,
                        %(symbol)s, %(direction)s, %(entry_price)s,
                        %(stop_loss)s, %(take_profit_1)s, %(confidence)s,
                        %(reason)s, %(bull_case)s, %(bear_case)s,
                        %(author)s, %(tags)s, %(points_awarded)s,
                        %(follower_score)s, %(source)s, %(hku_signal_id)s
                    )
                    """,
                    signal,
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_signals(
        self,
        strategy: str | None = None,
        symbol: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                query = "SELECT * FROM signals"
                params: list[Any] = []
                conditions = []
                if strategy:
                    conditions.append("strategy = %s")
                    params.append(strategy)
                if symbol:
                    conditions.append("symbol = %s")
                    params.append(symbol)
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                query += " ORDER BY created_at DESC LIMIT %s"
                params.append(limit)
                cur.execute(query, params)
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def save_bot_command(
        self, command: str, payload: dict[str, Any] | None = None
    ) -> int:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO bot_commands (command, payload) VALUES (%s, %s) RETURNING id",
                    (command, psycopg2.extras.Json(payload) if payload else None),
                )
                row = cur.fetchone()
            conn.commit()
            return row[0] if row else 0
        finally:
            self._put(conn)
