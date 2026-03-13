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
      ssl: { rejectUnauthorized: false },
      max: 3,
      idleTimeoutMillis: 30_000,
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
}

export interface AgentEvent {
  id: number;
  agent: string;
  level: string;
  message: string;
  data: Record<string, unknown> | null;
  created_at: string;
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

export async function getOpenTrades(): Promise<Trade[]> {
  const rows = await query(
    "SELECT * FROM trades WHERE status IN ('OPEN','PARTIAL') ORDER BY open_time DESC"
  );
  return rows as Trade[];
}

export async function getAllTrades(limit = 100): Promise<Trade[]> {
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
  payload?: Record<string, unknown>
): Promise<void> {
  await query(
    "INSERT INTO bot_commands (command, payload) VALUES ($1, $2)",
    [command, payload ? JSON.stringify(payload) : null]
  );
}

// ── Analytics queries ──────────────────────────────────────────────────

/** All closed trades, ordered by close time, optionally filtered by date range */
export async function getClosedTrades(since?: string): Promise<Trade[]> {
  if (since) {
    const rows = await query(
      "SELECT * FROM trades WHERE status = 'CLOSED' AND close_time >= $1 ORDER BY close_time ASC",
      [since]
    );
    return rows as Trade[];
  }
  const rows = await query(
    "SELECT * FROM trades WHERE status = 'CLOSED' ORDER BY close_time ASC"
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
