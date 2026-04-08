import { Pool, PoolClient } from "pg";

// ── Singleton pool (survives Next.js HMR in dev) ───────────────────────
const globalForPg = globalThis as unknown as { __pgPool?: Pool };

function getPool(): Pool {
  if (!globalForPg.__pgPool) {
    const connStr = (process.env.DATABASE_URL || "").replace(
      /[?&]sslmode=[^&]*/g,
      ""
    );
    globalForPg.__pgPool = new Pool({
      connectionString: connStr,
      ssl: process.env.NODE_ENV === "production" ? true : { rejectUnauthorized: false },
      max: 10,
      idleTimeoutMillis: 15_000,
      connectionTimeoutMillis: 10_000,
    });
    // Prevent unhandled errors from crashing the process
    globalForPg.__pgPool.on("error", (err) => {
      console.error("[pg-pool] idle client error:", err.message);
    });
  }
  return globalForPg.__pgPool;
}

async function query(text: string, params?: unknown[]) {
  let client: PoolClient | undefined;
  try {
    client = await getPool().connect();
    const { rows } = await client.query(text, params);
    return rows;
  } catch (err) {
    // If the connection was severed, destroy it so the pool replaces it
    if (client) {
      (client as unknown as { release: (destroy?: boolean) => void }).release(true);
      client = undefined;
    }
    throw err;
  } finally {
    client?.release();
  }
}

// ── Types ──────────────────────────────────────────────────────────────
export interface BotStatus {
  state: string;
  last_tick: string | null;
  equity: number;
  open_trades: number;
  daily_pnl: number;
  uptime_start: string | null;
  broker_account: string;
  broker_server: string;
  broker_name: string;
  balance: number;
  leverage: number;
}

export interface AgentEvent {
  id: number;
  agent: string;
  level: string;
  message: string;
  data: Record<string, unknown> | null;
  created_at: string;
}

export interface ToolCycleEvent extends AgentEvent {
  data: {
    loop?: number;
    failed_tools?: string[];
    executed_tools?: string[];
    emergency_mode?: boolean;
    doctor_warning_count?: number;
  } | null;
}

export interface Trade {
  id: string;
  symbol: string;
  strategy: string;
  direction: string;
  entry_price: number;
  lot_size: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  take_profit_3: number;
  tp1_hit: boolean;
  tp2_hit: boolean;
  tp3_hit: boolean;
  status: string;
  open_time: string;
  close_time: string | null;
  pnl: number;
  current_price: number;
  broker_ticket: number;
  close_reason: string;
}

export interface StrategyConfidence {
  strategy: string;
  confidence: number;
  total_trades: number;
  total_score: number;
  last_updated: string;
}

export interface TradeScore {
  id: number;
  trade_id: string;
  strategy: string;
  symbol: string;
  session: string;
  market_condition: string;
  score: number;
  pnl: number;
  created_at: string;
}

export interface BrokerAccount {
  id: number;
  user_id: number | null;
  name: string;
  account_number: string;
  server: string;
  is_demo: boolean;
  is_active: boolean;
  created_at: string;
  last_connected: string | null;
}

export interface DashboardUser {
  id: number;
  username: string;
  password_hash?: string;
  created_at: string;
}

export interface PendingReviewCommand {
  id: number;
  command: string;
  payload: Record<string, unknown> | null;
  status: string;
  created_at: string;
}

// ── Queries ────────────────────────────────────────────────────────────

export async function getBotStatus(): Promise<BotStatus | null> {
  const rows = await query("SELECT * FROM bot_status WHERE id = 1");
  return (rows[0] as BotStatus) ?? null;
}

export async function getAgentEvents(limit = 80): Promise<AgentEvent[]> {
  const rows = await query(
    "SELECT * FROM agent_events ORDER BY created_at DESC LIMIT $1",
    [limit]
  );
  return rows as AgentEvent[];
}

export async function getToolCycleEvents(limit = 50): Promise<ToolCycleEvent[]> {
  const rows = await query(
    `SELECT * FROM agent_events
     WHERE agent = 'tool_system'
       AND message = 'Autonomous tool cycle completed'
     ORDER BY created_at DESC
     LIMIT $1`,
    [limit]
  );
  return rows as ToolCycleEvent[];
}

