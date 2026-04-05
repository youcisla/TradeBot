-- migrations/001_trade_commits.sql
-- Immutable audit ledger for every execution decision.
-- Apply with:  psql $DATABASE_URL -f migrations/001_trade_commits.sql

CREATE TABLE IF NOT EXISTS trade_commits (
    hash            CHAR(8)         PRIMARY KEY,        -- first 8 chars of SHA-256(ts+symbol+direction)
    ts              TIMESTAMPTZ     NOT NULL DEFAULT NOW(),
    symbol          VARCHAR(20)     NOT NULL,
    direction       VARCHAR(10)     NOT NULL,           -- 'BUY' | 'SELL'
    lots            DECIMAL(10,5),
    entry_price     DECIMAL(20,8),
    stop_loss       DECIMAL(20,8),
    take_profit     DECIMAL(20,8),
    strategy        VARCHAR(60),
    reason          TEXT,                               -- guard block reason or 'executed'
    guards          JSONB,                              -- guard pipeline result snapshot
    broker_resp     JSONB,                              -- raw broker response
    parent_hash     CHAR(8)         REFERENCES trade_commits(hash) ON DELETE SET NULL,
    -- Outcome fields — populated when trade closes
    closed_at       TIMESTAMPTZ,
    exit_price      DECIMAL(20,8),
    pnl_usd         NUMERIC(12,4),
    rr_achieved     NUMERIC(8,4)
);

-- Fast lookups by time and by symbol+time
CREATE INDEX IF NOT EXISTS idx_trade_commits_ts
    ON trade_commits (ts DESC);

CREATE INDEX IF NOT EXISTS idx_trade_commits_symbol_ts
    ON trade_commits (symbol, ts DESC);

-- Allow efficient querying of unresolved commits
CREATE INDEX IF NOT EXISTS idx_trade_commits_open
    ON trade_commits (ts DESC)
    WHERE closed_at IS NULL;

COMMENT ON TABLE trade_commits IS
    'Immutable audit ledger: one row per execution decision (blocked OR executed).';
COMMENT ON COLUMN trade_commits.hash IS
    'SHA-256(ts::text || symbol || direction)[:8] — deterministic dedup key.';
COMMENT ON COLUMN trade_commits.guards IS
    'Snapshot of GuardPipeline.check() result at time of decision.';
COMMENT ON COLUMN trade_commits.parent_hash IS
    'Links scale-in or partial-close commits back to the originating commit.';
