"""PostgreSQL database handler for the trading bot.

Uses psycopg2 with a connection pool.  Connects to Vercel Postgres via
the DATABASE_URL environment variable.

Tables
------
- trades              – open & closed trade state (crash recovery)
- trade_scores        – learning system scoring per closed trade
- strategy_confidence – per-strategy confidence values
- agent_events        – persona-style event log per agent
- bot_commands        – command queue written by UI, read by bot
- bot_status          – single-row heartbeat
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

import psycopg2
import psycopg2.extras
import psycopg2.pool

from utils.crypto import encrypt, decrypt

from config import settings
from models.trade import Trade

logger = logging.getLogger(__name__)

# ── Schema DDL ───────────────────────────────────────────────────────────

_CREATE_TRADES = """
CREATE TABLE IF NOT EXISTS trades (
    id                  TEXT PRIMARY KEY,
    symbol              TEXT NOT NULL,
    strategy            TEXT NOT NULL,
    direction           TEXT NOT NULL,
    entry_price         NUMERIC NOT NULL,
    lot_size            NUMERIC NOT NULL,
    stop_loss           NUMERIC NOT NULL,
    take_profit_1       NUMERIC NOT NULL,
    take_profit_2       NUMERIC NOT NULL,
    take_profit_3       NUMERIC NOT NULL,
    tp1_lots            NUMERIC NOT NULL,
    tp2_lots            NUMERIC NOT NULL,
    tp3_lots            NUMERIC NOT NULL,
    tp1_hit             BOOLEAN DEFAULT FALSE,
    tp2_hit             BOOLEAN DEFAULT FALSE,
    tp3_hit             BOOLEAN DEFAULT FALSE,
    status              TEXT DEFAULT 'OPEN',
    open_time           TIMESTAMP NOT NULL,
    close_time          TIMESTAMP,
    pnl                 NUMERIC DEFAULT 0.0,
    commission          NUMERIC DEFAULT 0.0,
    close_reason        TEXT DEFAULT '',
    broker_ticket       BIGINT DEFAULT 0,
    spread_at_entry     NUMERIC DEFAULT 0.0,
    snap_rsi_aligned        BOOLEAN DEFAULT FALSE,
    snap_trend_aligned      BOOLEAN DEFAULT FALSE,
    snap_volume_sufficient  BOOLEAN DEFAULT FALSE,
    snap_near_news_event    BOOLEAN DEFAULT FALSE,
    snap_market_condition   TEXT DEFAULT '',
    snap_session            TEXT DEFAULT '',
    snap_day_of_week        TEXT DEFAULT ''
);
"""

_CREATE_TRADE_SCORES = """
CREATE TABLE IF NOT EXISTS trade_scores (
    id                  SERIAL PRIMARY KEY,
    trade_id            TEXT NOT NULL,
    strategy            TEXT NOT NULL,
    symbol              TEXT NOT NULL,
    session             TEXT,
    market_condition    TEXT,
    spread_at_entry     NUMERIC,
    day_of_week         TEXT,
    score               INTEGER NOT NULL,
    pnl                 NUMERIC,
    rsi_aligned         BOOLEAN,
    trend_aligned       BOOLEAN,
    volume_sufficient   BOOLEAN,
    near_news_event     BOOLEAN,
    filters_aligned     BOOLEAN,
    created_at          TIMESTAMP DEFAULT NOW()
);
"""

_CREATE_STRATEGY_CONFIDENCE = """
CREATE TABLE IF NOT EXISTS strategy_confidence (
    strategy        TEXT PRIMARY KEY,
    confidence      NUMERIC NOT NULL DEFAULT 0.5,
    total_trades    INTEGER DEFAULT 0,
    total_score     INTEGER DEFAULT 0,
    last_updated    TIMESTAMP DEFAULT NOW()
);
"""

_CREATE_AGENT_EVENTS = """
CREATE TABLE IF NOT EXISTS agent_events (
    id          SERIAL PRIMARY KEY,
    agent       TEXT NOT NULL,
    level       TEXT NOT NULL,
    message     TEXT NOT NULL,
    data        JSONB,
    created_at  TIMESTAMP DEFAULT NOW()
);
"""

_CREATE_BOT_COMMANDS = """
CREATE TABLE IF NOT EXISTS bot_commands (
    id          SERIAL PRIMARY KEY,
    command     TEXT NOT NULL,
    payload     JSONB,
    status      TEXT DEFAULT 'pending',
    result      TEXT,
    created_at  TIMESTAMP DEFAULT NOW(),
    executed_at TIMESTAMP
);
"""

_CREATE_BOT_STATUS = """
CREATE TABLE IF NOT EXISTS bot_status (
    id           INTEGER PRIMARY KEY DEFAULT 1,
    state        TEXT DEFAULT 'stopped',
    last_tick    TIMESTAMP,
    equity       NUMERIC DEFAULT 0,
    open_trades  INTEGER DEFAULT 0,
    daily_pnl    NUMERIC DEFAULT 0,
    uptime_start TIMESTAMP
);
"""

_INIT_BOT_STATUS = """
INSERT INTO bot_status (id, state) VALUES (1, 'stopped')
ON CONFLICT (id) DO NOTHING;
"""

_CREATE_ICT_SETUPS = """
CREATE TABLE IF NOT EXISTS ict_setups (
    id                  SERIAL PRIMARY KEY,
    symbol              TEXT NOT NULL,
    direction           TEXT NOT NULL,
    model               TEXT NOT NULL,
    entry_price         NUMERIC,
    stop_loss           NUMERIC,
    take_profit_1       NUMERIC,
    take_profit_2       NUMERIC,
    take_profit_3       NUMERIC,
    confidence          NUMERIC DEFAULT 0,
    htf_bias            TEXT DEFAULT '',
    htf_regime          TEXT DEFAULT '',
    premium_discount    TEXT DEFAULT '',
    entry_zone          TEXT DEFAULT '',
    reason              TEXT DEFAULT '',
    confluences         JSONB DEFAULT '{}',
    missing             TEXT[] DEFAULT '{}',
    session             TEXT DEFAULT '',
    executed            BOOLEAN DEFAULT FALSE,
    trade_id            TEXT,
    created_at          TIMESTAMP DEFAULT NOW()
);
"""

_CREATE_BROKER_ACCOUNTS = """
CREATE TABLE IF NOT EXISTS broker_accounts (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER,
    name            TEXT NOT NULL,
    account_number  TEXT NOT NULL,
    password        TEXT NOT NULL,
    server          TEXT NOT NULL,
    is_demo         BOOLEAN DEFAULT TRUE,
    is_active       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT NOW(),
    last_connected  TIMESTAMP
);
"""

_CREATE_DASHBOARD_USERS = """
CREATE TABLE IF NOT EXISTS dashboard_users (
    id              SERIAL PRIMARY KEY,
    username        TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    created_at      TIMESTAMP DEFAULT NOW()
);
"""

_CREATE_PERFORMANCE_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS performance_snapshots (
    id          SERIAL PRIMARY KEY,
    period_type TEXT NOT NULL,
    period_key  TEXT NOT NULL,
    trades      INTEGER DEFAULT 0,
    wins        INTEGER DEFAULT 0,
    losses      INTEGER DEFAULT 0,
    total_pnl   NUMERIC DEFAULT 0,
    avg_score   NUMERIC DEFAULT 0,
    win_rate    NUMERIC DEFAULT 0,
    created_at  TIMESTAMP DEFAULT NOW(),
    UNIQUE(period_type, period_key)
);
"""

