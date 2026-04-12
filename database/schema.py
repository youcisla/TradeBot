"""Schema DDL — extracted from database/db.py."""

from __future__ import annotations

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

_ALTER_BOT_STATUS_INTELLIGENCE = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='bot_status' AND column_name='spread_condition') THEN
        ALTER TABLE bot_status ADD COLUMN spread_condition TEXT DEFAULT 'unknown';
        ALTER TABLE bot_status ADD COLUMN current_session TEXT DEFAULT 'unknown';
        ALTER TABLE bot_status ADD COLUMN market_regime TEXT DEFAULT 'unknown';
        ALTER TABLE bot_status ADD COLUMN spread_pips REAL DEFAULT 0;
        ALTER TABLE bot_status ADD COLUMN vix REAL DEFAULT 0;
        ALTER TABLE bot_status ADD COLUMN daily_loss_pct REAL DEFAULT 0;
        ALTER TABLE bot_status ADD COLUMN equity_drawdown_pct REAL DEFAULT 0;
    END IF;
END $$;
"""

_ALTER_BOT_STATUS_GUARD_STATUS = """
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name='bot_status' AND column_name='guard_status') THEN
        ALTER TABLE bot_status ADD COLUMN guard_status JSONB DEFAULT '[]';
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

# Alias for the migrations that run after table creation
_SCHEMA_MIGRATIONS = [
    _ALTER_BOT_STATUS_BROKER,
    _ALTER_BOT_STATUS_INTELLIGENCE,
    _ALTER_BOT_STATUS_GUARD_STATUS,
    _ALTER_TRADES_COMMISSION,
    _ALTER_TRADES_TP4,
    _ALTER_TRADES_EXPECTANCY,
    _ALTER_TRADES_LIVE,
    _ALTER_STRATEGY_CONFIDENCE_STREAK,
    _ALTER_BOT_COMMANDS_RUNNING,
]
