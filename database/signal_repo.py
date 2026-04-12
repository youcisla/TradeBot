"""Signal, ICT setup, and trade thesis repository — extracted from database/broker_repo.py."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import TYPE_CHECKING

import psycopg2.extras

if TYPE_CHECKING:
    from database.pool import ConnectionPool

logger = logging.getLogger(__name__)


class SignalRepo:
    __slots__ = ("_pool",)

    def __init__(self, pool: "ConnectionPool") -> None:
        self._pool = pool

    def _conn(self):
        return self._pool.get_conn()

    def _put(self, conn):
        self._pool.put_conn(conn)

    # ── signals ──────────────────────────────────────────────────────────

    def save_signal(
        self,
        *,
        signal_intent: str,
        signal_type: str,
        strategy: str,
        symbol: str = "",
        direction: str = "",
        entry_price: float = 0.0,
        stop_loss: float = 0.0,
        take_profit_1: float = 0.0,
        confidence: float = 0.5,
        reason: str = "",
        bull_case: str = "",
        bear_case: str = "",
        author: str = "bot",
        tags: list[str] | None = None,
    ) -> int:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO signals
                           (signal_intent, signal_type, strategy, symbol, direction,
                            entry_price, stop_loss, take_profit_1, confidence,
                            reason, bull_case, bear_case, author, tags)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           RETURNING id""",
                        (
                            signal_intent, signal_type, strategy, symbol, direction,
                            entry_price, stop_loss, take_profit_1, confidence,
                            reason, bull_case, bear_case, author,
                            tags or [],
                        ),
                    )
                    return cur.fetchone()[0]
        finally:
            self._put(conn)

    def save_hku_signal(
        self,
        signal,
        hku_signal_id: str,
        author: str = "bot",
    ) -> int:
        """Save an external HKU signal to the signals table.

        Args:
            signal:       Signal instance to save.
            hku_signal_id: Original HKU signal ID for cross-reference.
            author:       Author tag — defaults to "bot"; use "hku:{agent_id}" for HKU.

        Returns:
            The inserted row ID.
        """
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO signals
                           (signal_intent, signal_type, strategy, symbol, direction,
                            entry_price, stop_loss, take_profit_1, confidence,
                            reason, bull_case, bear_case, author, tags,
                            source, hku_signal_id)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           RETURNING id""",
                        (
                            signal.signal_intent,
                            "OPERATION",
                            signal.strategy,
                            signal.symbol,
                            signal.direction,
                            signal.entry_price,
                            signal.stop_loss,
                            signal.take_profit_1,
                            signal.confidence,
                            signal.reason,
                            signal.bull_case,
                            signal.bear_case,
                            author,
                            ["hku"],
                            "hku",
                            hku_signal_id,
                        ),
                    )
                    return cur.fetchone()[0]
        finally:
            self._put(conn)

    def get_signals(
        self,
        signal_intent: str | None = None,
        signal_type: str | None = None,
        strategy: str | None = None,
        author: str | None = None,
        source: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                conditions = []
                params: list = []
                if signal_intent:
                    conditions.append("signal_intent = %s")
                    params.append(signal_intent)
                if signal_type:
                    conditions.append("signal_type = %s")
                    params.append(signal_type)
                if strategy:
                    conditions.append("strategy = %s")
                    params.append(strategy)
                if author:
                    conditions.append("author = %s")
                    params.append(author)
                if source:
                    conditions.append("source = %s")
                    params.append(source)
                where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
                params.append(max(1, limit))
                cur.execute(
                    f"""SELECT * FROM signals
                        {where}
                        ORDER BY created_at DESC
                        LIMIT %s""",
                    params,
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    def mark_signal_points_awarded(self, signal_id: int) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE signals SET points_awarded = TRUE WHERE id = %s",
                        (signal_id,),
                    )
        finally:
            self._put(conn)

    # ── ICT setups ────────────────────────────────────────────────────────

    def save_ict_setup(self, setup: dict) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO ict_setups
                           (symbol, direction, model, entry_price, stop_loss,
                            take_profit_1, take_profit_2, take_profit_3,
                            confidence, htf_bias, htf_regime, premium_discount,
                            entry_zone, reason, confluences, missing, session,
                            executed, trade_id)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                        (
                            setup.get("symbol"),
                            setup.get("direction"),
                            setup.get("model"),
                            setup.get("entry_price"),
                            setup.get("stop_loss"),
                            setup.get("take_profit_1"),
                            setup.get("take_profit_2"),
                            setup.get("take_profit_3"),
                            setup.get("confidence"),
                            setup.get("htf_bias", ""),
                            setup.get("htf_regime", ""),
                            setup.get("premium_discount", ""),
                            setup.get("entry_zone", ""),
                            setup.get("reason", ""),
                            json.dumps(setup.get("confluences", {})),
                            setup.get("missing", []),
                            setup.get("session", ""),
                            setup.get("executed", False),
                            setup.get("trade_id"),
                        ),
                    )
        finally:
            self._put(conn)

    # ── trade theses ─────────────────────────────────────────────────────

    def save_trade_thesis(
        self,
        *,
        symbol: str,
        direction: str = "",
        stage: str = "IDEA",
        trade_id: str | None = None,
        entry_price: float | None = None,
        sl_price: float | None = None,
        tp_price: float | None = None,
        rr_ratio: float | None = None,
        bull_case: str = "",
        bear_case: str = "",
        entry_reason: str = "",
        notes: str = "",
    ) -> int:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO trade_theses
                           (trade_id, symbol, direction, stage,
                            entry_price, sl_price, tp_price, rr_ratio,
                            bull_case, bear_case, entry_reason, notes)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                           RETURNING id""",
                        (trade_id, symbol, direction, stage,
                         entry_price, sl_price, tp_price, rr_ratio,
                         bull_case, bear_case, entry_reason, notes),
                    )
                    return cur.fetchone()[0]
        finally:
            self._put(conn)

    def get_trade_thesis(self, trade_id: str) -> dict | None:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM trade_theses
                       WHERE trade_id = %s
                       ORDER BY created_at DESC
                       LIMIT 1""",
                    (trade_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            self._put(conn)

    def update_trade_outcome(
        self,
        trade_id: str,
        *,
        actual_outcome: str,
        mae_pips: float | None = None,
        mfe_pips: float | None = None,
        notes: str = "",
    ) -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE trade_theses
                           SET stage          = 'CLOSED',
                               actual_outcome = %s,
                               mae_pips       = %s,
                               mfe_pips       = %s,
                               notes          = CASE WHEN %s = '' THEN notes ELSE %s END,
                               closed_at      = NOW()
                           WHERE trade_id = %s""",
                        (actual_outcome, mae_pips, mfe_pips,
                         notes, notes, trade_id),
                    )
        finally:
            self._put(conn)
