"""SQLite database handler for the trading bot.

Tables
------
- bot_trades          – open & closed trade state (crash recovery)
- trade_scores        – learning system scoring per closed trade
- strategy_confidence – per-strategy confidence values
- events              – general event log
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from config import settings
from models.trade import Trade

logger = logging.getLogger(__name__)

# ── SQL Statements ───────────────────────────────────────────────────────

_CREATE_BOT_TRADES = """
CREATE TABLE IF NOT EXISTS bot_trades (
    id                  TEXT PRIMARY KEY,
    symbol              TEXT NOT NULL,
    strategy            TEXT NOT NULL,
    direction           TEXT NOT NULL,
    entry_price         REAL NOT NULL,
    lot_size            REAL NOT NULL,
    stop_loss           REAL NOT NULL,
    take_profit_1       REAL NOT NULL,
    take_profit_2       REAL NOT NULL,
    take_profit_3       REAL NOT NULL,
    tp1_lots            REAL NOT NULL,
    tp2_lots            REAL NOT NULL,
    tp3_lots            REAL NOT NULL,
    tp1_hit             INTEGER DEFAULT 0,
    tp2_hit             INTEGER DEFAULT 0,
    tp3_hit             INTEGER DEFAULT 0,
    status              TEXT DEFAULT 'OPEN',
    open_time           TEXT NOT NULL,
    close_time          TEXT,
    pnl                 REAL DEFAULT 0.0,
    close_reason        TEXT DEFAULT '',
    broker_ticket       INTEGER DEFAULT 0,
    spread_at_entry     REAL DEFAULT 0.0,
    snap_rsi_aligned        INTEGER DEFAULT 0,
    snap_trend_aligned      INTEGER DEFAULT 0,
    snap_volume_sufficient  INTEGER DEFAULT 0,
    snap_near_news_event    INTEGER DEFAULT 0,
    snap_market_condition   TEXT DEFAULT '',
    snap_session            TEXT DEFAULT '',
    snap_day_of_week        TEXT DEFAULT ''
);
"""

_CREATE_TRADE_SCORES = """
CREATE TABLE IF NOT EXISTS trade_scores (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_id            TEXT NOT NULL,
    strategy            TEXT NOT NULL,
    symbol              TEXT NOT NULL,
    session             TEXT,
    market_condition    TEXT,
    spread_at_entry     REAL,
    day_of_week         TEXT,
    score               INTEGER NOT NULL,
    pnl                 REAL,
    rsi_aligned         INTEGER,
    trend_aligned       INTEGER,
    volume_sufficient   INTEGER,
    near_news_event     INTEGER,
    filters_aligned     INTEGER,
    created_at          TEXT DEFAULT (datetime('now'))
);
"""

_CREATE_STRATEGY_CONFIDENCE = """
CREATE TABLE IF NOT EXISTS strategy_confidence (
    strategy        TEXT PRIMARY KEY,
    confidence      REAL NOT NULL DEFAULT 0.5,
    total_trades    INTEGER DEFAULT 0,
    total_score     INTEGER DEFAULT 0,
    last_updated    TEXT DEFAULT (datetime('now'))
);
"""

_CREATE_EVENTS = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT DEFAULT (datetime('now')),
    level       TEXT NOT NULL,
    source      TEXT NOT NULL,
    message     TEXT NOT NULL,
    data        TEXT
);
"""