export async function getToolSystemEvents(limit = 200): Promise<AgentEvent[]> {
  const rows = await query(
    `SELECT * FROM agent_events
     WHERE agent = 'tool_system'
     ORDER BY created_at DESC
     LIMIT $1`,
    [limit]
  );
  return rows as AgentEvent[];
}

export async function getOpenTrades(): Promise<Trade[]> {
  const rows = await query(
    "SELECT * FROM trades WHERE status IN ('OPEN','PARTIAL') ORDER BY open_time DESC"
  );
  return rows as Trade[];
}

export async function getAllTrades(limit = 500, cursor?: string): Promise<Trade[]> {
  if (cursor) {
    const rows = await query(
      "SELECT * FROM trades WHERE open_time < $1 ORDER BY open_time DESC LIMIT $2",
      [cursor, limit]
    );
    return rows as Trade[];
  }
  const rows = await query(
    "SELECT * FROM trades ORDER BY open_time DESC LIMIT $1",
    [limit]
  );
  return rows as Trade[];
}

export async function getStrategyConfidences(): Promise<StrategyConfidence[]> {
  const rows = await query("SELECT * FROM strategy_confidence ORDER BY strategy");
  return rows as StrategyConfidence[];
}

export async function getTradeScores(limit = 100): Promise<TradeScore[]> {
  const rows = await query(
    "SELECT * FROM trade_scores ORDER BY created_at DESC LIMIT $1",
    [limit]
  );
  return rows as TradeScore[];
}

export async function insertCommand(
  command: string,
  payload?: Record<string, unknown>,
  status = "pending"
): Promise<void> {
  await query(
    "INSERT INTO bot_commands (command, payload, status) VALUES ($1, $2, $3)",
    [command, payload ? JSON.stringify(payload) : null, status]
  );
}

export async function reviewCommand(
  id: number,
  decision: "approve" | "deny",
  reviewedBy: string,
  reason: string
): Promise<number> {
  const nextStatus = decision === "approve" ? "pending" : "failed";
  const result =
    decision === "approve" ? "Approved for execution" : `Denied: ${reason}`;

  const rows = await query(
    `
      UPDATE bot_commands
      SET status = $1,
          result = $2,
          payload = COALESCE(payload, '{}'::jsonb) || jsonb_build_object(
            '_review',
            jsonb_build_object(
              'reviewedBy', $3,
              'reviewedAt', NOW(),
              'decision', $4,
              'reason', $5
            )
          ),
          executed_at = CASE WHEN $1 = 'failed' THEN NOW() ELSE NULL END
      WHERE id = $6 AND status = 'pending_confirmation'
      RETURNING id
    `,
    [nextStatus, result, reviewedBy, decision, reason, id]
  );

  return rows.length;
}

export interface CommandHistoryItem {
  id: number;
  command: string;
  status: string;
  result: string | null;
  created_at: string;
  executed_at: string | null;
  review: {
    reviewedBy: string;
    reviewedAt: string;
    decision: string;
    reason: string;
  } | null;
}

export async function getCommandHistory(limit = 20): Promise<CommandHistoryItem[]> {
  const rows = await query(
    `SELECT id, command, status, result, created_at, executed_at,
            payload -> '_review' AS review
     FROM bot_commands
     WHERE status IN ('done', 'failed')
       AND created_at > NOW() - INTERVAL '24 hours'
     ORDER BY COALESCE(executed_at, created_at) DESC
     LIMIT $1`,
    [limit]
  );
  return rows as CommandHistoryItem[];
}

export async function getPendingReviewCommands(
  limit = 25
): Promise<PendingReviewCommand[]> {
  const rows = await query(
    `
      SELECT id, command, payload, status, created_at
      FROM bot_commands
      WHERE status = 'pending_confirmation'
      ORDER BY created_at ASC
      LIMIT $1
    `,
    [limit]
  );

  return rows as PendingReviewCommand[];
}

export interface CommandAuditSummary {
  windowHours: number;
  total: number;
  pending: number;
  running: number;
  pendingConfirmation: number;
  done: number;
  failed: number;
  highRiskPendingReview: number;
  mediumRiskPendingReview: number;
  lowRiskPendingReview: number;
  avgRuntimeMs: number;
}

