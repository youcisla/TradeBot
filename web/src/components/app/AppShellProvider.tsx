"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import useSWR from "swr";
import type { AgentEvent } from "@/types/api";
import { useBotStatus, type Trade } from "@/lib/swr";

// ── Fetcher ───────────────────────────────────────────────────────────────────

const fetcher = (url: string) => fetch(url).then((r) => r.json());

// ── Context types ─────────────────────────────────────────────────────────────

interface AppShellCtx {
  status: {
    state: string;
    equity: number;
    balance: number;
    daily_pnl: number;
    open_trades: number;
    loop_count?: number;
    last_tick?: string | null;
    uptime_start?: string | null;
    guard_status?: unknown[];
    broker_account?: string;
    broker_server?: string;
    broker_name?: string;
    leverage?: number;
    last_scan_latency_ms?: number;
    last_reconnect_at?: string;
  } | undefined;
  isRunning: boolean;
  wsEvents: AgentEvent[];
  openTrades: Trade[];
  intelligence: {
    session: string;
    sessionLabel: string;
    spreadCondition: string;
    marketRegime: string;
    vix?: number;
    dailyLossPct?: number;
  } | undefined;
  auth: {
    sessionToken: string | null;
    derivedKey: string | null;
    isAuthenticated: boolean;
    botLocked: boolean;
    activeProfileId: number | null;
    profiles: Array<{
      id: number;
      profile_label: string;
      account_number: string;
      server: string;
      is_demo: boolean;
      is_active: boolean;
    }>;
  };
}

const AppShellContext = createContext<AppShellCtx>({
  status: undefined,
  isRunning: false,
  wsEvents: [],
  openTrades: [],
  intelligence: undefined,
  auth: {
    sessionToken: null,
    derivedKey: null,
    isAuthenticated: false,
    botLocked: true,
    activeProfileId: null,
    profiles: [],
  },
});

export function useAppShell(): AppShellCtx {
  return useContext(AppShellContext);
}

// ── Auth helpers ───────────────────────────────────────────────────────────────

function useAuthState() {
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [derivedKey, setDerivedKey] = useState<string | null>(null);

  useEffect(() => {
    setSessionToken(sessionStorage.getItem("session_token"));
    setDerivedKey(sessionStorage.getItem("derived_key"));
  }, []);

  const { data: authStatus } = useSWR(
    sessionToken ? "http://127.0.0.1:8001/api/auth/status" : null,
    (url) =>
      fetch(url, {
        headers: { Authorization: `Bearer ${sessionToken}` },
      }).then((r) => r.json()),
    { revalidateOnFocus: false, refreshInterval: 10_000 }
  ) as { data?: { authenticated: boolean; user_id: number | null; username: string | null; bot_locked: boolean; active_profile_id: number | null } };

  const { data: profiles = [] } = useSWR(
    sessionToken ? "http://127.0.0.1:8001/api/auth/profiles" : null,
    (url) =>
      fetch(url, {
        headers: { Authorization: `Bearer ${sessionToken}` },
      }).then((r) => r.json()),
    { revalidateOnFocus: false, refreshInterval: 30_000 }
  ) as { data?: Array<{ id: number; profile_label: string; account_number: string; server: string; is_demo: boolean; is_active: boolean }> };

  return {
    sessionToken,
    derivedKey,
    isAuthenticated: !!authStatus?.authenticated,
    botLocked: authStatus?.bot_locked ?? true,
    activeProfileId: authStatus?.active_profile_id ?? null,
    profiles,
    setSessionToken,
    setDerivedKey,
  };
}

// ── WebSocket bridge ──────────────────────────────────────────────────────────

const WS_URL =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_WS_URL as string | undefined) ?? null
    : null;

function useGlobalWebSocket() {
  const [wsEvents, setWsEvents] = useState<AgentEvent[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    if (!WS_URL) return;
    mountedRef.current = true;

    let reconnectTimer: ReturnType<typeof setTimeout>;

    function connect() {
      try {
        const ws = new WebSocket(WS_URL as string);
        ws.onmessage = (msg) => {
          if (!mountedRef.current) return;
          try {
            const incoming: AgentEvent[] = JSON.parse(msg.data);
            setWsEvents((prev) => [...incoming, ...prev].slice(0, 200));
          } catch { /* ignore */ }
        };
        let reconnectAttempt = 0;
        ws.onerror = () => {
          reconnectAttempt++;
          console.warn(`[WS] error — attempt ${reconnectAttempt}, reconnecting in 3s`);
          ws.close();
        };
        ws.onclose = () => {
          if (!mountedRef.current) return;
          reconnectTimer = setTimeout(connect, 3_000);
        };
        wsRef.current = ws;
      } catch { /* not available */ }
    }

    connect();

    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  }, []);

  return wsEvents;
}

// ── Provider ──────────────────────────────────────────────────────────────────

export function AppShellProvider({ children }: { children: React.ReactNode }) {
  const { data: dashboard } = useSWR("/api/dashboard-summary", fetcher, {
    revalidateOnFocus: false,
    keepPreviousData: true,
    errorRetryCount: 3,
    refreshInterval: 5_000,
  });

  const wsEvents = useGlobalWebSocket();
  const authState = useAuthState();

  const status    = dashboard?.status;
  const openTrades = dashboard?.openTrades ?? [];
  const isRunning  = status?.state === "RUNNING";

  return (
    <AppShellContext.Provider
      value={{
        status,
        isRunning,
        wsEvents,
        openTrades,
        intelligence: undefined,
        auth: authState,
      }}
    >
      {children}
    </AppShellContext.Provider>
  );
}