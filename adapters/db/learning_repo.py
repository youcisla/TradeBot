"""Learning repository — migrated from database/learning_repo.py."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import psycopg2

from adapters.db.retry import with_retry

if TYPE_CHECKING:
    from adapters.db.pool import ConnectionPool


class LearningRepo:
    """PostgreSQL learning/confidence persistence layer."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def _conn(self) -> psycopg2.extensions.connection:
        return self._pool.get_conn()

    def _put(self, conn: psycopg2.extensions.connection) -> None:
        self._pool.put_conn(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_confidence(self, strategy: str) -> float:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT confidence FROM strategy_confidence WHERE strategy = %s",
                    (strategy,),
                )
                row = cur.fetchone()
                return float(row[0]) if row else 0.5
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def upsert_confidence(
        self,
        strategy: str,
        total_trades: int,
        total_score: int,
        win_streak: int = 0,
        last_score: float = 0.0,
    ) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO strategy_confidence (
                        strategy, confidence, total_trades, total_score,
                        win_streak, last_score, last_updated
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s
                    )
                    ON CONFLICT (strategy) DO UPDATE SET
                        confidence   = EXCLUDED.confidence,
                        total_trades = EXCLUDED.total_trades,
                        total_score  = EXCLUDED.total_score,
                        win_streak   = EXCLUDED.win_streak,
                        last_score   = EXCLUDED.last_score,
                        last_updated = EXCLUDED.last_updated
                    """,
                    (
                        strategy,
                        total_score / total_trades if total_trades > 0 else 0.5,
                        total_trades,
                        total_score,
                        win_streak,
                        last_score,
                        datetime.now(),
                    ),
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_rolling_avg_score(self, strategy: str, window: int = 20) -> float:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT AVG(score)::numeric(5,2)
                    FROM (
                        SELECT score FROM trade_scores
                        WHERE strategy = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                    ) sub
                    """,
                    (strategy, window),
                )
                row = cur.fetchone()
                return float(row[0]) if row and row[0] is not None else 0.0
        finally:
            self._put(conn)

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
    def bump_agent_reputation(
        self,
        agent: str,
        adopted: bool = False,
        points: int = 0,
        score: float = 0.0,
    ) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO agent_reputation (
                        agent, total_signals, adopted_signals,
                        total_points, last_score, win_streak, reputation_score
                    ) VALUES (%s, 1, %s, %s, %s, 0, 0.5)
                    ON CONFLICT (agent) DO UPDATE SET
                        total_signals   = agent_reputation.total_signals + 1,
                        adopted_signals = agent_reputation.adopted_signals + %s,
                        total_points    = agent_reputation.total_points + %s,
                        last_score      = %s,
                        win_streak      = CASE
                            WHEN %s > agent_reputation.last_score
                            THEN agent_reputation.win_streak + 1
                            ELSE 0
                        END,
                        reputation_score = CASE
                            WHEN agent_reputation.total_signals + 1 < 10 THEN 0.5
                            ELSE LEAST(1.0, agent_reputation.reputation_score + %s)
                        END,
                        updated_at = NOW()
                    """,
                    (agent, int(adopted), points, score, score, score, score, points / 100.0),
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_agent_reputations(self) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM agent_reputation ORDER BY reputation_score DESC")
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_subscriptions(self, leader_id: str | None = None) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                if leader_id:
                    cur.execute(
                        "SELECT * FROM subscriptions WHERE leader_id = %s",
                        (leader_id,),
                    )
                else:
                    cur.execute("SELECT * FROM subscriptions")
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
