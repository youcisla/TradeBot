"use client";

import { createContext, useContext } from "react";
import { useBotStatus } from "@/lib/swr";
import type { BotStatus as SwrBotStatus } from "@/lib/swr";

// ── Types ─────────────────────────────────────────────────────────────────────

export interface BotStatus extends SwrBotStatus {}

// ── Context ───────────────────────────────────────────────────────────────────

interface AppShellCtx {
  status: BotStatus | undefined;
  isRunning: boolean;
  relTime: (ts?: string) => string;
}

const AppShellContext = createContext<AppShellCtx>({
  status: undefined,
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
  // Single SWR fetcher — all components that call useBotStatus() share this cache
  const { data: status } = useBotStatus();

  const isRunning = status?.state === "running";

  return (
    <AppShellContext.Provider value={{ status, isRunning, relTime }}>
      {children}
    </AppShellContext.Provider>
  );
}
