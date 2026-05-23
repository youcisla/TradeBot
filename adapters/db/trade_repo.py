"""Trade repository — migrated from database/trade_repo.py."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

import psycopg2

from adapters.db.retry import with_retry

if TYPE_CHECKING:
    from adapters.db.pool import ConnectionPool


class TradeRepo:
    """PostgreSQL trade persistence layer."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def _conn(self) -> psycopg2.extensions.connection:
        return self._pool.get_conn()

    def _put(self, conn: psycopg2.extensions.connection) -> None:
        self._pool.put_conn(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def upsert_trade(self, trade: dict[str, Any]) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trades (
                        id, symbol, strategy, direction,
                        entry_price, lot_size, stop_loss,
                        take_profit_1, take_profit_2, take_profit_3,
                        tp1_lots, tp2_lots, tp3_lots,
                        tp1_hit, tp2_hit, tp3_hit,
                        status, open_time, close_time, pnl,
                        commission, swap,
                        expected_edge_pct, expected_pnl,
                        close_reason, broker_ticket, spread_at_entry,
                        snap_rsi_aligned, snap_trend_aligned,
                        snap_volume_sufficient, snap_near_news_event,
                        snap_market_condition, snap_session, snap_day_of_week,
                        take_profit_4, tp4_lots, tp4_hit, structural_be,
                        current_price
                    ) VALUES (
                        %(id)s, %(symbol)s, %(strategy)s, %(direction)s,
                        %(entry_price)s, %(lot_size)s, %(stop_loss)s,
                        %(take_profit_1)s, %(take_profit_2)s, %(take_profit_3)s,
                        %(tp1_lots)s, %(tp2_lots)s, %(tp3_lots)s,
                        %(tp1_hit)s, %(tp2_hit)s, %(tp3_hit)s,
                        %(status)s, %(open_time)s, %(close_time)s, %(pnl)s,
                        %(commission)s, %(swap)s,
                        %(expected_edge_pct)s, %(expected_pnl)s,
                        %(close_reason)s, %(broker_ticket)s, %(spread_at_entry)s,
                        %(snap_rsi_aligned)s, %(snap_trend_aligned)s,
                        %(snap_volume_sufficient)s, %(snap_near_news_event)s,
                        %(snap_market_condition)s, %(snap_session)s, %(snap_day_of_week)s,
                        %(take_profit_4)s, %(tp4_lots)s, %(tp4_hit)s, %(structural_be)s,
                        %(current_price)s
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        status          = EXCLUDED.status,
                        close_time      = EXCLUDED.close_time,
                        pnl             = EXCLUDED.pnl,
                        commission      = EXCLUDED.commission,
                        swap            = EXCLUDED.swap,
                        tp1_hit         = EXCLUDED.tp1_hit,
                        tp2_hit         = EXCLUDED.tp2_hit,
                        tp3_hit         = EXCLUDED.tp3_hit,
                        tp4_hit         = EXCLUDED.tp4_hit,
                        take_profit_4   = EXCLUDED.take_profit_4,
                        tp4_lots        = EXCLUDED.tp4_lots,
                        current_price   = EXCLUDED.current_price,
                        snap_rsi_aligned = EXCLUDED.snap_rsi_aligned,
                        snap_trend_aligned = EXCLUDED.snap_trend_aligned,
                        snap_volume_sufficient = EXCLUDED.snap_volume_sufficient,
                        snap_near_news_event   = EXCLUDED.snap_near_news_event,
                        snap_market_condition  = EXCLUDED.snap_market_condition,
                        snap_session           = EXCLUDED.snap_session,
                        snap_day_of_week       = EXCLUDED.snap_day_of_week
                    """,
                    trade,
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_open_trades(self) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM trades WHERE status IN ('OPEN', 'PARTIAL') ORDER BY open_time DESC"
                )
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_trade(self, trade_id: str) -> dict[str, Any] | None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT * FROM trades WHERE id = %s", (trade_id,))
                row = cur.fetchone()
                if row is None:
                    return None
                cols = [desc[0] for desc in cur.description]
                return dict(zip(cols, row))
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_closed_trades(
        self,
        limit: int = 100,
        symbol: str | None = None,
        strategy: str | None = None,
    ) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                query = "SELECT * FROM trades WHERE status = 'CLOSED'"
                params: list[Any] = []
                if symbol:
                    query += " AND symbol = %s"
                    params.append(symbol)
                if strategy:
                    query += " AND strategy = %s"
                    params.append(strategy)
                query += " ORDER BY close_time DESC LIMIT %s"
                params.append(limit)
                cur.execute(query, params)
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_trades_by_symbol(self, symbol: str, status: str | None = None) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                if status:
                    cur.execute(
                        "SELECT * FROM trades WHERE symbol = %s AND status = %s ORDER BY open_time DESC",
                        (symbol, status),
                    )
                else:
                    cur.execute(
                        "SELECT * FROM trades WHERE symbol = %s ORDER BY open_time DESC",
                        (symbol,),
                    )
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def count_open_trades(self) -> int:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM trades WHERE status IN ('OPEN', 'PARTIAL')"
                )
                return int(cur.fetchone()[0])
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def save_trade_score(self, score: dict[str, Any]) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trade_scores (
                        trade_id, strategy, symbol, session, market_condition,
                        spread_at_entry, day_of_week, score, pnl,
                        rsi_aligned, trend_aligned, volume_sufficient,
                        near_news_event, filters_aligned
                    ) VALUES (
                        %(trade_id)s, %(strategy)s, %(symbol)s, %(session)s,
                        %(market_condition)s, %(spread_at_entry)s, %(day_of_week)s,
                        %(score)s, %(pnl)s, %(rsi_aligned)s, %(trend_aligned)s,
                        %(volume_sufficient)s, %(near_news_event)s, %(filters_aligned)s
                    )
                    """,
                    score,
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_recent_scores(self, strategy: str, limit: int = 50) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM trade_scores
                    WHERE strategy = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (strategy, limit),
                )
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def save_ict_setup(self, setup: dict[str, Any]) -> int:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ict_setups (
                        symbol, direction, model, entry_price, stop_loss,
                        take_profit_1, take_profit_2, take_profit_3,
                        confidence, htf_bias, htf_regime, premium_discount,
                        entry_zone, reason, confluences, missing,
                        session, executed, trade_id
                    ) VALUES (
                        %(symbol)s, %(direction)s, %(model)s, %(entry_price)s,
                        %(stop_loss)s, %(take_profit_1)s, %(take_profit_2)s, %(take_profit_3)s,
                        %(confidence)s, %(htf_bias)s, %(htf_regime)s,
                        %(premium_discount)s, %(entry_zone)s, %(reason)s,
                        %(confluences)s, %(missing)s, %(session)s,
                        %(executed)s, %(trade_id)s
                    ) RETURNING id
                    """,
                    setup,
                )
                row = cur.fetchone()
            conn.commit()
            return row[0] if row else 0
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_open_ict_setups(self, symbol: str | None = None) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                if symbol:
                    cur.execute(
                        "SELECT * FROM ict_setups WHERE symbol = %s AND executed = FALSE ORDER BY created_at DESC",
                        (symbol,),
                    )
                else:
                    cur.execute(
                        "SELECT * FROM ict_setups WHERE executed = FALSE ORDER BY created_at DESC"
                    )
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def mark_setup_executed(self, setup_id: int, trade_id: str) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE ict_setups SET executed = TRUE, trade_id = %s WHERE id = %s",
                    (trade_id, setup_id),
                )
            conn.commit()
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def save_trade_thesis(self, thesis: dict[str, Any]) -> int:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO trade_theses (
                        trade_id, symbol, direction, stage, entry_price,
                        sl_price, tp_price, rr_ratio, bull_case, bear_case,
                        entry_reason, actual_outcome, mae_pips, mfe_pips, notes
                    ) VALUES (
                        %(trade_id)s, %(symbol)s, %(direction)s, %(stage)s,
                        %(entry_price)s, %(sl_price)s, %(tp_price)s, %(rr_ratio)s,
                        %(bull_case)s, %(bear_case)s, %(entry_reason)s,
                        %(actual_outcome)s, %(mae_pips)s, %(mfe_pips)s, %(notes)s
                    ) RETURNING id
                    """,
                    thesis,
                )
                row = cur.fetchone()
            conn.commit()
            return row[0] if row else 0
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_trade_theses(self, trade_id: str) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM trade_theses WHERE trade_id = %s ORDER BY created_at DESC",
                    (trade_id,),
                )
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_performance_snapshots(
        self, period_type: str, period_key: str
    ) -> dict[str, Any] | None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM performance_snapshots
                    WHERE period_type = %s AND period_key = %s
                    """,
                    (period_type, period_key),
                )
                row = cur.fetchone()
                if row is None:
                    return None
                cols = [desc[0] for desc in cur.description]
                return dict(zip(cols, row))
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def upsert_performance_snapshot(
        self, period_type: str, period_key: str, data: dict[str, Any]
    ) -> None:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO performance_snapshots (
                        period_type, period_key, trades, wins, losses,
                        total_pnl, avg_score, win_rate
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (period_type, period_key) DO UPDATE SET
                        trades     = EXCLUDED.trades,
                        wins       = EXCLUDED.wins,
                        losses     = EXCLUDED.losses,
                        total_pnl  = EXCLUDED.total_pnl,
                        avg_score  = EXCLUDED.avg_score,
                        win_rate   = EXCLUDED.win_rate
                    """,
                    (
                        period_type,
                        period_key,
                        data["trades"],
                        data["wins"],
                        data["losses"],
                        data["total_pnl"],
                        data["avg_score"],
                        data["win_rate"],
                    ),
                )
            conn.commit()
        finally:
            self._put(conn)
