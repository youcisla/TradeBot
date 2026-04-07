"use client";

import useSWR, { SWRConfiguration } from "swr";

// ── Fetcher ───────────────────────────────────────────────────────────────────

const fetcher = (url: string) => fetch(url).then(r => r.json());

// ── Shared config ────────────────────────────────────────────────────────────

const POLL_INTERVAL = 8_000;
const CONF: SWRConfiguration = {
  refreshInterval: POLL_INTERVAL,
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
}

export function useBotStatus() {
  return useSWR<BotStatus>("/api/status", fetcher, CONF);
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

export function useAgentEvents(limit = 80) {
  return useSWR<AgentEvent[]>(`/api/events?limit=${limit}`, fetcher, {
    ...CONF,
    refreshInterval: 5_000, // faster for live feed
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
}

export function useTrades(all = false) {
  return useSWR<Trade[]>(`/api/trades${all ? "?all=true&limit=500" : ""}`, fetcher, {
    ...CONF,
    refreshInterval: 12_000,
  });
}