export async function getCommandAuditSummary(hours = 24): Promise<CommandAuditSummary> {
  const windowHours = Math.min(Math.max(hours, 1), 168);
  const rows = await query(
    `WITH recent AS (
       SELECT
         status,
         COALESCE(payload -> '_meta' ->> 'riskLevel', 'unknown') AS risk_level,
         CASE
           WHEN started_at IS NOT NULL AND executed_at IS NOT NULL THEN
             EXTRACT(EPOCH FROM (executed_at - started_at)) * 1000
           ELSE NULL
         END AS runtime_ms
       FROM bot_commands
       WHERE created_at > NOW() - ($1 || ' hours')::interval
     )
     SELECT
       COUNT(*)::int AS total,
       COUNT(*) FILTER (WHERE status = 'pending')::int AS pending,
       COUNT(*) FILTER (WHERE status = 'running')::int AS running,
       COUNT(*) FILTER (WHERE status = 'pending_confirmation')::int AS pending_confirmation,
       COUNT(*) FILTER (WHERE status = 'done')::int AS done,
       COUNT(*) FILTER (WHERE status = 'failed')::int AS failed,
       COUNT(*) FILTER (
         WHERE status = 'pending_confirmation' AND risk_level = 'high'
       )::int AS high_risk_pending_review,
       COUNT(*) FILTER (
         WHERE status = 'pending_confirmation' AND risk_level = 'medium'
       )::int AS medium_risk_pending_review,
       COUNT(*) FILTER (
         WHERE status = 'pending_confirmation' AND risk_level = 'low'
       )::int AS low_risk_pending_review,
       COALESCE(AVG(runtime_ms), 0)::float AS avg_runtime_ms
     FROM recent`,
    [windowHours]
  );

  const row = rows[0] as
    | {
        total: number;
        pending: number;
        running: number;
        pending_confirmation: number;
        done: number;
        failed: number;
        high_risk_pending_review: number;
        medium_risk_pending_review: number;
        low_risk_pending_review: number;
        avg_runtime_ms: number;
      }
    | undefined;

  return {
    windowHours,
    total: Number(row?.total ?? 0),
    pending: Number(row?.pending ?? 0),
    running: Number(row?.running ?? 0),
    pendingConfirmation: Number(row?.pending_confirmation ?? 0),
    done: Number(row?.done ?? 0),
    failed: Number(row?.failed ?? 0),
    highRiskPendingReview: Number(row?.high_risk_pending_review ?? 0),
    mediumRiskPendingReview: Number(row?.medium_risk_pending_review ?? 0),
    lowRiskPendingReview: Number(row?.low_risk_pending_review ?? 0),
    avgRuntimeMs: Number(row?.avg_runtime_ms ?? 0),
  };
}

// ── Analytics queries ──────────────────────────────────────────────────

/** All closed trades, ordered by close time, optionally filtered by date range and/or symbol */
export async function getClosedTrades(since?: string, symbol?: string): Promise<Trade[]> {
  const conditions: string[] = ["status = 'CLOSED'"];
  const params: unknown[] = [];
  if (since) { params.push(since); conditions.push(`close_time >= $${params.length}`); }
  if (symbol) { params.push(symbol); conditions.push(`symbol = $${params.length}`); }
  const where = conditions.join(" AND ");
  const rows = await query(
    `SELECT * FROM trades WHERE ${where} ORDER BY close_time ASC`,
    params.length ? params : undefined
  );
  return rows as Trade[];
}

/** Aggregate stats per symbol */
export async function getSymbolStats() {
  return query(`
    SELECT symbol,
           COUNT(*)::int                         AS total,
           COUNT(*) FILTER (WHERE pnl > 0)::int  AS wins,
           COUNT(*) FILTER (WHERE pnl <= 0)::int  AS losses,
           COALESCE(SUM(pnl), 0)                 AS total_pnl,
           COALESCE(AVG(pnl), 0)                 AS avg_pnl,
           COALESCE(AVG(CASE WHEN pnl > 0 THEN pnl END), 0) AS avg_win,
           COALESCE(AVG(CASE WHEN pnl <= 0 THEN pnl END), 0) AS avg_loss
    FROM trades WHERE status = 'CLOSED'
    GROUP BY symbol ORDER BY total_pnl DESC
  `);
}

