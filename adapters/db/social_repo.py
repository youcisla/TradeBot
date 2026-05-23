"""Social repository — migrated from database/social_repo.py."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import psycopg2

from adapters.db.retry import with_retry

if TYPE_CHECKING:
    from adapters.db.pool import ConnectionPool


class SocialRepo:
    """PostgreSQL social/reputation persistence layer."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def _conn(self) -> psycopg2.extensions.connection:
        return self._pool.get_conn()

    def _put(self, conn: psycopg2.extensions.connection) -> None:
        self._pool.put_conn(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_agent_reputation(self, agent: str) -> dict[str, Any]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM agent_reputation WHERE agent = %s",
                    (agent,),
                )
                row = cur.fetchone()
                if row is None:
                    return {
                        "agent": agent,
                        "total_signals": 0,
                        "adopted_signals": 0,
                        "total_points": 0,
                        "win_streak": 0,
                        "last_score": 0.0,
                        "reputation_score": 0.5,
                    }
                cols = [desc[0] for desc in cur.description]
                return dict(zip(cols, row))
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def upsert_agent_reputation(
        self,
        agent: str,
        total_signals: int = 0,
        adopted_signals: int = 0,
        total_points: int = 0,
        win_streak: int = 0,
        last_score: float = 0.0,
        reputation_score: float = 0.5,
    ) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_reputation (
                        agent, total_signals, adopted_signals, total_points,
                        win_streak, last_score, reputation_score
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (agent) DO UPDATE SET
                        total_signals    = EXCLUDED.total_signals,
                        adopted_signals  = EXCLUDED.adopted_signals,
                        total_points     = EXCLUDED.total_points,
                        win_streak       = EXCLUDED.win_streak,
                        last_score       = EXCLUDED.last_score,
                        reputation_score = EXCLUDED.reputation_score,
                        updated_at       = NOW()
                    """,
                    (
                        agent,
                        total_signals,
                        adopted_signals,
                        total_points,
                        win_streak,
                        last_score,
                        reputation_score,
                    ),
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_subscriptions(self, follower_id: str | None = None, leader_id: str | None = None) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                query = "SELECT * FROM subscriptions WHERE 1=1"
                params: list[Any] = []
                if follower_id:
                    query += " AND follower_id = %s"
                    params.append(follower_id)
                if leader_id:
                    query += " AND leader_id = %s"
                    params.append(leader_id)
                cur.execute(query, params)
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def save_subscription(
        self,
        follower_id: str,
        leader_id: str,
        leader_strategy: str = "all",
    ) -> int:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO subscriptions (follower_id, leader_id, leader_strategy)
                    VALUES (%s, %s, %s)
                    ON CONFLICT DO NOTHING
                    RETURNING id
                    """,
                    (follower_id, leader_id, leader_strategy),
                )
                row = cur.fetchone()
            conn.commit()
            return row[0] if row else 0
        finally:
            self._put(conn)
