"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface BotStatus {
  state: string;
  last_tick?: string;
  equity?: number | string;
  balance?: number | string;
  daily_pnl?: number | string;
  open_trades?: number;
  broker_account?: string;
  broker_server?: string;
  broker_name?: string;
  leverage?: number | string;
}

// ── Context ───────────────────────────────────────────────────────────────────

interface AppShellCtx {
  status: BotStatus | null;
  isRunning: boolean;
  relTime: (ts?: string) => string;
}

const AppShellContext = createContext<AppShellCtx>({
  status: null,
  isRunning: false,
  relTime: () => "—",
});

// ── Hook ─────────────────────────────────────────────────────────────────────

export function useAppShell(): AppShellCtx {
  return useContext(AppShellContext);
}

// ── Provider ─────────────────────────────────────────────────────────────────

function relTime(ts?: string | null): string {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 60_000)  return Math.floor(ms / 1_000)    + "s ago";
  if (ms < 3_600_000) return Math.floor(ms / 60_000)   + "m ago";
  return                     Math.floor(ms / 3_600_000) + "h ago";
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<BotStatus | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await fetch("/api/status");
      if (r.ok) {
        const data: BotStatus = await r.json();
        setStatus(data);
      }
    } catch { /* silent */ }
  }, []);

  // Single polling source — no more duplicate calls from Header + Sidebar + pages
  useEffect(() => {
    load();
    const id = setInterval(load, 8_000);
    return () => clearInterval(id);
  }, [load]);

  const isRunning = status?.state === "running";

  return (
    <AppShellContext.Provider value={{ status, isRunning, relTime }}>
      {children}
    </AppShellContext.Provider>
  );
}
