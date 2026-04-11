"""Social/copy-trading repository — extracted from database/broker_repo.py."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import psycopg2.extras

if TYPE_CHECKING:
    from database.pool import ConnectionPool

logger = logging.getLogger(__name__)


class SocialRepo:
    __slots__ = ("_pool",)

    def __init__(self, pool: "ConnectionPool") -> None:
        self._pool = pool

    def _conn(self):
        return self._pool.get_conn()

    def _put(self, conn):
        self._pool.put_conn(conn)

    # ── agent reputation ─────────────────────────────────────────────────

    def get_agent_reputation(self, agent: str) -> dict:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM agent_reputation WHERE agent = %s",
                    (agent,),
                )
                row = cur.fetchone()
                if row:
                    return dict(row)
                # Create default record on first access
                cur.execute(
                    "INSERT INTO agent_reputation (agent) VALUES (%s) ON CONFLICT (agent) DO NOTHING",
                    (agent,),
                )
                cur.execute(
                    "SELECT * FROM agent_reputation WHERE agent = %s",
                    (agent,),
                )
                row = cur.fetchone()
                return dict(row) if row else {
                    "agent": agent, "total_signals": 0, "adopted_signals": 0,
                    "total_points": 0, "win_streak": 0, "last_score": 0,
                    "reputation_score": 0.5,
                }
        finally:
            self._put(conn)

    def bump_agent_reputation(
        self,
        agent: str,
        *,
        adopted: bool = False,
        points_delta: int = 0,
        score_delta: int = 0,
    ) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    if adopted:
                        cur.execute(
                            """INSERT INTO agent_reputation
                               (agent, total_signals, adopted_signals, total_points,
                                last_score, updated_at)
                               VALUES (%s, 1, 1, %s, %s, NOW())
                               ON CONFLICT (agent) DO UPDATE SET
                                   total_signals  = agent_reputation.total_signals + 1,
                                   adopted_signals = agent_reputation.adopted_signals + 1,
                                   total_points    = agent_reputation.total_points + %s,
                                   last_score      = %s,
                                   win_streak      = agent_reputation.win_streak + 1,
                                   updated_at      = NOW()""",
                            (agent, points_delta, score_delta, points_delta, score_delta),
                        )
                    else:
                        cur.execute(
                            """INSERT INTO agent_reputation
                               (agent, total_signals, total_points, last_score, updated_at)
                               VALUES (%s, 1, %s, %s, NOW())
                               ON CONFLICT (agent) DO UPDATE SET
                                   total_signals  = agent_reputation.total_signals + 1,
                                   total_points   = agent_reputation.total_points + %s,
                                   last_score     = %s,
                                   updated_at     = NOW()""",
                            (agent, points_delta, score_delta, points_delta, score_delta),
                        )
        finally:
            self._put(conn)

    def get_leaderboard(self, limit: int = 10) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT agent, total_signals, adopted_signals,
                              total_points, win_streak, reputation_score, updated_at
                       FROM agent_reputation
                       ORDER BY total_points DESC
                       LIMIT %s""",
                    (max(1, limit),),
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    # ── subscriptions (copy-trading) ─────────────────────────────────────

    def save_subscription(
        self,
        follower_id: str,
        leader_id: str,
        leader_strategy: str = "all",
    ) -> int:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO subscriptions (follower_id, leader_id, leader_strategy)
                           VALUES (%s, %s, %s)
                           ON CONFLICT DO NOTHING
                           RETURNING id""",
                        (follower_id, leader_id, leader_strategy),
                    )
                    row = cur.fetchone()
                    return int(row[0]) if row else 0
        finally:
            self._put(conn)

    def get_subscriptions(
        self,
        follower_id: str | None = None,
        leader_id: str | None = None,
    ) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                conditions = []
                params: list = []
                if follower_id:
                    conditions.append("follower_id = %s")
                    params.append(follower_id)
                if leader_id:
                    conditions.append("leader_id = %s")
                    params.append(leader_id)
                where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
                cur.execute(
                    f"""SELECT * FROM subscriptions {where}
                        ORDER BY created_at DESC""",
                    params,
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    def delete_subscription(self, follower_id: str, leader_id: str) -> bool:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """DELETE FROM subscriptions
                           WHERE follower_id = %s AND leader_id = %s""",
                        (follower_id, leader_id),
                    )
                    return cur.rowcount > 0
        finally:
            self._put(conn)

    def get_followers(self, leader_id: str) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM subscriptions
                       WHERE leader_id = %s AND status = 'ACTIVE'
                       ORDER BY created_at DESC""",
                    (leader_id,),
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)
