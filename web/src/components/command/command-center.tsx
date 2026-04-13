"use client";

import { useAppShell } from "@/components/AppShell";
import { StatCard } from "@/components/ui/stat-card";
import { Panel } from "@/components/ui/panel";
import { StatusBadge } from "@/components/ui/status-badge";
import PositionsCard from "@/components/command/PositionsCard";
import EventStream from "@/components/command/EventStream";
import QuickActions from "@/components/command/QuickActions";
import MacroStrip from "@/components/command/MacroStrip";
import { fmtPnl } from "@/lib/format";

const SESSION_COLORS: Record<string, string> = {
  asian:   "var(--purple)",
  london:  "var(--cyan)",
  overlap: "var(--green)",
  newyork: "var(--orange)",
};

export default function CommandCenter() {
  const { status, isRunning, openTrades, intelligence } = useAppShell();

  const equity    = Number(status?.equity    ?? 0);
  const balance   = Number(status?.balance   ?? 0);
  const dailyPnl  = Number(status?.daily_pnl ?? 0);
  const loopCount = status?.loop_count ?? 0;
  const session   = intelligence?.session ?? "—";
  const regime    = intelligence?.marketRegime ?? "—";
  const vix       = intelligence?.vix;
  const spread    = intelligence?.spreadCondition ?? "—";

  const fmt = (v: number, sign = false) =>
    (sign && v > 0 ? "+" : "") +
    "$" +
    Math.abs(v).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

  return (
    <div className="flex flex-col gap-3">

      {/* ── KPI row ── */}
      <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
        <StatCard
          label="Equity"
          value={fmt(equity)}
          color="var(--accent)"
        />
        <StatCard
          label="Balance"
          value={fmt(balance)}
          color="var(--text-2)"
        />
        <StatCard
          label="Daily P&L"
          value={fmt(dailyPnl, true)}
          color={dailyPnl >= 0 ? "var(--green)" : "var(--red)"}
          trend={dailyPnl > 0 ? "up" : dailyPnl < 0 ? "down" : "flat"}
        />
        <StatCard
          label="Open"
          value={String(openTrades.length)}
          color={openTrades.length > 0 ? "var(--gold)" : "var(--text-3)"}
        />
        <StatCard
          label="Loops"
          value={String(loopCount)}
          color="var(--text-3)"
        />
        <StatCard
          label="Bot"
          value={isRunning ? "LIVE" : "IDLE"}
          color={isRunning ? "var(--green)" : "var(--red)"}
        />
      </div>

      {/* ── Macro intelligence strip ── */}
      <MacroStrip />

      {/* ── Quick actions ── */}
      <QuickActions />

      {/* ── Positions + Events ── */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 items-start">
        <PositionsCard />

        <Panel title="Agent Events">
          <EventStream />
        </Panel>
      </div>
    </div>
  );
}
