"""Signal repository — migrated from database/signal_repo.py."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

import psycopg2

from adapters.db.retry import with_retry

if TYPE_CHECKING:
    from adapters.db.pool import ConnectionPool


class SignalRepo:
    """PostgreSQL signal persistence layer."""

    def __init__(self, pool: ConnectionPool) -> None:
        self._pool = pool

    def _conn(self) -> psycopg2.extensions.connection:
        return self._pool.get_conn()

    def _put(self, conn: psycopg2.extensions.connection) -> None:
        self._pool.put_conn(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def save_signal(self, signal: dict[str, Any]) -> int:
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
                    ) RETURNING id
                    """,
                    signal,
                )
                row = cur.fetchone()
            conn.commit()
            return row[0] if row else 0
        finally:
            self._put(conn)

    @with_retry(max_retries=3, base_delay=0.5)
    def get_signals(
        self,
        strategy: str | None = None,
        author: str | None = None,
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
                if author:
                    conditions.append("author = %s")
                    params.append(author)
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
    def get_ict_setups(self, symbol: str | None = None, executed: bool | None = None) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                query = "SELECT * FROM ict_setups"
                params: list[Any] = []
                conditions = []
                if symbol:
                    conditions.append("symbol = %s")
                    params.append(symbol)
                if executed is not None:
                    conditions.append("executed = %s")
                    params.append(executed)
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                query += " ORDER BY created_at DESC"
                cur.execute(query, params)
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
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
    def get_trade_theses(self, trade_id: str | None = None, stage: str | None = None) -> list[dict[str, Any]]:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                query = "SELECT * FROM trade_theses"
                params: list[Any] = []
                conditions = []
                if trade_id:
                    conditions.append("trade_id = %s")
                    params.append(trade_id)
                if stage:
                    conditions.append("stage = %s")
                    params.append(stage)
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
                query += " ORDER BY created_at DESC"
                cur.execute(query, params)
                cols = [desc[0] for desc in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        finally:
            self._put(conn)