class Database:
    """Thin wrapper around SQLite for the trading bot."""

    def __init__(self, db_path: str | None = None) -> None:
        self._path = db_path or settings.DB_PATH
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        self._conn: sqlite3.Connection | None = None
        self._connect()
        self._create_tables()

    # ── connection ───────────────────────────────────────────────────────

    def _connect(self) -> None:
        self._conn = sqlite3.connect(self._path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._connect()
        assert self._conn is not None
        return self._conn

    # ── schema ───────────────────────────────────────────────────────────

    def _create_tables(self) -> None:
        with self.conn:
            self.conn.executescript(
                _CREATE_BOT_TRADES
                + _CREATE_TRADE_SCORES
                + _CREATE_STRATEGY_CONFIDENCE
                + _CREATE_EVENTS
            )
        logger.info("Database tables verified at %s", self._path)

    # ── trade persistence ────────────────────────────────────────────────

    def upsert_trade(self, t: Trade) -> None:
        """Insert or replace a trade row (used for both create and update)."""
        with self.conn:
            self.conn.execute(
                """
                INSERT OR REPLACE INTO bot_trades (
                    id, symbol, strategy, direction, entry_price, lot_size,
                    stop_loss, take_profit_1, take_profit_2, take_profit_3,
                    tp1_lots, tp2_lots, tp3_lots,
                    tp1_hit, tp2_hit, tp3_hit, status,
                    open_time, close_time, pnl, close_reason,
                    broker_ticket, spread_at_entry,
                    snap_rsi_aligned, snap_trend_aligned,
                    snap_volume_sufficient, snap_near_news_event,
                    snap_market_condition, snap_session, snap_day_of_week
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    t.id, t.symbol, t.strategy, t.direction, t.entry_price,
                    t.lot_size, t.stop_loss, t.take_profit_1, t.take_profit_2,
                    t.take_profit_3, t.tp1_lots, t.tp2_lots, t.tp3_lots,
                    int(t.tp1_hit), int(t.tp2_hit), int(t.tp3_hit), t.status,
                    t.open_time.isoformat(), t.close_time.isoformat() if t.close_time else None,
                    t.pnl, t.close_reason, t.broker_ticket, t.spread_at_entry,
                    int(t.snap_rsi_aligned), int(t.snap_trend_aligned),
                    int(t.snap_volume_sufficient), int(t.snap_near_news_event),
                    t.snap_market_condition, t.snap_session, t.snap_day_of_week,
                ),
            )

    def get_open_trades(self) -> list[Trade]:
        cur = self.conn.execute(
            "SELECT * FROM bot_trades WHERE status IN ('OPEN','PARTIAL')"
        )
        return [self._row_to_trade(r) for r in cur.fetchall()]

    def get_all_trades(self) -> list[Trade]:
        cur = self.conn.execute("SELECT * FROM bot_trades")
        return [self._row_to_trade(r) for r in cur.fetchall()]

    def get_trade(self, trade_id: str) -> Trade | None:
        cur = self.conn.execute("SELECT * FROM bot_trades WHERE id = ?", (trade_id,))
        row = cur.fetchone()
        return self._row_to_trade(row) if row else None

    @staticmethod
    def _row_to_trade(row: sqlite3.Row) -> Trade:
        return Trade(
            id=row["id"],
            symbol=row["symbol"],
            strategy=row["strategy"],
            direction=row["direction"],
            entry_price=row["entry_price"],
            lot_size=row["lot_size"],
            stop_loss=row["stop_loss"],
            take_profit_1=row["take_profit_1"],
            take_profit_2=row["take_profit_2"],
            take_profit_3=row["take_profit_3"],
            tp1_lots=row["tp1_lots"],
            tp2_lots=row["tp2_lots"],
            tp3_lots=row["tp3_lots"],
            tp1_hit=bool(row["tp1_hit"]),
            tp2_hit=bool(row["tp2_hit"]),
            tp3_hit=bool(row["tp3_hit"]),
            status=row["status"],
            open_time=datetime.fromisoformat(row["open_time"]),
            close_time=datetime.fromisoformat(row["close_time"]) if row["close_time"] else None,
            pnl=row["pnl"],
            close_reason=row["close_reason"] or "",
            broker_ticket=row["broker_ticket"],
            spread_at_entry=row["spread_at_entry"],
            snap_rsi_aligned=bool(row["snap_rsi_aligned"]),
            snap_trend_aligned=bool(row["snap_trend_aligned"]),
            snap_volume_sufficient=bool(row["snap_volume_sufficient"]),
            snap_near_news_event=bool(row["snap_near_news_event"]),
            snap_market_condition=row["snap_market_condition"] or "",
            snap_session=row["snap_session"] or "",
            snap_day_of_week=row["snap_day_of_week"] or "",
        )

    # ── trade scores ─────────────────────────────────────────────────────

    def insert_score(self, trade_id: str, strategy: str, symbol: str,
                     session: str, market_condition: str, spread_at_entry: float,
                     day_of_week: str, score: int, pnl: float,
                     rsi_aligned: bool, trend_aligned: bool,
                     volume_sufficient: bool, near_news_event: bool,
                     filters_aligned: bool) -> None:
        with self.conn:
            self.conn.execute(
                """INSERT INTO trade_scores
                   (trade_id, strategy, symbol, session, market_condition,
                    spread_at_entry, day_of_week, score, pnl,
                    rsi_aligned, trend_aligned, volume_sufficient,
                    near_news_event, filters_aligned)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (trade_id, strategy, symbol, session, market_condition,
                 spread_at_entry, day_of_week, score, pnl,
                 int(rsi_aligned), int(trend_aligned),
                 int(volume_sufficient), int(near_news_event),
                 int(filters_aligned)),
            )

    # ── strategy confidence ──────────────────────────────────────────────

    def get_confidence(self, strategy: str) -> float:
        cur = self.conn.execute(
            "SELECT confidence FROM strategy_confidence WHERE strategy = ?",
            (strategy,),
        )
        row = cur.fetchone()
        return float(row["confidence"]) if row else settings.DEFAULT_CONFIDENCE

    def upsert_confidence(self, strategy: str, confidence: float,
                          total_trades: int, total_score: int) -> None:
        with self.conn:
            self.conn.execute(
                """INSERT OR REPLACE INTO strategy_confidence
                   (strategy, confidence, total_trades, total_score, last_updated)
                   VALUES (?, ?, ?, ?, datetime('now'))""",
                (strategy, confidence, total_trades, total_score),
            )

    # ── event log ────────────────────────────────────────────────────────

    def log_event(self, level: str, source: str, message: str,
                  data: str | None = None) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO events (level, source, message, data) VALUES (?,?,?,?)",
                (level, source, message, data),
            )

    # ── queries for daily stats ──────────────────────────────────────────

    def get_trades_closed_today(self) -> list[Trade]:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        cur = self.conn.execute(
            "SELECT * FROM bot_trades WHERE status='CLOSED' AND close_time LIKE ?",
            (f"{today}%",),
        )
        return [self._row_to_trade(r) for r in cur.fetchall()]

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)
