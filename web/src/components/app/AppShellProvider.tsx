"use client";

import { createContext, useContext, useEffect, useRef, useState } from "react";
import { useBotStatus, useOpenTrades, useIntelligence } from "@/lib/swr";
import type { AgentEvent } from "@/types/api";
import type { BotStatus, Intelligence, Trade } from "@/lib/swr";

// ── Context types ─────────────────────────────────────────────────────────────

interface AppShellCtx {
  status: BotStatus | undefined;
  isRunning: boolean;
  wsEvents: AgentEvent[];
  openTrades: Trade[];
  intelligence: Intelligence | undefined;
}

const AppShellContext = createContext<AppShellCtx>({
  status: undefined,
  isRunning: false,
  wsEvents: [],
  openTrades: [],
  intelligence: undefined,
});

export function useAppShell(): AppShellCtx {
  return useContext(AppShellContext);
}

// ── WebSocket bridge ──────────────────────────────────────────────────────────

const WS_URL =
  typeof window !== "undefined"
    ? (window as unknown as { NEXT_PUBLIC_WS_URL?: string }).NEXT_PUBLIC_WS_URL ?? null
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
  const botStatus = useBotStatus();
  const openTradesHook = useOpenTrades();
  const intelligenceHook = useIntelligence();
  const wsEvents = useGlobalWebSocket();

  const status = botStatus.data;
  const openTrades = openTradesHook.data ?? [];
  const intelligence = intelligenceHook.data;
  const isRunning = status?.state === "RUNNING";

  return (
    <AppShellContext.Provider
      value={{
        status,
        isRunning,
        wsEvents,
        openTrades,
        intelligence,
      }}
    >
      {children}
    </AppShellContext.Provider>
  );
}