/** Trades grouped by direction */
export async function getDirectionStats() {
  return query(`
    SELECT direction,
           COUNT(*)::int AS total,
           COALESCE(SUM(pnl), 0) AS total_pnl
    FROM trades WHERE status = 'CLOSED'
    GROUP BY direction
  `);
}

/** Daily PnL for equity curve */
export async function getDailyPnl(since?: string) {
  const base = `
    SELECT close_time::date AS day,
           COUNT(*)::int AS trades,
           COALESCE(SUM(pnl), 0) AS pnl
    FROM trades WHERE status = 'CLOSED'
  `;
  if (since) {
    return query(base + " AND close_time >= $1 GROUP BY day ORDER BY day", [since]);
  }
  return query(base + " GROUP BY day ORDER BY day");
}

/** Summary KPIs */
export async function getKpis() {
  const rows = await query(`
    SELECT
      COUNT(*)::int                         AS total_trades,
      COUNT(*) FILTER (WHERE pnl > 0)::int  AS wins,
      COUNT(*) FILTER (WHERE pnl <= 0)::int AS losses,
      COALESCE(SUM(pnl), 0)                AS total_pnl,
      COALESCE(AVG(pnl), 0)                AS avg_pnl,
      COALESCE(MAX(pnl), 0)                AS best_trade,
      COALESCE(MIN(pnl), 0)                AS worst_trade,
      COALESCE(AVG(EXTRACT(EPOCH FROM (close_time - open_time))/60), 0) AS avg_duration_min
    FROM trades WHERE status = 'CLOSED'
  `);
  return rows[0] ?? {};
}

/** Month-to-date closed P&L (used by Risk Console) */
export async function getMonthlyPnl(): Promise<number> {
  const rows = await query(`
    SELECT COALESCE(SUM(pnl), 0)::float AS monthly_pnl
    FROM trades
    WHERE status = 'CLOSED'
      AND close_time >= date_trunc('month', now() AT TIME ZONE 'UTC')
  `);
  return Number((rows[0] as { monthly_pnl: number }).monthly_pnl ?? 0);
}

// ── ICT Strategy Queries ────────────────────────────────────────────────

/** Recent ICT setups (last 100) */
export async function getIctSetups(symbol?: string) {
  const where = symbol ? "WHERE symbol = $1" : "";
  const params = symbol ? [symbol] : [];
  return query(
    `SELECT * FROM ict_setups ${where} ORDER BY created_at DESC LIMIT 100`,
    params
  );
}

/** ICT setup model stats */
export async function getIctModelStats() {
  return query(`
    SELECT
      model,
      COUNT(*)::int                           AS total,
      COUNT(*) FILTER (WHERE executed)::int   AS executed,
      ROUND(AVG(confidence)::numeric, 1)      AS avg_confidence
    FROM ict_setups
    GROUP BY model
    ORDER BY total DESC
  `);
}

/** ICT confluence frequency */
export async function getIctConfluenceStats() {
  return query(`
    SELECT
      COUNT(*)::int AS total_setups,
      COUNT(*) FILTER (WHERE confluences->>'htf_bias_aligned' = 'true')::int   AS htf_aligned,
      COUNT(*) FILTER (WHERE confluences->>'liquidity_swept' = 'true')::int    AS swept,
      COUNT(*) FILTER (WHERE confluences->>'mss_confirmed' = 'true')::int      AS mss,
      COUNT(*) FILTER (WHERE confluences->>'displacement_present' = 'true')::int AS displacement,
      COUNT(*) FILTER (WHERE confluences->>'fvg_present' = 'true')::int        AS fvg,
      COUNT(*) FILTER (WHERE confluences->>'ob_present' = 'true')::int         AS ob,
      COUNT(*) FILTER (WHERE confluences->>'session_valid' = 'true')::int      AS session_valid,
      ROUND(AVG(confidence)::numeric, 1)                                       AS avg_confidence
    FROM ict_setups
  `);
}

/** ICT session distribution */
export async function getIctSessionStats() {
  return query(`
    SELECT
      session,
      COUNT(*)::int                         AS total,
      COUNT(*) FILTER (WHERE executed)::int AS executed,
      ROUND(AVG(confidence)::numeric, 1)    AS avg_confidence
    FROM ict_setups
    WHERE session != ''
    GROUP BY session
    ORDER BY total DESC
  `);
}

