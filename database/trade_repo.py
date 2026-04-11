"""Trade repository — extracted from database/db.py."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import psycopg2
import psycopg2.extras

if TYPE_CHECKING:
    from database.pool import ConnectionPool

logger = logging.getLogger(__name__)


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def _row_to_trade(row: dict) -> "Trade":
    """Convert a DB row dict to a Trade model instance.

    Trade is imported lazily to avoid circular imports — the Trade model
    itself may import from database components in the future.
    """
    # Lazy import to avoid circular reference
    from models.trade import Trade

    open_time = _ensure_utc(row["open_time"]) or datetime.now(UTC)
    close_time = _ensure_utc(row["close_time"])
    return Trade(
        id=row["id"],
        symbol=row["symbol"],
        strategy=row["strategy"],
        direction=row["direction"],
        entry_price=float(row["entry_price"]),
        lot_size=float(row["lot_size"]),
        stop_loss=float(row["stop_loss"]),
        take_profit_1=float(row["take_profit_1"]),
        take_profit_2=float(row["take_profit_2"]),
        take_profit_3=float(row["take_profit_3"]),
        take_profit_4=float(row["take_profit_4"] or 0),
        tp1_lots=float(row["tp1_lots"]),
        tp2_lots=float(row["tp2_lots"]),
        tp3_lots=float(row["tp3_lots"]),
        tp4_lots=float(row["tp4_lots"] or 0),
        tp1_hit=bool(row["tp1_hit"]),
        tp2_hit=bool(row["tp2_hit"]),
        tp3_hit=bool(row["tp3_hit"]),
        tp4_hit=bool(row.get("tp4_hit", False)),
        structural_be=float(row["structural_be"] or 0),
        status=row["status"],
        open_time=open_time,
        close_time=close_time,
        pnl=float(row["pnl"] or 0),
        commission=float(row["commission"] or 0),
        expected_edge_pct=float(row.get("expected_edge_pct") or 0),
        expected_pnl=float(row.get("expected_pnl") or 0),
        close_reason=row["close_reason"] or "",
        broker_ticket=int(row["broker_ticket"] or 0),
        spread_at_entry=float(row["spread_at_entry"] or 0),
        snap_rsi_aligned=bool(row["snap_rsi_aligned"]),
        snap_trend_aligned=bool(row["snap_trend_aligned"]),
        snap_volume_sufficient=bool(row["snap_volume_sufficient"]),
        snap_near_news_event=bool(row["snap_near_news_event"]),
        snap_market_condition=row["snap_market_condition"] or "",
        snap_session=row["snap_session"] or "",
        snap_day_of_week=row["snap_day_of_week"] or "",
    )


class TradeRepo:
    __slots__ = ("_pool",)

    def __init__(self, pool: "ConnectionPool") -> None:
        self._pool = pool

    def _conn(self):
        return self._pool.get_conn()

    def _put(self, conn):
        self._pool.put_conn(conn)

    def upsert_trade(self, t: "Trade") -> None:
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO trades (
                            id, symbol, strategy, direction, entry_price, lot_size,
                            stop_loss, take_profit_1, take_profit_2, take_profit_3,
                            take_profit_4, tp1_lots, tp2_lots, tp3_lots, tp4_lots,
                            tp1_hit, tp2_hit, tp3_hit, tp4_hit, structural_be, status,
                            open_time, close_time, pnl, current_price, commission, swap,
                            expected_edge_pct, expected_pnl,
                            close_reason, broker_ticket, spread_at_entry,
                            snap_rsi_aligned, snap_trend_aligned,
                            snap_volume_sufficient, snap_near_news_event,
                            snap_market_condition, snap_session, snap_day_of_week
                        ) VALUES (
                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,%s
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            stop_loss=EXCLUDED.stop_loss,
                            tp1_hit=EXCLUDED.tp1_hit, tp2_hit=EXCLUDED.tp2_hit,
                            tp3_hit=EXCLUDED.tp3_hit, tp4_hit=EXCLUDED.tp4_hit,
                            status=EXCLUDED.status,
                            close_time=EXCLUDED.close_time, pnl=EXCLUDED.pnl,
                            current_price=EXCLUDED.current_price,
                            commission=EXCLUDED.commission, swap=EXCLUDED.swap,
                            expected_edge_pct=EXCLUDED.expected_edge_pct,
                            expected_pnl=EXCLUDED.expected_pnl,
                            close_reason=EXCLUDED.close_reason,
                            lot_size=EXCLUDED.lot_size,
                            spread_at_entry=EXCLUDED.spread_at_entry
                        """,
                        (
                            t.id, t.symbol, t.strategy, t.direction, t.entry_price,
                            t.lot_size, t.stop_loss, t.take_profit_1, t.take_profit_2,
                            t.take_profit_3, t.take_profit_4,
                            t.tp1_lots, t.tp2_lots, t.tp3_lots, t.tp4_lots,
                            t.tp1_hit, t.tp2_hit, t.tp3_hit, t.tp4_hit, t.structural_be,
                            t.status, t.open_time, t.close_time,
                            t.pnl, t.current_price, t.commission, t.swap,
                            t.expected_edge_pct, t.expected_pnl,
                            t.close_reason,
                            t.broker_ticket, t.spread_at_entry,
                            t.snap_rsi_aligned, t.snap_trend_aligned,
                            t.snap_volume_sufficient, t.snap_near_news_event,
                            t.snap_market_condition, t.snap_session, t.snap_day_of_week,
                        ),
                    )
        finally:
            self._put(conn)

    def update_live_state(self, trade_id: str, pnl: float, current_price: float) -> None:
        """Lightweight update called every monitor cycle — only writes pnl + current_price."""
        conn = self._conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE trades SET pnl=%s, current_price=%s WHERE id=%s",
                        (pnl, current_price, trade_id),
                    )
        finally:
            self._put(conn)

    def get_open_trades(self) -> list["Trade"]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM trades WHERE status IN ('OPEN','PARTIAL')")
                return [_row_to_trade(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    def get_all_trades(self) -> list["Trade"]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM trades ORDER BY open_time DESC")
                return [_row_to_trade(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    def get_trade(self, trade_id: str) -> "Trade | None":
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM trades WHERE id = %s", (trade_id,))
                row = cur.fetchone()
                return _row_to_trade(row) if row else None
        finally:
            self._put(conn)

    def get_trade_by_broker_ticket(self, broker_ticket: int) -> "Trade | None":
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM trades WHERE broker_ticket = %s",
                    (broker_ticket,),
                )
                row = cur.fetchone()
                return _row_to_trade(row) if row else None
        finally:
            self._put(conn)

    def get_trades_closed_today(self) -> list["Trade"]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                today = datetime.now(UTC).strftime("%Y-%m-%d")
                cur.execute(
                    "SELECT * FROM trades WHERE status='CLOSED' AND close_time::date = %s",
                    (today,),
                )
                return [_row_to_trade(r) for r in cur.fetchall()]
        finally:
            self._put(conn)

    def count_closed_trades(self) -> int:
        conn = self._conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM trades "
                    "WHERE status='CLOSED' AND pnl IS NOT NULL AND pnl != 0"
                )
                row = cur.fetchone()
                return int(row[0]) if row else 0
        finally:
            self._put(conn)

    def get_closed_trades_since(self, since: datetime, limit: int = 500) -> list["Trade"]:
        conn = self._conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM trades
                       WHERE status='CLOSED' AND close_time >= %s
                       ORDER BY close_time ASC
                       LIMIT %s""",
                    (since, max(1, int(limit))),
                )
                return [_row_to_trade(r) for r in cur.fetchall()]
        finally:
            self._put(conn)