_ALTER_STRATEGY_CONFIDENCE_STREAK = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='strategy_confidence' AND column_name='win_streak') THEN
        ALTER TABLE strategy_confidence ADD COLUMN win_streak INTEGER DEFAULT 0;
        ALTER TABLE strategy_confidence ADD COLUMN last_score NUMERIC DEFAULT 0;
    END IF;
END $$;
"""

_ALTER_TRADES_COMMISSION = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trades' AND column_name='commission') THEN
        ALTER TABLE trades ADD COLUMN commission NUMERIC DEFAULT 0.0;
    END IF;
END $$;
"""

_ALTER_BOT_STATUS_BROKER = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='bot_status' AND column_name='broker_account') THEN
        ALTER TABLE bot_status ADD COLUMN broker_account TEXT DEFAULT '';
        ALTER TABLE bot_status ADD COLUMN broker_server TEXT DEFAULT '';
        ALTER TABLE bot_status ADD COLUMN broker_name TEXT DEFAULT '';
        ALTER TABLE bot_status ADD COLUMN balance NUMERIC DEFAULT 0;
        ALTER TABLE bot_status ADD COLUMN leverage INTEGER DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='broker_accounts' AND column_name='user_id') THEN
        ALTER TABLE broker_accounts ADD COLUMN user_id INTEGER;
    END IF;