// ── Broker Accounts ─────────────────────────────────────────────────────

export async function getBrokerAccountById(
  id: number
): Promise<BrokerAccount | null> {
  const rows = await query(
    `SELECT id, user_id, name, account_number, server, is_demo, is_active,
            created_at, last_connected
     FROM broker_accounts WHERE id = $1`,
    [id]
  );
  return (rows[0] as BrokerAccount) ?? null;
}

export async function getBrokerAccounts(userId?: number): Promise<BrokerAccount[]> {
  if (userId) {
    const rows = await query(
      `SELECT id, user_id, name, account_number, server, is_demo, is_active,
              created_at, last_connected
       FROM broker_accounts WHERE user_id = $1 ORDER BY created_at DESC`,
      [userId]
    );
    return rows as BrokerAccount[];
  }
  const rows = await query(
    `SELECT id, user_id, name, account_number, server, is_demo, is_active,
            created_at, last_connected
     FROM broker_accounts ORDER BY created_at DESC`
  );
  return rows as BrokerAccount[];
}

export async function addBrokerAccount(
  name: string,
  accountNumber: string,
  encryptedPassword: string,
  server: string,
  isDemo: boolean,
  userId?: number
): Promise<number> {
  const rows = await query(
    `INSERT INTO broker_accounts (user_id, name, account_number, password, server, is_demo)
     VALUES ($1, $2, $3, $4, $5, $6) RETURNING id`,
    [userId ?? null, name, accountNumber, encryptedPassword, server, isDemo]
  );
  return rows[0].id;
}

export async function updateBrokerAccount(
  id: number,
  name: string,
  accountNumber: string,
  encryptedPassword: string | null,
  server: string,
  isDemo: boolean
): Promise<void> {
  if (encryptedPassword) {
    await query(
      `UPDATE broker_accounts SET name=$1, account_number=$2, password=$3, server=$4, is_demo=$5 WHERE id=$6`,
      [name, accountNumber, encryptedPassword, server, isDemo, id]
    );
  } else {
    await query(
      `UPDATE broker_accounts SET name=$1, account_number=$2, server=$3, is_demo=$4 WHERE id=$5`,
      [name, accountNumber, server, isDemo, id]
    );
  }
}

export async function deleteBrokerAccount(id: number): Promise<void> {
  await query("DELETE FROM broker_accounts WHERE id = $1", [id]);
}

export async function activateBrokerAccount(id: number): Promise<void> {
  await query("UPDATE broker_accounts SET is_active = FALSE");
  await query("UPDATE broker_accounts SET is_active = TRUE WHERE id = $1", [id]);
}

// ── Dashboard Users ─────────────────────────────────────────────────────

export async function getUserByUsername(
  username: string
): Promise<DashboardUser | null> {
  const rows = await query(
    "SELECT * FROM dashboard_users WHERE username = $1",
    [username]
  );
  return (rows[0] as DashboardUser) ?? null;
}

export async function getUserById(
  id: number
): Promise<DashboardUser | null> {
  const rows = await query(
    "SELECT id, username, created_at FROM dashboard_users WHERE id = $1",
    [id]
  );
  return (rows[0] as DashboardUser) ?? null;
}

export async function createUser(
  username: string,
  passwordHash: string
): Promise<number> {
  const rows = await query(
    "INSERT INTO dashboard_users (username, password_hash) VALUES ($1, $2) RETURNING id",
    [username, passwordHash]
  );
  return rows[0].id;
}

export async function updateUserPassword(
  userId: number,
  passwordHash: string
): Promise<void> {
  await query(
    "UPDATE dashboard_users SET password_hash = $1 WHERE id = $2",
    [passwordHash, userId]
  );
}

export async function getUserCount(): Promise<number> {
  const rows = await query("SELECT COUNT(*)::int AS count FROM dashboard_users");
  return rows[0].count;
}

// ── Signals ─────────────────────────────────────────────────────────────

export interface Signal {
  id: number;
  signal_intent: string;
  signal_type: string;
  strategy: string;
  symbol: string;
  direction: string;
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  confidence: number;
  reason: string;
  bull_case: string;
  bear_case: string;
  author: string;
  tags: string[];
  points_awarded: boolean;
  follower_score: number;
  created_at: string;
}

