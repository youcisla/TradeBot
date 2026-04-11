"""Learning/scoring repository — extracted from database/db.py."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

import psycopg2.extras

if TYPE_CHECKING:
    from database.pool import ConnectionPool

logger = logging.getLogger(__name__)


class LearningRepo:
    __slots__ = ("_pool",)

    def __init__(self, pool: "ConnectionPool") -> None:
        self._pool = pool

    def _conn(self):
        return self._pool.get_conn()

    def _put(self, conn):
        self._pool.put_conn(conn)

    # ── trade scores ─────────────────────────────────────────────────────

    def insert_score(
        self,
        trade_id: str,
        strategy: str,
        symbol: str,
        session: str,
        market_condition: str,
        spread_at_entry: float,
        day_of_week: str,
        score: int,
        pnl: float,
        rsi_aligned: bool,
        trend_aligned: bool,
        volume_sufficient: bool,
        near_news_event: bool,
        filters_aligned: bool,
    ) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO trade_scores
                           (trade_id, strategy, symbol, session, market_condition,
                            spread_at_entry, day_of_week, score, pnl,
                            rsi_aligned, trend_aligned, volume_sufficient,
                            near_news_event, filters_aligned)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (trade_id, strategy, symbol, session, market_condition,
                         spread_at_entry, day_of_week, score, pnl,
                         rsi_aligned, trend_aligned,
                         volume_sufficient, near_news_event,
                         filters_aligned),
                    )
        finally:
            self._put(conn)

    # ── strategy confidence ──────────────────────────────────────────────

    def get_confidence(self, strategy: str) -> float:
        from config import settings

        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT confidence FROM strategy_confidence WHERE strategy = %s",
                    (strategy,),
                )
                row = cur.fetchone()
                return float(row["confidence"]) if row else settings.DEFAULT_CONFIDENCE
        finally:
            self._put(conn)

    def upsert_confidence(
        self,
        strategy: str,
        confidence: float,
        total_trades: int,
        total_score: int,
    ) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO strategy_confidence
                           (strategy, confidence, total_trades, total_score, last_updated)
                           VALUES (%s, %s, %s, %s, NOW())
                           ON CONFLICT (strategy) DO UPDATE SET
                               confidence=EXCLUDED.confidence,
                               total_trades=strategy_confidence.total_trades + EXCLUDED.total_trades,
                               total_score=strategy_confidence.total_score + EXCLUDED.total_score,
                               last_updated=NOW()""",
                        (strategy, confidence, total_trades, total_score),
                    )
        finally:
            self._put(conn)

    def get_rolling_avg_score(self, strategy: str, n: int = 10) -> float | None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT AVG(score) FROM (
                           SELECT score FROM trade_scores
                           WHERE strategy = %s
                           ORDER BY created_at DESC LIMIT %s
                       ) sub""",
                    (strategy, n),
                )
                row = cur.fetchone()
                return float(row[0]) if row and row[0] is not None else None
        finally:
            self._put(conn)

    def get_strategy_streak(self, strategy: str) -> int:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT win_streak FROM strategy_confidence WHERE strategy = %s",
                    (strategy,),
                )
                row = cur.fetchone()
                return int(row[0]) if row and row[0] is not None else 0
        finally:
            self._put(conn)

    def update_strategy_streak(
        self,
        strategy: str,
        win_streak: int,
        last_score: float,
    ) -> None:
        from config import settings

        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO strategy_confidence
                               (strategy, confidence, win_streak, last_score, last_updated)
                           VALUES (%s, %s, %s, %s, NOW())
                           ON CONFLICT (strategy) DO UPDATE SET
                               win_streak = EXCLUDED.win_streak,
                               last_score = EXCLUDED.last_score,
                               last_updated = NOW()""",
                        (strategy, settings.DEFAULT_CONFIDENCE, win_streak, last_score),
                    )
        finally:
            self._put(conn)

    # ── performance snapshots ─────────────────────────────────────────────

    def save_performance_snapshot(
        self,
        period_type: str,
        period_key: str,
        trades: int,
        wins: int,
        losses: int,
        total_pnl: float,
        avg_score: float,
        win_rate: float,
    ) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO performance_snapshots
                               (period_type, period_key, trades, wins, losses,
                                total_pnl, avg_score, win_rate)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                           ON CONFLICT (period_type, period_key) DO UPDATE SET
                               trades    = EXCLUDED.trades,
                               wins      = EXCLUDED.wins,
                               losses    = EXCLUDED.losses,
                               total_pnl = EXCLUDED.total_pnl,
                               avg_score = EXCLUDED.avg_score,
                               win_rate  = EXCLUDED.win_rate""",
                        (period_type, period_key, trades, wins, losses,
                         total_pnl, avg_score, win_rate),
                    )
        finally:
            self._put(conn)

    def get_previous_snapshot(self, period_type: str, before_key: str) -> dict | None:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM performance_snapshots
                       WHERE period_type = %s AND period_key < %s
                       ORDER BY period_key DESC LIMIT 1""",
                    (period_type, before_key),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            self._put(conn)

    def get_period_stats(self, since: datetime, until: datetime) -> dict:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT COUNT(*),
                              COUNT(*) FILTER (WHERE pnl >= 0),
                              COUNT(*) FILTER (WHERE pnl < 0),
                              COALESCE(SUM(pnl), 0),
                              COALESCE(AVG(score), 0)
                       FROM trade_scores
                       WHERE created_at >= %s AND created_at < %s""",
                    (since, until),
                )
                row = cur.fetchone()
                if not row or row[0] == 0:
                    return {"trades": 0, "wins": 0, "losses": 0,
                            "total_pnl": 0.0, "avg_score": 0.0, "win_rate": 0.0}
                trades, wins, losses, total_pnl, avg_score = row
                return {
                    "trades":    int(trades),
                    "wins":      int(wins),
                    "losses":    int(losses),
                    "total_pnl": float(total_pnl),
                    "avg_score": float(avg_score),
                    "win_rate":  round(int(wins) / int(trades), 4) if trades else 0.0,
                }
        finally:
            self._put(conn)

    def get_recent_strategy_regime_stats(
        self,
        lookback_hours: int = 48,
        min_trades: int = 3,
    ) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT
                           strategy,
                           COALESCE(NULLIF(market_condition, ''), 'unknown') AS market_condition,
                           COUNT(*)::int AS trades,
                           COUNT(*) FILTER (WHERE pnl >= 0)::int AS wins,
                           COALESCE(AVG(score), 0)::float AS avg_score,
                           COALESCE(AVG(pnl), 0)::float AS avg_pnl
                       FROM trade_scores
                       WHERE created_at >= NOW() - (%s || ' hours')::interval
                       GROUP BY strategy, COALESCE(NULLIF(market_condition, ''), 'unknown')
                       HAVING COUNT(*) >= %s
                       ORDER BY strategy ASC, trades DESC""",
                    (str(max(1, lookback_hours)), max(1, min_trades)),
                )
                return [dict(row) for row in cur.fetchall()]
        finally:
            self._put(conn)

    def get_recent_context_outcomes(
        self,
        strategy: str,
        symbol: str,
        session: str,
        market_condition: str,
        lookback_days: int = 30,
        limit: int = 50,
    ) -> dict[str, float | int]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT
                           COUNT(*)::int AS trades,
                           COALESCE(AVG(score), 0)::float AS avg_score,
                           COALESCE(AVG(pnl), 0)::float AS avg_pnl,
                           COALESCE(AVG(CASE WHEN pnl >= 0 THEN 1.0 ELSE 0.0 END), 0)::float AS win_rate
                       FROM (
                           SELECT score, pnl
                           FROM trade_scores
                           WHERE strategy = %s
                             AND symbol = %s
                             AND COALESCE(session, '') = COALESCE(%s, '')
                             AND COALESCE(market_condition, '') = COALESCE(%s, '')
                             AND created_at >= NOW() - (%s || ' days')::interval
                           ORDER BY created_at DESC
                           LIMIT %s
                       ) recent""",
                    (
                        strategy,
                        symbol,
                        session or "",
                        market_condition or "",
                        str(max(1, lookback_days)),
                        max(1, limit),
                    ),
                )
                row = cur.fetchone()
                if not row:
                    return {"trades": 0, "avg_score": 0.0, "avg_pnl": 0.0, "win_rate": 0.0}
                trades, avg_score, avg_pnl, win_rate = row
                return {
                    "trades":    int(trades or 0),
                    "avg_score": float(avg_score or 0.0),
                    "avg_pnl":   float(avg_pnl or 0.0),
                    "win_rate":  float(win_rate or 0.0),
                }
        finally:
            self._put(conn)

    def boost_all_strategy_confidence(self, boost: float) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE strategy_confidence
                           SET confidence = LEAST(1.0, confidence + %s),
                               last_updated = NOW()""",
                        (boost,),
                    )
        finally:
            self._put(conn)

    def reset_learning_state(self) -> dict[str, int]:
        """Delete historical learning state (scores, confidence, snapshots)."""
        conn = self._conn()
        removed_scores = 0
        removed_confidence = 0
        removed_snapshots = 0
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM trade_scores")
                    removed_scores = cur.rowcount

                    cur.execute("DELETE FROM strategy_confidence")
                    removed_confidence = cur.rowcount

                    cur.execute("DELETE FROM performance_snapshots")
                    removed_snapshots = cur.rowcount

            return {
                "trade_scores":            removed_scores,
                "strategy_confidence":    removed_confidence,
                "performance_snapshots":  removed_snapshots,
            }
        finally:
            self._put(conn)