END $$;
"""

_CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_agent_events_created_at   ON agent_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_events_agent         ON agent_events (agent);
CREATE INDEX IF NOT EXISTS idx_trades_status              ON trades (status);
CREATE INDEX IF NOT EXISTS idx_trades_open_time           ON trades (open_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_symbol              ON trades (symbol);
CREATE INDEX IF NOT EXISTS idx_trades_close_time          ON trades (close_time DESC);
CREATE INDEX IF NOT EXISTS idx_ict_setups_created_at      ON ict_setups (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ict_setups_symbol          ON ict_setups (symbol);
CREATE INDEX IF NOT EXISTS idx_bot_commands_status        ON bot_commands (status);
CREATE INDEX IF NOT EXISTS idx_trade_scores_created_at    ON trade_scores (created_at DESC);
"""

_ALL_TABLES = [
    _CREATE_TRADES,
    _CREATE_TRADE_SCORES,
    _CREATE_STRATEGY_CONFIDENCE,
    _CREATE_AGENT_EVENTS,
    _CREATE_BOT_COMMANDS,
    _CREATE_BOT_STATUS,
    _CREATE_ICT_SETUPS,
    _CREATE_BROKER_ACCOUNTS,
    _CREATE_DASHBOARD_USERS,
    _CREATE_PERFORMANCE_SNAPSHOTS,
]


