/**
 * Centralised API type definitions.
 * These types mirror the HTTP API responses from the backend.
 * Import from here — do not duplicate types across components.
 */

// ── Bot ───────────────────────────────────────────────────────────────────────

export interface BotStatus {
  state: "RUNNING" | "IDLE" | "PAUSED" | "STOPPED";
  last_tick?: string | null;
  equity?: number | string;
  balance?: number | string;
  daily_pnl?: number | string;
  open_trades?: number;
  uptime_start?: string | null;
  broker_account?: string;
  broker_server?: string;
  broker_name?: string;
  leverage?: number | string;
  loop_count?: number;
  last_scan_latency_ms?: number;
  last_reconnect_at?: string;
}

// ── Trades ───────────────────────────────────────────────────────────────────

export type TradeDirection = "BUY" | "SELL";
export type TradeStatus = "OPEN" | "CLOSED" | "PARTIAL";

export interface Trade {
  id: number;
  symbol: string;
  direction: TradeDirection;
  entry_price: number;
  open_time?: string;
  close_time?: string;
  pnl?: number;
  status: TradeStatus;
  strategy?: string;
  lots?: number;
  tp1?: number;
  tp2?: number;
  tp3?: number;
  tp4?: number;
  sl?: number;
  /** Percentage of TP levels hit (0–4) */
  tp_hits?: number;
}

// ── Signals ───────────────────────────────────────────────────────────────────

export type SignalDirection = "BUY" | "SELL" | "HOLD";

export interface Signal {
  id: string;
  symbol: string;
  direction: SignalDirection;
  strategy: string;
  confidence: number;        // 0–100
  created_at: string;
  entry_price: number;
  tp1: number;
  tp2: number;
  tp3: number;
  tp4: number;
  sl: number;
  /** Bull case reasoning text */
  bull_case?: string;
  /** Bear case reasoning text */
  bear_case?: string;
  /** Structural break level */
  structural_be?: number;
  /** Rank within current scan (1 = best) */
  rank?: number;
}

// ── Risk ──────────────────────────────────────────────────────────────────────

export type GuardStatusValue = "pass" | "warn" | "fail";

export interface GuardStatus {
  name: string;
  status: GuardStatusValue;
  threshold: string;
  current: string;
  lastCheck?: string;
}

export interface RiskData {
  equity: number;
  balance: number;
  daily_pnl: number;
  monthly_pnl: number;
  daily_loss_pct: number;
  monthly_loss_pct: number;
  max_daily_loss_pct: number;
  max_monthly_loss_pct: number;
  open_trades: number;
  max_open_trades: number;
  guards: GuardStatus[];
  // WFO
  wfo_overfitting: number | null;
  wfo_stability: number | null;
  wfo_num_windows: number | null;
  wfo_last_run: string | null;
  wfo_strategy: string | null;
  // Emergency
  emergency_caps_active: boolean;
  emergency_event_at: string | null;
}

// ── Intelligence ──────────────────────────────────────────────────────────────

export type SessionName = "asian" | "london" | "overlap" | "newyork";

export interface Intelligence {
  session: SessionName;
  sessionLabel: string;
  vix?: number;
  spreadCondition: string;
  spreadPips?: number;
  marketRegime: string;
}

// ── Agent Events ───────────────────────────────────────────────────────────────

export type AgentLevel = "INFO" | "WARN" | "ERROR" | "DEBUG";

export interface AgentEvent {
  id?: string | number;
  agent: string;
  level: AgentLevel;
  message?: string;
  msg?: string;
  created_at?: string;
  ts?: string;
  data?: Record<string, unknown>;
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface DailyPnl {
  date: string;
  pnl: number;
}

export interface SymbolStats {
  symbol: string;
  winRate: number;
  pnl: number;
  trades: number;
}

export interface DirectionStats {
  direction: TradeDirection;
  winRate: number;
  pnl: number;
}

export interface Kpis {
  winRate: number;
  profitFactor: number;
  totalPnl: number;
  avgWin: number;
  avgLoss: number;
  expectancy: number;
  totalTrades: number;
}

export interface Analytics {
  kpis: Kpis;
  closedTrades: Trade[];
  dailyPnl: DailyPnl[];
  symbolStats: SymbolStats[];
  directionStats: DirectionStats[];
}

// ── Learning ──────────────────────────────────────────────────────────────────

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

export interface LearningData {
  confidences: StrategyConfidence[];
  scores: TradeScore[];
}

// ── Health ────────────────────────────────────────────────────────────────────

export type ServiceHealth = "healthy" | "degraded" | "down" | "unknown";

export interface ServiceStatus {
  name: string;
  status: ServiceHealth;
  latency_ms?: number;
  error?: string;
}

export interface HealthData {
  services: ServiceStatus[];
  overall: ServiceHealth;
}

// ── Candles ───────────────────────────────────────────────────────────────────

export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

// ── ICT Setups ────────────────────────────────────────────────────────────────

export interface IctSetup {
  type: string;
  price: number;
  direction: TradeDirection;
  freshness: string;
  filledPct?: number;
  timestamp?: string;
}