export async function getSignals(params: {
  intent?: string;
  type?: string;
  strategy?: string;
  author?: string;
  limit?: number;
}): Promise<Signal[]> {
  const conditions: string[] = [];
  const vals: unknown[] = [];
  if (params.intent)   { vals.push(params.intent);   conditions.push(`signal_intent = $${vals.length}`); }
  if (params.type)      { vals.push(params.type);    conditions.push(`signal_type = $${vals.length}`); }
  if (params.strategy)  { vals.push(params.strategy); conditions.push(`strategy = $${vals.length}`); }
  if (params.author)    { vals.push(params.author);   conditions.push(`author = $${vals.length}`); }
  vals.push(params.limit ?? 50);
  const where = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";
  const rows = await query(
    `SELECT * FROM signals ${where} ORDER BY created_at DESC LIMIT $${vals.length}`,
    vals
  );
  return rows as Signal[];
}

export async function publishSignal(body: {
  signal_intent: string;
  signal_type: string;
  strategy: string;
  symbol?: string;
  direction?: string;
  entry_price?: number;
  stop_loss?: number;
  take_profit_1?: number;
  confidence?: number;
  reason?: string;
  bull_case?: string;
  bear_case?: string;
  author?: string;
  tags?: string[];
}): Promise<number> {
  const rows = await query(
    `INSERT INTO signals
       (signal_intent, signal_type, strategy, symbol, direction,
        entry_price, stop_loss, take_profit_1, confidence,
        reason, bull_case, bear_case, author, tags)
     VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
     RETURNING id`,
    [
      body.signal_intent, body.signal_type, body.strategy,
      body.symbol ?? "", body.direction ?? "",
      body.entry_price ?? 0, body.stop_loss ?? 0, body.take_profit_1 ?? 0,
      body.confidence ?? 0.5,
      body.reason ?? "", body.bull_case ?? "", body.bear_case ?? "",
      body.author ?? "bot", body.tags ?? [],
    ]
  );
  return rows[0].id;
}

// ── Agent Reputation ─────────────────────────────────────────────────────

export interface AgentReputation {
  agent: string;
  total_signals: number;
  adopted_signals: number;
  total_points: number;
  win_streak: number;
  last_score: number;
  reputation_score: number;
  updated_at: string;
}

export async function getAgentReputation(agent: string): Promise<AgentReputation | null> {
  const rows = await query(
    "SELECT * FROM agent_reputation WHERE agent = $1",
    [agent]
  );
  return (rows[0] as AgentReputation) ?? null;
}

export async function getLeaderboard(limit = 10): Promise<AgentReputation[]> {
  const rows = await query(
    `SELECT agent, total_signals, adopted_signals, total_points,
            win_streak, reputation_score, updated_at
     FROM agent_reputation
     ORDER BY total_points DESC
     LIMIT $1`,
    [limit]
  );
  return rows as AgentReputation[];
}

// ── Subscriptions (copy-trading) ────────────────────────────────────────

export interface Subscription {
  id: number;
  follower_id: string;
  leader_id: string;
  leader_strategy: string;
  status: string;
  created_at: string;
}

export async function getSubscriptions(params: {
  follower?: string;
  leader?: string;
}): Promise<Subscription[]> {
  const conditions: string[] = [];
  const vals: unknown[] = [];
  if (params.follower) { vals.push(params.follower); conditions.push(`follower_id = $${vals.length}`); }
  if (params.leader)    { vals.push(params.leader);   conditions.push(`leader_id = $${vals.length}`); }
  const where = conditions.length ? `WHERE ${conditions.join(" AND ")}` : "";
  const rows = await query(`SELECT * FROM subscriptions ${where} ORDER BY created_at DESC`, vals);
  return rows as Subscription[];
}

export async function followLeader(
  followerId: string,
  leaderId: string,
  leaderStrategy = "all"
): Promise<number> {
  const rows = await query(
    `INSERT INTO subscriptions (follower_id, leader_id, leader_strategy)
     VALUES ($1,$2,$3) ON CONFLICT DO NOTHING RETURNING id`,
    [followerId, leaderId, leaderStrategy]
  );
  return rows[0]?.id ?? 0;
}