class Database:
    """PostgreSQL wrapper with connection pooling and auto-reconnect."""

    def __init__(self, dsn: str | None = None) -> None:
        self._dsn = dsn or settings.DATABASE_URL
        self._pool: psycopg2.pool.SimpleConnectionPool | None = None
        self._connect()
        self._create_tables()

    # ── connection pool ──────────────────────────────────────────────────

    def _connect(self) -> None:
        if self._pool:
            try:
                self._pool.closeall()
            except Exception:
                pass
        self._pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=self._dsn,
            options="-c statement_timeout=15000",
        )
        logger.info("PostgreSQL connection pool created")

    def _get_conn(self) -> psycopg2.extensions.connection:
        """Get a connection from the pool, reconnecting if stale."""
        assert self._pool is not None
        conn = self._pool.getconn()
        # Validate the connection is alive
        try:
            conn.isolation_level  # triggers check
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        except (psycopg2.OperationalError, psycopg2.InterfaceError):
            logger.warning("Stale DB connection detected — reconnecting pool")
            try:
                self._pool.putconn(conn, close=True)
            except Exception:
                pass
            self._reconnect()
            conn = self._pool.getconn()  # type: ignore[union-attr]
        return conn

    def _put_conn(self, conn: psycopg2.extensions.connection) -> None:
        if self._pool:
            try:
                # If the connection is in a bad state, discard it
                if conn.closed or conn.status != psycopg2.extensions.STATUS_READY:
                    self._pool.putconn(conn, close=True)
                else:
                    self._pool.putconn(conn)
            except Exception:
                pass

    def _reconnect(self) -> None:
        """Tear down the pool and create a fresh one."""
        logger.info("Rebuilding DB connection pool…")
        try:
            if self._pool:
                self._pool.closeall()
        except Exception:
            pass
        self._pool = psycopg2.pool.SimpleConnectionPool(
            minconn=1,
            maxconn=5,
            dsn=self._dsn,
            options="-c statement_timeout=15000",
        )
        logger.info("DB connection pool rebuilt")

    def close(self) -> None:
        if self._pool:
            self._pool.closeall()
            self._pool = None

    # ── schema ───────────────────────────────────────────────────────────

    def _create_tables(self) -> None:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    for ddl in _ALL_TABLES:
                        cur.execute(ddl)
                    cur.execute(_INIT_BOT_STATUS)
                    cur.execute(_ALTER_BOT_STATUS_BROKER)
                    cur.execute(_ALTER_TRADES_COMMISSION)
                    cur.execute(_ALTER_STRATEGY_CONFIDENCE_STREAK)
                    cur.execute(_CREATE_INDEXES)
            logger.info("Database tables verified")
        finally:
            self._put_conn(conn)

    # ── trade persistence ────────────────────────────────────────────────

    def upsert_trade(self, t: Trade) -> None:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO trades (
                            id, symbol, strategy, direction, entry_price, lot_size,
                            stop_loss, take_profit_1, take_profit_2, take_profit_3,
                            tp1_lots, tp2_lots, tp3_lots,
                            tp1_hit, tp2_hit, tp3_hit, status,
                            open_time, close_time, pnl, commission, close_reason,
                            broker_ticket, spread_at_entry,
                            snap_rsi_aligned, snap_trend_aligned,
                            snap_volume_sufficient, snap_near_news_event,
                            snap_market_condition, snap_session, snap_day_of_week
                        ) VALUES (
                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s
                        )
                        ON CONFLICT (id) DO UPDATE SET
                            stop_loss=EXCLUDED.stop_loss,
                            tp1_hit=EXCLUDED.tp1_hit, tp2_hit=EXCLUDED.tp2_hit,
                            tp3_hit=EXCLUDED.tp3_hit, status=EXCLUDED.status,
                            close_time=EXCLUDED.close_time, pnl=EXCLUDED.pnl,
                            commission=EXCLUDED.commission,
                            close_reason=EXCLUDED.close_reason,
                            lot_size=EXCLUDED.lot_size,
                            spread_at_entry=EXCLUDED.spread_at_entry
                        """,
                        (
                            t.id, t.symbol, t.strategy, t.direction, t.entry_price,
                            t.lot_size, t.stop_loss, t.take_profit_1, t.take_profit_2,
                            t.take_profit_3, t.tp1_lots, t.tp2_lots, t.tp3_lots,
                            t.tp1_hit, t.tp2_hit, t.tp3_hit, t.status,
                            t.open_time, t.close_time,
                            t.pnl, t.commission, t.close_reason, t.broker_ticket, t.spread_at_entry,
                            t.snap_rsi_aligned, t.snap_trend_aligned,
                            t.snap_volume_sufficient, t.snap_near_news_event,
                            t.snap_market_condition, t.snap_session, t.snap_day_of_week,
                        ),
                    )
        finally:
            self._put_conn(conn)

    def get_open_trades(self) -> list[Trade]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM trades WHERE status IN ('OPEN','PARTIAL')")
                return [self._row_to_trade(r) for r in cur.fetchall()]
        finally:
            self._put_conn(conn)

    def get_all_trades(self) -> list[Trade]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM trades ORDER BY open_time DESC")
                return [self._row_to_trade(r) for r in cur.fetchall()]
        finally:
            self._put_conn(conn)

    def get_trade(self, trade_id: str) -> Trade | None:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT * FROM trades WHERE id = %s", (trade_id,))
                row = cur.fetchone()
                return self._row_to_trade(row) if row else None
        finally:
            self._put_conn(conn)

    @staticmethod
    def _row_to_trade(row: dict) -> Trade:
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
            tp1_lots=float(row["tp1_lots"]),
            tp2_lots=float(row["tp2_lots"]),
            tp3_lots=float(row["tp3_lots"]),
            tp1_hit=bool(row["tp1_hit"]),
            tp2_hit=bool(row["tp2_hit"]),
            tp3_hit=bool(row["tp3_hit"]),
            status=row["status"],
            open_time=row["open_time"],
            close_time=row["close_time"],
            pnl=float(row["pnl"] or 0),
            commission=float(row["commission"] or 0),
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

    # ── trade scores ─────────────────────────────────────────────────────

    def insert_score(self, trade_id: str, strategy: str, symbol: str,
                     session: str, market_condition: str, spread_at_entry: float,
                     day_of_week: str, score: int, pnl: float,
                     rsi_aligned: bool, trend_aligned: bool,
                     volume_sufficient: bool, near_news_event: bool,
                     filters_aligned: bool) -> None:
        conn = self._get_conn()
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
            self._put_conn(conn)

    # ── strategy confidence ──────────────────────────────────────────────

    def get_confidence(self, strategy: str) -> float:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT confidence FROM strategy_confidence WHERE strategy = %s",
                    (strategy,),
                )
                row = cur.fetchone()
                return float(row["confidence"]) if row else settings.DEFAULT_CONFIDENCE
        finally:
            self._put_conn(conn)

    def upsert_confidence(self, strategy: str, confidence: float,
                          total_trades: int, total_score: int) -> None:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO strategy_confidence
                           (strategy, confidence, total_trades, total_score, last_updated)
                           VALUES (%s, %s, %s, %s, NOW())
                           ON CONFLICT (strategy) DO UPDATE SET
                               confidence=EXCLUDED.confidence,
                               total_trades=EXCLUDED.total_trades,
                               total_score=EXCLUDED.total_score,
                               last_updated=NOW()""",
                        (strategy, confidence, total_trades, total_score),
                    )
        finally:
            self._put_conn(conn)

    def get_rolling_avg_score(self, strategy: str, n: int = 10) -> float | None:
        """Average score of the last N scored trades for this strategy."""
        conn = self._get_conn()
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
            self._put_conn(conn)

    def get_strategy_streak(self, strategy: str) -> int:
        """Current win streak for a strategy (0 if not tracked yet)."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT win_streak FROM strategy_confidence WHERE strategy = %s",
                    (strategy,),
                )
                row = cur.fetchone()
                return int(row[0]) if row and row[0] is not None else 0
        finally:
            self._put_conn(conn)

    def update_strategy_streak(self, strategy: str,
                                win_streak: int, last_score: float) -> None:
        conn = self._get_conn()
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
            self._put_conn(conn)

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
        conn = self._get_conn()
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
            self._put_conn(conn)

    def get_previous_snapshot(self, period_type: str,
                              before_key: str) -> dict | None:
        """Most recent completed snapshot of this period type before the given key."""
        conn = self._get_conn()
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
            self._put_conn(conn)

    def get_period_stats(self, since: "datetime", until: "datetime") -> dict:
        """Aggregate win/loss/PnL/score stats for trade_scores in [since, until)."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """SELECT COUNT(*),
                              COUNT(*) FILTER (WHERE pnl > 0),
                              COUNT(*) FILTER (WHERE pnl <= 0),
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
            self._put_conn(conn)

    def boost_all_strategy_confidence(self, boost: float) -> None:
        """Add *boost* to every strategy's confidence, capped at 1.0."""
        conn = self._get_conn()
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
            self._put_conn(conn)

    # ── agent events (persona log) ───────────────────────────────────────

    def log_agent_event(self, agent: str, level: str, message: str,
                        data: dict | None = None) -> None:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO agent_events (agent, level, message, data)
                           VALUES (%s, %s, %s, %s)""",
                        (agent, level, message,
                         json.dumps(data) if data else None),
                    )
        finally:
            self._put_conn(conn)

    # ── legacy event log (kept for LoggingAgent compat) ──────────────────

    def log_event(self, level: str, source: str, message: str,
                  data: str | None = None) -> None:
        self.log_agent_event(
            agent=source.lower(),
            level=level.lower(),
            message=message,
            data={"raw": data} if data else None,
        )

    # ── bot commands (command queue) ─────────────────────────────────────

    def get_pending_commands(self) -> list[dict]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM bot_commands
                       WHERE status = 'pending'
                       ORDER BY created_at ASC"""
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put_conn(conn)

    def update_command(self, cmd_id: int, status: str,
                       result: str | None = None) -> None:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE bot_commands
                           SET status = %s, result = %s, executed_at = NOW()
                           WHERE id = %s""",
                        (status, result, cmd_id),
                    )
        finally:
            self._put_conn(conn)

    # ── bot status heartbeat ─────────────────────────────────────────────

    def update_bot_status(self, state: str, equity: float,
                          open_trades: int, daily_pnl: float,
                          broker_account: str = "", broker_server: str = "",
                          broker_name: str = "", balance: float = 0.0,
                          leverage: int = 0) -> None:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """UPDATE bot_status SET
                               state = %s, last_tick = NOW(),
                               equity = %s, open_trades = %s, daily_pnl = %s,
                               broker_account = %s, broker_server = %s,
                               broker_name = %s, balance = %s, leverage = %s
                           WHERE id = 1""",
                        (state, equity, open_trades, daily_pnl,
                         broker_account, broker_server, broker_name,
                         balance, leverage),
                    )
        finally:
            self._put_conn(conn)

    def set_bot_uptime_start(self) -> None:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE bot_status SET uptime_start = NOW(), state = 'running' WHERE id = 1"
                    )
        finally:
            self._put_conn(conn)

    def set_bot_stopped(self) -> None:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE bot_status SET state = 'stopped', last_tick = NOW() WHERE id = 1"
                    )
        finally:
            self._put_conn(conn)

    # ── queries for daily stats ──────────────────────────────────────────

    def get_trades_closed_today(self) -> list[Trade]:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                today = datetime.now(UTC).strftime("%Y-%m-%d")
                cur.execute(
                    "SELECT * FROM trades WHERE status='CLOSED' AND close_time::date = %s",
                    (today,),
                )
                return [self._row_to_trade(r) for r in cur.fetchall()]
        finally:
            self._put_conn(conn)

    # ── ICT setup logging ────────────────────────────────────────────────

    def save_ict_setup(self, setup: dict) -> None:
        """Persist an ICT setup candidate for dashboard analytics."""
        conn = self._get_conn()
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
            self._put_conn(conn)

    # ── broker accounts ──────────────────────────────────────────────────

    def get_broker_accounts(self, user_id: int | None = None) -> list[dict]:
        """Return all broker accounts (password excluded)."""
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if user_id:
                    cur.execute(
                        """SELECT id, user_id, name, account_number, server,
                                  is_demo, is_active, created_at, last_connected
                           FROM broker_accounts WHERE user_id = %s
                           ORDER BY created_at DESC""",
                        (user_id,),
                    )
                else:
                    cur.execute(
                        """SELECT id, user_id, name, account_number, server,
                                  is_demo, is_active, created_at, last_connected
                           FROM broker_accounts ORDER BY created_at DESC"""
                    )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put_conn(conn)

    def get_active_broker_account(self) -> dict | None:
        """Return the active broker account (with decrypted password)."""
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM broker_accounts WHERE is_active = TRUE LIMIT 1"
                )
                row = cur.fetchone()
                if not row:
                    return None
                result = dict(row)
                result["password"] = decrypt(result["password"])
                return result
        finally:
            self._put_conn(conn)

    def add_broker_account(self, name: str, account_number: str,
                           password: str, server: str,
                           is_demo: bool = True,
                           user_id: int | None = None) -> int:
        """Insert a new broker account (password encrypted). Returns row id."""
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO broker_accounts
                           (user_id, name, account_number, password, server, is_demo)
                           VALUES (%s, %s, %s, %s, %s, %s)
                           RETURNING id""",
                        (user_id, name, account_number,
                         encrypt(password), server, is_demo),
                    )
                    return cur.fetchone()[0]
        finally:
            self._put_conn(conn)

    def update_broker_account(self, account_id: int, name: str,
                              account_number: str, password: str | None,
                              server: str, is_demo: bool) -> None:
        """Update an existing broker account. Encrypts password if provided."""
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    if password:
                        cur.execute(
                            """UPDATE broker_accounts SET
                                   name=%s, account_number=%s, password=%s,
                                   server=%s, is_demo=%s
                               WHERE id=%s""",
                            (name, account_number, encrypt(password),
                             server, is_demo, account_id),
                        )
                    else:
                        cur.execute(
                            """UPDATE broker_accounts SET
                                   name=%s, account_number=%s,
                                   server=%s, is_demo=%s
                               WHERE id=%s""",
                            (name, account_number, server, is_demo,
                             account_id),
                        )
        finally:
            self._put_conn(conn)

    def delete_broker_account(self, account_id: int) -> None:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM broker_accounts WHERE id = %s",
                                (account_id,))
        finally:
            self._put_conn(conn)

    def activate_broker_account(self, account_id: int) -> None:
        """Set one account as active, deactivating all others."""
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute("UPDATE broker_accounts SET is_active = FALSE")
                    cur.execute(
                        "UPDATE broker_accounts SET is_active = TRUE WHERE id = %s",
                        (account_id,),
                    )
        finally:
            self._put_conn(conn)

    def mark_broker_connected(self, account_id: int) -> None:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE broker_accounts SET last_connected = NOW() WHERE id = %s",
                        (account_id,),
                    )
        finally:
            self._put_conn(conn)

    # ── dashboard users ──────────────────────────────────────────────────

    def get_user_by_username(self, username: str) -> dict | None:
        """Return a user row (id, username, password_hash) or None."""
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT * FROM dashboard_users WHERE username = %s",
                    (username,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            self._put_conn(conn)

    def get_user_by_id(self, user_id: int) -> dict | None:
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, username, created_at FROM dashboard_users WHERE id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                return dict(row) if row else None
        finally:
            self._put_conn(conn)

    def create_user(self, username: str, password_hash: str) -> int:
        """Insert a new dashboard user. Returns the new row id."""
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO dashboard_users (username, password_hash)
                           VALUES (%s, %s) RETURNING id""",
                        (username, password_hash),
                    )
                    return cur.fetchone()[0]
        finally:
            self._put_conn(conn)

    def update_user_password(self, user_id: int, password_hash: str) -> None:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE dashboard_users SET password_hash = %s WHERE id = %s",
                        (password_hash, user_id),
                    )
        finally:
            self._put_conn(conn)

    def get_all_users(self) -> list[dict]:
        """Return all users (id, username, created_at — no password hash)."""
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, username, created_at FROM dashboard_users ORDER BY created_at"
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put_conn(conn)

    def user_count(self) -> int:
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM dashboard_users")
                return cur.fetchone()[0]
        finally:
            self._put_conn(conn)
