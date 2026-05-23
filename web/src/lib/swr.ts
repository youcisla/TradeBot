"use client";

import useSWR, { SWRConfiguration } from "swr";

// ── Fetcher ───────────────────────────────────────────────────────────────────

const fetcher = (url: string) => fetch(url).then((r) => r.json());

const BASE_CONF: SWRConfiguration = {
  revalidateOnFocus: false,
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
  guard_status?: unknown[];
  current_session?: string;
  market_regime?: string;
  spread_pips?: number;
  vix?: number;
  equity_drawdown_pct?: number;
  daily_loss_pct?: number;
  spread_condition?: string;
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
  lot_size?: number;
  tp1?: number;
  tp2?: number;
  tp3?: number;
  tp4?: number;
  sl?: number;
  stop_loss?: number;
  tp1_lots?: number;
  tp2_lots?: number;
  tp3_lots?: number;
  tp4_lots?: number;
  tp1_hit?: boolean;
  tp2_hit?: boolean;
  current_price?: number;
  broker_ticket?: number;
  close_reason?: string;
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

// ── Signals ─────────────────────────────────────────────────────────────────────

export function useSignals(intent?: string, limit = 50) {
  const params = new URLSearchParams();
  if (intent) params.set("intent", intent);
  params.set("limit", String(limit));
  return useSWR<import("@/lib/db").Signal[]>(`/api/signals?${params}`, fetcher, {
    ...BASE_CONF,
    refreshInterval: 5_000,
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
  nextSession?: string;
  nextSessionIn?: number;
  vix?: number;
  spreadCondition: string;
  spreadPips?: number;
  marketRegime: string;
  dailyLossPct?: number;
  equityDrawdownPct?: number;
  todayPnl?: number;
  winRate?: number;
  tradesToday?: number;
  openTrades?: number;
  totalTrades?: number;
  recentAlerts?: Array<{
    id: number;
    agent: string;
    level: string;
    message: string;
    created_at: string;
  }>;
  alertCount?: number;
  intelligence?: string;
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

// ── Auth (FastAPI session) ───────────────────────────────────────────────────────

export interface LoginRequest {
  username: string;
  password: string;
}

export interface LoginResponse {
  user_id: number;
  username: string;
  session_token: string;
  expires_at: number;
}

export interface AuthStatus {
  authenticated: boolean;
  user_id: number | null;
  username: string | null;
  bot_locked: boolean;
  active_profile_id: number | null;
}

export interface BrokerProfile {
  id: number;
  profile_label: string;
  account_number: string;
  server: string;
  is_demo: boolean;
  is_active: boolean;
}

export interface UnlockRequest {
  session_token: string;
  profile_id: number;
  derived_key: string;
}

export interface UnlockResponse {
  ok: boolean;
  account: string;
  server: string;
}

export function useLogin() {
  return async (body: LoginRequest): Promise<LoginResponse> => {
    const res = await fetch("http://127.0.0.1:8001/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail ?? "Login failed");
    }
    return res.json();
  };
}

export function useAuthStatus(sessionToken: string | null) {
  return useSWR<AuthStatus>(
    sessionToken ? ["http://127.0.0.1:8001/api/auth/status", sessionToken] : null,
    () => {
      if (!sessionToken) throw new Error("No session");
      return fetch("http://127.0.0.1:8001/api/auth/status", {
        headers: { Authorization: `Bearer ${sessionToken}` },
      }).then((r) => r.json());
    },
    { ...BASE_CONF, refreshInterval: 10_000 }
  );
}

export function useProfiles(sessionToken: string | null) {
  return useSWR<BrokerProfile[]>(
    sessionToken ? ["http://127.0.0.1:8001/api/auth/profiles", sessionToken] : null,
    () => {
      if (!sessionToken) throw new Error("No session");
      return fetch("http://127.0.0.1:8001/api/auth/profiles", {
        headers: { Authorization: `Bearer ${sessionToken}` },
      }).then((r) => r.json());
    },
    { ...BASE_CONF, refreshInterval: 30_000 }
  );
}

export async function unlockBot(body: UnlockRequest): Promise<UnlockResponse> {
  const res = await fetch("http://127.0.0.1:8001/api/auth/unlock", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? "Unlock failed");
  }
  return res.json();
}

export async function activateProfile(
  profileId: number,
  sessionToken: string
): Promise<{ ok: boolean }> {
  const res = await fetch(
    `http://127.0.0.1:8001/api/auth/profiles/${profileId}/activate`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${sessionToken}` },
    }
  );
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? "Activate failed");
  }
  return res.json();
}

export async function deleteProfile(
  profileId: number,
  sessionToken: string
): Promise<{ ok: boolean }> {
  const res = await fetch(
    `http://127.0.0.1:8001/api/auth/profiles/${profileId}/delete`,
    {
      method: "POST",
      headers: { Authorization: `Bearer ${sessionToken}` },
    }
  );
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? "Delete failed");
  }
  return res.json();
}

export async function createProfile(
  body: {
    profile_label: string;
    account_number: string;
    server: string;
    password: string;
  },
  sessionToken: string
): Promise<BrokerProfile> {
  const res = await fetch("http://127.0.0.1:8001/api/auth/profiles", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${sessionToken}`,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail ?? "Create profile failed");
  }
  return res.json();
}

// ── Backtest ───────────────────────────────────────────────────────────────────────

export interface StrategyStats {
  symbol: string;
  strategy: string;
  signals: number;
  wins: number;
  tp1_hits: number;
  tp2_hits: number;
  tp3_hits: number;
  sl_hits: number;
  timeouts: number;
  total_r: number;
  avg_r: number;
  win_rate: number;
  profit_factor: number;
  score: number;
}

export interface BacktestJob {
  jobId: string;
  status: "running" | "done" | "error";
  started_at: string;
  result: StrategyStats[] | null;
  error: string | null;
}

export function useBacktestStatus(jobId: string | null) {
  return useSWR<BacktestJob>(
    jobId ? `/api/backtest/status?jobId=${encodeURIComponent(jobId)}` : null,
    fetcher,
    {
      ...BASE_CONF,
      refreshInterval: jobId ? 3_000 : 0,
      revalidateOnFocus: false,
    },
  );
}
