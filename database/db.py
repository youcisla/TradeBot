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
    swap                NUMERIC DEFAULT 0.0,
    expected_edge_pct   NUMERIC DEFAULT 0.0,
    expected_pnl        NUMERIC DEFAULT 0.0,
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

_ALTER_BOT_COMMANDS_RUNNING = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='bot_commands' AND column_name='started_at') THEN
        ALTER TABLE bot_commands ADD COLUMN started_at TIMESTAMP;
    END IF;
END $$;
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

_ALTER_TRADES_LIVE = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trades' AND column_name='current_price') THEN
        ALTER TABLE trades ADD COLUMN current_price NUMERIC DEFAULT 0.0;
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

_ALTER_TRADES_TP4 = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trades' AND column_name='take_profit_4') THEN
        ALTER TABLE trades ADD COLUMN take_profit_4  NUMERIC DEFAULT 0.0;
        ALTER TABLE trades ADD COLUMN tp4_lots       NUMERIC DEFAULT 0.0;
        ALTER TABLE trades ADD COLUMN tp4_hit        BOOLEAN DEFAULT FALSE;
        ALTER TABLE trades ADD COLUMN structural_be  NUMERIC DEFAULT 0.0;
    END IF;
END $$;
"""

_ALTER_TRADES_EXPECTANCY = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trades' AND column_name='expected_edge_pct') THEN
        ALTER TABLE trades ADD COLUMN expected_edge_pct NUMERIC DEFAULT 0.0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='trades' AND column_name='expected_pnl') THEN
        ALTER TABLE trades ADD COLUMN expected_pnl NUMERIC DEFAULT 0.0;
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

_CREATE_SYMBOL_FAULT = """
CREATE TABLE IF NOT EXISTS symbol_fault (
    symbol        TEXT PRIMARY KEY,
    fail_count    INTEGER DEFAULT 0,
    disabled_until TIMESTAMP WITH TIME ZONE
);
"""

_CREATE_BOT_SESSIONS = """
CREATE TABLE IF NOT EXISTS bot_sessions (
    id          SERIAL PRIMARY KEY,
    started_at  TIMESTAMP DEFAULT NOW(),
    ended_at    TIMESTAMP,
    version     TEXT DEFAULT '',
    exit_reason TEXT DEFAULT 'normal'
);
"""

_CREATE_TRADE_THESES = """
CREATE TABLE IF NOT EXISTS trade_theses (
    id              SERIAL PRIMARY KEY,
    trade_id        TEXT REFERENCES trades(id) ON DELETE SET NULL,
    symbol          VARCHAR(20) NOT NULL,
    direction       VARCHAR(5),
    stage           VARCHAR(20) NOT NULL DEFAULT 'IDEA',
    entry_price     NUMERIC(10, 5),
    sl_price        NUMERIC(10, 5),
    tp_price        NUMERIC(10, 5),
    rr_ratio        NUMERIC(5, 2),
    bull_case       TEXT DEFAULT '',
    bear_case       TEXT DEFAULT '',
    entry_reason    TEXT DEFAULT '',
    actual_outcome  VARCHAR(20),
    mae_pips        NUMERIC(8, 1),
    mfe_pips        NUMERIC(8, 1),
    notes           TEXT DEFAULT '',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    closed_at       TIMESTAMPTZ
);
"""

_CREATE_TRADE_THESES_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_trade_theses_trade_id   ON trade_theses (trade_id);
CREATE INDEX IF NOT EXISTS idx_trade_theses_symbol     ON trade_theses (symbol);
CREATE INDEX IF NOT EXISTS idx_trade_theses_stage      ON trade_theses (stage);
CREATE INDEX IF NOT EXISTS idx_trade_theses_created    ON trade_theses (created_at DESC);
"""

_CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_agent_events_created_at        ON agent_events (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_events_agent             ON agent_events (agent);
CREATE INDEX IF NOT EXISTS idx_agent_events_agent_time        ON agent_events (agent, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_agent_events_agent_level_time  ON agent_events (agent, level, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trades_status                  ON trades (status);
CREATE INDEX IF NOT EXISTS idx_trades_open_time               ON trades (open_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_symbol                  ON trades (symbol);
CREATE INDEX IF NOT EXISTS idx_trades_close_time              ON trades (close_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_status_open_time        ON trades (status, open_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_open_partial            ON trades (open_time DESC) WHERE status IN ('OPEN', 'PARTIAL');
CREATE INDEX IF NOT EXISTS idx_ict_setups_created_at          ON ict_setups (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ict_setups_symbol              ON ict_setups (symbol);
CREATE INDEX IF NOT EXISTS idx_ict_setups_symbol_created      ON ict_setups (symbol, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_bot_commands_status            ON bot_commands (status);
CREATE INDEX IF NOT EXISTS idx_bot_commands_pending           ON bot_commands (created_at DESC) WHERE status = 'pending';
CREATE INDEX IF NOT EXISTS idx_bot_commands_pending_review    ON bot_commands (created_at DESC) WHERE status = 'pending_confirmation';
CREATE INDEX IF NOT EXISTS idx_bot_sessions_started           ON bot_sessions (started_at DESC);
CREATE INDEX IF NOT EXISTS idx_trade_scores_created_at        ON trade_scores (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trade_scores_strategy_time     ON trade_scores (strategy, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_created_at             ON signals (created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_intent                ON signals (signal_intent);
CREATE INDEX IF NOT EXISTS idx_signals_author                ON signals (author);
CREATE INDEX IF NOT EXISTS idx_signals_strategy              ON signals (strategy);
CREATE INDEX IF NOT EXISTS idx_agent_reputation_updated       ON agent_reputation (updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_subscriptions_leader           ON subscriptions (leader_id);
CREATE INDEX IF NOT EXISTS idx_subscriptions_follower         ON subscriptions (follower_id);
CREATE INDEX IF NOT EXISTS idx_macro_snapshots_fetched        ON macro_snapshots (fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_macro_snapshots_risk_tier      ON macro_snapshots (risk_tier);
"""

_CREATE_BOT_MEMORY = """
CREATE TABLE IF NOT EXISTS bot_memory (
    block_name   TEXT PRIMARY KEY,
    content      TEXT NOT NULL DEFAULT '',
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);
"""

_CREATE_SIGNALS = """
CREATE TABLE IF NOT EXISTS signals (
    id              SERIAL PRIMARY KEY,
    signal_intent  TEXT NOT NULL DEFAULT 'EXECUTION',
    signal_type     TEXT NOT NULL DEFAULT 'OPERATION',
    strategy        TEXT NOT NULL,
    symbol          TEXT NOT NULL DEFAULT '',
    direction       TEXT DEFAULT '',
    entry_price     NUMERIC DEFAULT 0,
    stop_loss       NUMERIC DEFAULT 0,
    take_profit_1   NUMERIC DEFAULT 0,
    confidence      NUMERIC DEFAULT 0.5,
    reason          TEXT DEFAULT '',
    bull_case       TEXT DEFAULT '',
    bear_case       TEXT DEFAULT '',
    author          TEXT NOT NULL DEFAULT 'bot',
    tags            TEXT[] DEFAULT '{}',
    points_awarded BOOLEAN DEFAULT FALSE,
    follower_score  INTEGER DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
"""

_CREATE_AGENT_REPUTATION = """
CREATE TABLE IF NOT EXISTS agent_reputation (
    agent            TEXT PRIMARY KEY,
    total_signals    INTEGER DEFAULT 0,
    adopted_signals  INTEGER DEFAULT 0,
    total_points     INTEGER DEFAULT 0,
    win_streak       INTEGER DEFAULT 0,
    last_score       NUMERIC DEFAULT 0,
    reputation_score NUMERIC DEFAULT 0.5,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW()
);
"""

_CREATE_SUBSCRIPTIONS = """
CREATE TABLE IF NOT EXISTS subscriptions (
    id              SERIAL PRIMARY KEY,
    follower_id     TEXT NOT NULL,
    leader_id       TEXT NOT NULL,
    leader_strategy TEXT NOT NULL DEFAULT 'all',
    status          TEXT DEFAULT 'ACTIVE',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
"""

_CREATE_MACRO_SNAPSHOTS = """
CREATE TABLE IF NOT EXISTS macro_snapshots (
    id              SERIAL PRIMARY KEY,
    snapshot_json   JSONB NOT NULL,
    risk_tier       TEXT DEFAULT 'normal',
    yield_inverted  BOOLEAN DEFAULT FALSE,
    usd_strength    TEXT DEFAULT 'neutral',
    gdelt_tone      NUMERIC,
    fetched_at      TIMESTAMPTZ DEFAULT NOW()
);
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
    _CREATE_SYMBOL_FAULT,
    _CREATE_BOT_SESSIONS,
    _CREATE_TRADE_THESES,
    _CREATE_BOT_MEMORY,
    _CREATE_SIGNALS,
    _CREATE_AGENT_REPUTATION,
    _CREATE_SUBSCRIPTIONS,
    _CREATE_MACRO_SNAPSHOTS,
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
        self._pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=20,
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
                    cur.execute(_ALTER_TRADES_TP4)
                    cur.execute(_ALTER_TRADES_EXPECTANCY)
                    cur.execute(_ALTER_TRADES_LIVE)
                    cur.execute(_ALTER_STRATEGY_CONFIDENCE_STREAK)
                    cur.execute(_ALTER_BOT_COMMANDS_RUNNING)
                    cur.execute(_CREATE_INDEXES)
                    cur.execute(_CREATE_TRADE_THESES_INDEXES)
            logger.info("Database tables verified")
        finally:
            self._put_conn(conn)
        self.purge_old_data()

    def purge_old_data(self) -> None:
        """Delete stale rows and expire pending approvals.

        Retention policy:
          - agent_events: 14 days  (~55k rows @ 4k/day)
          - bot_commands (done): 7 days
          - ict_setups: 30 days
          - pending_confirmation commands: expire (→ failed) after 1 hour
        """
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "DELETE FROM agent_events WHERE created_at < NOW() - INTERVAL '14 days'"
                    )
                    n_events = cur.rowcount
                    cur.execute(
                        "DELETE FROM bot_commands WHERE status='done' AND created_at < NOW() - INTERVAL '7 days'"
                    )
                    n_cmds = cur.rowcount
                    cur.execute(
                        "DELETE FROM ict_setups WHERE created_at < NOW() - INTERVAL '30 days'"
                    )
                    n_ict = cur.rowcount
                    cur.execute(
                        "DELETE FROM macro_snapshots WHERE fetched_at < NOW() - INTERVAL '7 days'"
                    )
                    n_macro = cur.rowcount
                    # Expire stale approval requests — prevents orphaned commands
                    # that were never reviewed from blocking the queue indefinitely.
                    cur.execute(
                        """
                        UPDATE bot_commands
                        SET status = 'failed',
                            result = 'Expired: approval not received within 1 hour',
                            executed_at = NOW()
                        WHERE status = 'pending_confirmation'
                          AND created_at < NOW() - INTERVAL '1 hour'
                        """
                    )
                    n_expired = cur.rowcount
            if n_events or n_cmds or n_ict or n_macro or n_expired:
                logger.info(
                    "DB purge: removed %d agent_events, %d bot_commands, %d ict_setups, "
                    "%d macro_snapshots; expired %d stale approval requests",
                    n_events, n_cmds, n_ict, n_macro, n_expired,
                )
        except Exception:
            logger.exception("DB purge failed (non-fatal)")
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
            self._put_conn(conn)

    def update_live_state(self, trade_id: str, pnl: float, current_price: float) -> None:
        """Lightweight update called every monitor cycle — only writes pnl + current_price."""
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE trades SET pnl=%s, current_price=%s WHERE id=%s",
                        (pnl, current_price, trade_id),
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
    def _ensure_utc(dt: datetime | None) -> datetime | None:
        """Return a UTC-aware datetime for values loaded from Postgres.

        The `trades` table currently stores `TIMESTAMP` (without timezone), so
        psycopg2 can return naive datetimes. Trade manager arithmetic uses
        UTC-aware datetimes, so normalize at the DB boundary.
        """
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)

    @staticmethod
    def _row_to_trade(row: dict) -> Trade:
        open_time = Database._ensure_utc(row["open_time"]) or datetime.now(UTC)
        close_time = Database._ensure_utc(row["close_time"])
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
                               total_trades=strategy_confidence.total_trades + EXCLUDED.total_trades,
                               total_score=strategy_confidence.total_score + EXCLUDED.total_score,
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
            self._put_conn(conn)

    def get_recent_strategy_regime_stats(
        self,
        lookback_hours: int = 48,
        min_trades: int = 3,
    ) -> list[dict]:
        """Return per-strategy/per-regime win-rate stats for recent closed trades."""
        conn = self._get_conn()
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
            self._put_conn(conn)

    def get_recent_context_outcomes(
        self,
        strategy: str,
        symbol: str,
        session: str,
        market_condition: str,
        lookback_days: int = 30,
        limit: int = 50,
    ) -> dict[str, float | int]:
        """Return recent outcomes for trades matching a similar execution context."""
        conn = self._get_conn()
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
                    "trades": int(trades or 0),
                    "avg_score": float(avg_score or 0.0),
                    "avg_pnl": float(avg_pnl or 0.0),
                    "win_rate": float(win_rate or 0.0),
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

    def reset_learning_state(self) -> dict[str, int]:
        """Delete historical learning state so confidence/scoring restarts fresh.

        This intentionally clears only learning artifacts and leaves trades,
        bot status, commands, and market/event telemetry untouched.
        """
        conn = self._get_conn()
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

            summary = {
                "trade_scores": removed_scores,
                "strategy_confidence": removed_confidence,
                "performance_snapshots": removed_snapshots,
            }
            self.log_agent_event(
                "learning_agent",
                "warning",
                "Learning state reset requested; historical scoring cleared",
                summary,
            )
            return summary
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

    def start_session(self, version: str = "") -> int:
        """Insert a new bot_sessions row and return its primary-key ID."""
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO bot_sessions (version) VALUES (%s) RETURNING id",
                        (version,),
                    )
                    row = cur.fetchone()
                    return int(row[0]) if row else 0
        except Exception:
            logger.exception("start_session failed (non-fatal)")
            return 0
        finally:
            self._put_conn(conn)

    def end_session(self, session_id: int, exit_reason: str = "normal") -> None:
        """Mark an open bot_sessions row as ended."""
        if not session_id:
            return
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE bot_sessions
                        SET ended_at = NOW(), exit_reason = %s
                        WHERE id = %s
                        """,
                        (exit_reason, session_id),
                    )
        except Exception:
            logger.exception("end_session failed (non-fatal)")
        finally:
            self._put_conn(conn)

    def claim_pending_commands(self, limit: int = 25) -> list[dict]:
        """Atomically claim pending commands for execution.

        Uses ``FOR UPDATE SKIP LOCKED`` so multiple bot workers can safely poll
        the same queue without executing the same command twice.
        """
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute(
                        """
                        WITH claimed AS (
                            SELECT id
                            FROM bot_commands
                            WHERE status = 'pending'
                            ORDER BY created_at ASC
                            FOR UPDATE SKIP LOCKED
                            LIMIT %s
                        )
                        UPDATE bot_commands bc
                        SET status = 'running',
                            result = CONCAT('Started ', bc.command),
                            started_at = NOW(),
                            executed_at = NULL
                        FROM claimed
                        WHERE bc.id = claimed.id
                        RETURNING bc.*
                        """,
                        (max(1, limit),),
                    )
                    return [dict(r) for r in cur.fetchall()]
        finally:
            self._put_conn(conn)

    def update_command(
        self,
        cmd_id: int,
        status: str,
        result: str | None = None,
        *,
        set_executed: bool = True,
    ) -> None:
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    if set_executed:
                        cur.execute(
                            """UPDATE bot_commands
                               SET status = %s, result = %s, executed_at = NOW()
                               WHERE id = %s""",
                            (status, result, cmd_id),
                        )
                    else:
                        cur.execute(
                            """UPDATE bot_commands
                               SET status = %s, result = %s, started_at = NOW(), executed_at = NULL
                               WHERE id = %s""",
                            (status, result, cmd_id),
                        )
        finally:
            self._put_conn(conn)

    def review_command(
        self,
        cmd_id: int,
        *,
        approved: bool,
        reviewer: str,
        reason: str,
    ) -> bool:
        """Approve or deny a command waiting for human confirmation."""
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT payload FROM bot_commands
                           WHERE id = %s AND status = 'pending_confirmation'""",
                        (cmd_id,),
                    )
                    row = cur.fetchone()
                    if row is None:
                        return False

                    payload = row[0] or {}
                    if not isinstance(payload, dict):
                        payload = {}

                    review_meta = payload.get("_review")
                    if not isinstance(review_meta, dict):
                        review_meta = {}

                    review_meta.update(
                        {
                            "reviewedBy": reviewer,
                            "reviewedAt": datetime.now(UTC).isoformat(),
                            "reason": reason,
                            "decision": "approved" if approved else "denied",
                        }
                    )
                    payload["_review"] = review_meta

                    next_status = "pending" if approved else "failed"
                    result = "Approved for execution" if approved else f"Denied: {reason}"

                    cur.execute(
                        """UPDATE bot_commands
                           SET status = %s,
                               result = %s,
                               payload = %s,
                               executed_at = CASE WHEN %s THEN NULL ELSE NOW() END
                           WHERE id = %s""",
                        (next_status, result, json.dumps(payload), approved, cmd_id),
                    )
                    return True
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

    # ── symbol fault persistence ─────────────────────────────────────────

    def load_symbol_faults(self) -> dict[str, dict]:
        """Return {symbol: {fail_count, disabled_until}} for all persisted faults."""
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT symbol, fail_count, disabled_until FROM symbol_fault")
                return {r["symbol"]: {"fail_count": r["fail_count"],
                                      "disabled_until": r["disabled_until"]}
                        for r in cur.fetchall()}
        finally:
            self._put_conn(conn)

    def save_symbol_fault(self, symbol: str, fail_count: int,
                          disabled_until: "datetime | None") -> None:
        """Upsert fault state for one symbol. Pass fail_count=0 to clear."""
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    if fail_count == 0 and disabled_until is None:
                        cur.execute("DELETE FROM symbol_fault WHERE symbol = %s", (symbol,))
                    else:
                        cur.execute(
                            """INSERT INTO symbol_fault (symbol, fail_count, disabled_until)
                               VALUES (%s, %s, %s)
                               ON CONFLICT (symbol) DO UPDATE SET
                                   fail_count = EXCLUDED.fail_count,
                                   disabled_until = EXCLUDED.disabled_until""",
                            (symbol, fail_count, disabled_until),
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

    def count_closed_trades(self) -> int:
        """Return total number of closed trades with non-null, non-zero pnl."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM trades "
                    "WHERE status='CLOSED' AND pnl IS NOT NULL AND pnl != 0"
                )
                row = cur.fetchone()
                return int(row[0]) if row else 0
        finally:
            self._put_conn(conn)

    def get_closed_trades_since(self, since: "datetime", limit: int = 500) -> list[Trade]:
        """Return closed trades with close_time >= since ordered by close_time asc."""
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM trades
                       WHERE status='CLOSED' AND close_time >= %s
                       ORDER BY close_time ASC
                       LIMIT %s""",
                    (since, max(1, int(limit))),
                )
                return [self._row_to_trade(r) for r in cur.fetchall()]
        finally:
            self._put_conn(conn)

    # ── persistent agent memory (bot_memory table) ───────────────────────

    def write_memory_block(self, block_name: str, content: str) -> None:
        """Upsert a named memory block (INSERT … ON CONFLICT UPDATE)."""
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO bot_memory (block_name, content, updated_at)
                           VALUES (%s, %s, NOW())
                           ON CONFLICT (block_name)
                           DO UPDATE SET content = EXCLUDED.content,
                                         updated_at = NOW()""",
                        (block_name, content),
                    )
        finally:
            self._put_conn(conn)

    def read_memory_block(self, block_name: str) -> str | None:
        """Return the stored content for a memory block, or None."""
        conn = self._get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT content FROM bot_memory WHERE block_name = %s",
                    (block_name,),
                )
                row = cur.fetchone()
                return row[0] if row else None
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

    # ── trade thesis ────────────────────────────────────────────────────

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
        """Insert a new trade thesis row.  Returns the new row id."""
        conn = self._get_conn()
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
            self._put_conn(conn)

    def get_trade_thesis(self, trade_id: str) -> dict | None:
        """Return the most recent thesis for *trade_id*, or None."""
        conn = self._get_conn()
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
            self._put_conn(conn)

    def update_trade_outcome(
        self,
        trade_id: str,
        *,
        actual_outcome: str,
        mae_pips: float | None = None,
        mfe_pips: float | None = None,
        notes: str = "",
    ) -> None:
        """Mark the thesis for *trade_id* as closed with outcome + MAE/MFE."""
        conn = self._get_conn()
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

    # ── signals ────────────────────────────────────────────────────────────

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
        """Insert a new signal. Returns the new row id."""
        conn = self._get_conn()
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
            self._put_conn(conn)

    def get_signals(
        self,
        signal_intent: str | None = None,
        signal_type: str | None = None,
        strategy: str | None = None,
        author: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Fetch signals with optional filters (mirrors AI-Trader's signal feed)."""
        conn = self._get_conn()
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
            self._put_conn(conn)

    def mark_signal_points_awarded(self, signal_id: int) -> None:
        """Mark a signal as having had its points awarded (idempotent)."""
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE signals SET points_awarded = TRUE WHERE id = %s",
                        (signal_id,),
                    )
        finally:
            self._put_conn(conn)

    # ── agent reputation ─────────────────────────────────────────────────

    def get_agent_reputation(self, agent: str) -> dict:
        """Return reputation record for an agent, creating one if it doesn't exist."""
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """SELECT * FROM agent_reputation WHERE agent = %s""",
                    (agent,),
                )
                row = cur.fetchone()
                if row:
                    return dict(row)
                # Create default record on first access
                cur.execute(
                    """INSERT INTO agent_reputation (agent)
                       VALUES (%s)
                       ON CONFLICT (agent) DO NOTHING""",
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
            self._put_conn(conn)

    def bump_agent_reputation(
        self,
        agent: str,
        *,
        adopted: bool = False,
        points_delta: int = 0,
        score_delta: int = 0,
    ) -> None:
        """Update agent reputation after a signal is published or adopted.

        Mirrors AI-Trader's +10 for signal, +1 per follower adoption.
        For your bot, 'adopted' means the council/risk pipeline accepted the signal.
        """
        conn = self._get_conn()
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
            self._put_conn(conn)

    def get_leaderboard(self, limit: int = 10) -> list[dict]:
        """Top agents by total_points for the dashboard."""
        conn = self._get_conn()
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
            self._put_conn(conn)

    # ── subscriptions (copy-trading) ──────────────────────────────────────

    def save_subscription(
        self,
        follower_id: str,
        leader_id: str,
        leader_strategy: str = "all",
    ) -> int:
        """Follow a leader (mirrors AI-Trader copy-trade)."""
        conn = self._get_conn()
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
            self._put_conn(conn)

    def get_subscriptions(self, follower_id: str | None = None,
                          leader_id: str | None = None) -> list[dict]:
        """Return subscriptions filtered by follower and/or leader."""
        conn = self._get_conn()
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
            self._put_conn(conn)

    def delete_subscription(self, follower_id: str, leader_id: str) -> bool:
        """Unfollow a leader. Returns True if a row was deleted."""
        conn = self._get_conn()
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
            self._put_conn(conn)

    def get_followers(self, leader_id: str) -> list[dict]:
        """Return all active followers of a leader (for copy-trade propagation)."""
        conn = self._get_conn()
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
            self._put_conn(conn)

    # ── macro snapshots (snapshot+store pattern) ──────────────────────────

    def save_macro_snapshot(self, snapshot_data: dict) -> None:
        """Persist a macro snapshot dict (mirrors AI-Trader's snapshot tables).

        Stores the full MacroSnapshot as JSONB alongside indexed scalar
        columns so the dashboard can query by risk_tier / timestamp cheaply.
        """
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """INSERT INTO macro_snapshots
                           (snapshot_json, risk_tier, yield_inverted, usd_strength, gdelt_tone, fetched_at)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (
                            json.dumps(snapshot_data),
                            snapshot_data.get("risk_tier", "normal"),
                            snapshot_data.get("yield_curve_inverted", False),
                            snapshot_data.get("usd_strength", "neutral"),
                            snapshot_data.get("gdelt_risk_tone"),
                            datetime.now(UTC),
                        ),
                    )
        finally:
            self._put_conn(conn)

    def get_macro_snapshots(self, lookback_hours: int = 24,
                            risk_tier: str | None = None,
                            limit: int = 100) -> list[dict]:
        """Retrieve macro snapshots from the store for dashboard display."""
        conn = self._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                conditions = [
                    "fetched_at >= NOW() - (%s || ' hours')::interval"
                ]
                params: list = [str(max(1, lookback_hours))]
                if risk_tier:
                    conditions.append("risk_tier = %s")
                    params.append(risk_tier)
                params.append(max(1, limit))
                cur.execute(
                    f"""SELECT id, snapshot_json, risk_tier, yield_inverted,
                              usd_strength, gdelt_tone, fetched_at
                       FROM macro_snapshots
                       WHERE {' AND '.join(conditions)}
                       ORDER BY fetched_at DESC
                       LIMIT %s""",
                    params,
                )
                return [dict(r) for r in cur.fetchall()]
        finally:
            self._put_conn(conn)

    def prune_macro_snapshots(self, keep_hours: int = 168) -> int:
        """Delete macro snapshots older than *keep_hours* (default = 7 days)."""
        conn = self._get_conn()
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """DELETE FROM macro_snapshots
                           WHERE fetched_at < NOW() - (%s || ' hours')::interval""",
                        (str(max(1, keep_hours)),),
                    )
                    return cur.rowcount
        finally:
            self._put_conn(conn)
