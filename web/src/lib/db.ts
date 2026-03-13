import { sql } from "@vercel/postgres";

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
  const { rows } = await sql`SELECT * FROM bot_status WHERE id = 1`;
  return rows[0] as BotStatus | null;
}

export async function getAgentEvents(limit = 80): Promise<AgentEvent[]> {
  const { rows } =
    await sql`SELECT * FROM agent_events ORDER BY created_at DESC LIMIT ${limit}`;
  return rows as AgentEvent[];
}

export async function getOpenTrades(): Promise<Trade[]> {
  const { rows } =
    await sql`SELECT * FROM trades WHERE status IN ('OPEN','PARTIAL') ORDER BY open_time DESC`;
  return rows as Trade[];
}

export async function getAllTrades(limit = 100): Promise<Trade[]> {
  const { rows } =
    await sql`SELECT * FROM trades ORDER BY open_time DESC LIMIT ${limit}`;
  return rows as Trade[];
}

export async function getStrategyConfidences(): Promise<StrategyConfidence[]> {
  const { rows } =
    await sql`SELECT * FROM strategy_confidence ORDER BY strategy`;
  return rows as StrategyConfidence[];
}

export async function getTradeScores(limit = 100): Promise<TradeScore[]> {
  const { rows } =
    await sql`SELECT * FROM trade_scores ORDER BY created_at DESC LIMIT ${limit}`;
  return rows as TradeScore[];
}

export async function insertCommand(
  command: string,
  payload?: Record<string, unknown>
): Promise<void> {
  await sql`INSERT INTO bot_commands (command, payload) VALUES (${command}, ${
    payload ? JSON.stringify(payload) : null
  })`;
}
