"use client";

import useSWR, { SWRConfiguration } from "swr";

// ── Fetcher ───────────────────────────────────────────────────────────────────

const fetcher = (url: string) => fetch(url).then((r) => r.json());

const BASE_CONF: SWRConfiguration = {
  revalidateOnFocus: true,
  keepPreviousData: true,
  errorRetryCount: 3,
};

// ── Bot status ───────────────────────────────────────────────────────────────

export interface BotStatus {
  state: string;
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

export function useBotStatus() {
  return useSWR<BotStatus>("/api/status", fetcher, {
    ...BASE_CONF,
    refreshInterval: 5_000,
  });
}

// ── Open trades ──────────────────────────────────────────────────────────────

export interface Trade {
  id: number;
  symbol: string;
  direction: string;
  entry_price: number;
  open_time?: string;
  close_time?: string;
  pnl?: number;
  status: string;
  strategy?: string;
  lots?: number;
  tp1?: number;
  tp2?: number;
  sl?: number;
}

export function useOpenTrades() {
  return useSWR<Trade[]>("/api/trades", fetcher, {
    ...BASE_CONF,
    refreshInterval: 5_000,
  });
}

// ── All trades ───────────────────────────────────────────────────────────────

export function useAllTrades(limit = 500) {
  return useSWR<Trade[]>(`/api/trades?all=true&limit=${limit}`, fetcher, {
    ...BASE_CONF,
    refreshInterval: 30_000,
  });
}

// ── Agent events ──────────────────────────────────────────────────────────────

export interface AgentEvent {
  id?: string | number;
  agent: string;
  level: string;
  message?: string;
  msg?: string;
  created_at?: string;
  ts?: string;
  data?: Record<string, unknown>;
}

export function useEvents(limit = 100) {
  return useSWR<AgentEvent[]>(`/api/events?limit=${limit}`, fetcher, {
    ...BASE_CONF,
    refreshInterval: 3_000,
  });
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface Analytics {
  kpis: {
    winRate: number;
    profitFactor: number;
    totalPnl: number;
    avgWin: number;
    avgLoss: number;
    expectancy: number;
    totalTrades: number;
  };
  closedTrades: Trade[];
  dailyPnl: { date: string; pnl: number }[];
  symbolStats: { symbol: string; winRate: number; pnl: number; trades: number }[];
  directionStats: { direction: string; winRate: number; pnl: number }[];
}

export function useAnalytics(since?: string, symbol?: string) {
  const params = new URLSearchParams();
  if (since) params.set("since", since);
  if (symbol) params.set("symbol", symbol);
  const qs = params.toString();
  return useSWR<Analytics>(
    qs ? `/api/analytics?${qs}` : "/api/analytics",
    fetcher,
    { ...BASE_CONF, refreshInterval: 60_000 }
  );
}

// ── Risk ─────────────────────────────────────────────────────────────────────

export interface GuardStatus {
  name: string;
  status: "pass" | "warn" | "fail";
  threshold: string;
  current: string;
  lastCheck?: string;
}

export interface RiskData {
  // Equity snapshot
  equity: number;
  balance: number;
  daily_pnl: number;
  monthly_pnl: number;
  // Loss percentages (daily_loss_pct = daily PnL / balance * 100)
  daily_loss_pct: number;
  monthly_loss_pct: number;
  // Configured limits (as百分比, e.g. 3.0 = 3%)
  max_daily_loss_pct: number;
  max_monthly_loss_pct: number;
  // Bot state
  open_trades: number;
  max_open_trades: number;
  guards: GuardStatus[];
  // WFO assessment
  wfo_overfitting: number | null;
  wfo_stability: number | null;
  wfo_num_windows: number | null;
  wfo_last_run: string | null;
  wfo_strategy: string | null;
  // Emergency caps
  emergency_caps_active: boolean;
  emergency_event_at: string | null;
}

export function useRisk() {
  return useSWR<RiskData>("/api/risk", fetcher, {
    ...BASE_CONF,
    refreshInterval: 10_000,
  });
}

// ── Intelligence ───────────────────────────────────────────────────────────────

export interface Intelligence {
  session: string;
  sessionLabel: string;
  vix?: number;
  spreadCondition: string;
  spreadPips?: number;
  marketRegime: string;
}

export function useIntelligence() {
  return useSWR<Intelligence>("/api/intelligence", fetcher, {
    ...BASE_CONF,
    refreshInterval: 30_000,
  });
}

// ── Candles ──────────────────────────────────────────────────────────────────

export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume?: number;
}

export function useCandles(symbol: string, timeframe: string, count = 500) {
  return useSWR<Candle[]>(
    `/api/candles?symbol=${symbol}&timeframe=${timeframe}&count=${count}`,
    fetcher,
    { ...BASE_CONF }
  );
}

// ── ICT Setups ───────────────────────────────────────────────────────────────

export interface IctSetup {
  type: string;
  price: number;
  direction: string;
  freshness: string;
  filledPct?: number;
  timestamp?: string;
}

export function useIctSetups(symbol: string) {
  return useSWR<IctSetup[]>(`/api/ict?symbol=${symbol}`, fetcher, {
    ...BASE_CONF,
    refreshInterval: 60_000,
  });
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

export function useLearning() {
  return useSWR<LearningData>("/api/learning", fetcher, {
    ...BASE_CONF,
    refreshInterval: 60_000,
  });
}