export async function unfollowLeader(followerId: string, leaderId: string): Promise<boolean> {
  const result = await query(
    `DELETE FROM subscriptions WHERE follower_id = $1 AND leader_id = $2`,
    [followerId, leaderId]
  );
  return (result as { rowCount?: number }).rowCount !== undefined && (result as { rowCount: number }).rowCount > 0;
}

export async function getFollowers(leaderId: string): Promise<Subscription[]> {
  const rows = await query(
    `SELECT * FROM subscriptions WHERE leader_id = $1 AND status = 'ACTIVE' ORDER BY created_at DESC`,
    [leaderId]
  );
  return rows as Subscription[];
}

// ── Macro Snapshots ─────────────────────────────────────────────────────

export interface MacroSnapshot {
  id: number;
  snapshot_json: Record<string, unknown>;
  risk_tier: string;
  yield_inverted: boolean;
  usd_strength: string;
  gdelt_tone: number | null;
  fetched_at: string;
}

export async function getMacroSnapshots(params: {
  lookback_hours?: number;
  risk_tier?: string;
  limit?: number;
}): Promise<MacroSnapshot[]> {
  const conditions = [`fetched_at >= NOW() - ($1 || ' hours')::interval`];
  const vals: unknown[] = [params.lookback_hours ?? 24];
  if (params.risk_tier) {
    vals.push(params.risk_tier);
    conditions.push(`risk_tier = $${vals.length}`);
  }
  vals.push(params.limit ?? 100);
  const rows = await query(
    `SELECT id, snapshot_json, risk_tier, yield_inverted, usd_strength,
            gdelt_tone, fetched_at
     FROM macro_snapshots
     WHERE ${conditions.join(" AND ")}
     ORDER BY fetched_at DESC
     LIMIT $${vals.length}`,
    vals
  );
  return rows as MacroSnapshot[];
}

// ── Encryption helper (mirrors Python utils/crypto.py) ──────────────────

import crypto from "crypto";

function getFernetKey(): Buffer | null {
  const envKey = process.env.ENCRYPTION_KEY;
  if (!envKey) return null;
  return crypto.createHash("sha256").update(envKey).digest();
}

/**
 * Encrypt a plaintext string using AES-256-CBC + HMAC (Fernet-compatible
 * layout simplified to standard Node.js crypto).
 *
 * We use AES-256-CBC with a random IV, then HMAC-SHA256 for integrity.
 * Format: base64( IV(16) + HMAC(32) + ciphertext )
 */
export function encryptValue(plaintext: string): string {
  const key = getFernetKey();
  if (!key) {
    throw new Error(
      "ENCRYPTION_KEY is not set. Broker passwords cannot be stored securely. " +
      "Generate a key and add it to your .env file."
    );
  }

  const iv = crypto.randomBytes(16);
  const cipher = crypto.createCipheriv("aes-256-cbc", key, iv);
  const encrypted = Buffer.concat([
    cipher.update(plaintext, "utf8"),
    cipher.final(),
  ]);
  const hmac = crypto
    .createHmac("sha256", key)
    .update(Buffer.concat([iv, encrypted]))
    .digest();
  // iv(16) + hmac(32) + ciphertext
  return Buffer.concat([iv, hmac, encrypted]).toString("base64");
}

export function decryptValue(ciphertext: string): string {
  const key = getFernetKey();
  if (!key) return ciphertext;

  try {
    const buf = Buffer.from(ciphertext, "base64");
    if (buf.length < 48) return ciphertext; // too short → legacy plaintext
    const iv = buf.subarray(0, 16);
    const storedHmac = buf.subarray(16, 48);
    const encrypted = buf.subarray(48);

    // Verify HMAC
    const computedHmac = crypto
      .createHmac("sha256", key)
      .update(Buffer.concat([iv, encrypted]))
      .digest();
    if (!crypto.timingSafeEqual(storedHmac, computedHmac)) {
      return ciphertext; // HMAC mismatch → probably legacy plaintext
    }

    const decipher = crypto.createDecipheriv("aes-256-cbc", key, iv);
    const decrypted = Buffer.concat([
      decipher.update(encrypted),
      decipher.final(),
    ]);
    return decrypted.toString("utf8");
  } catch {
    return ciphertext; // decrypt fail → legacy plaintext
  }
}
