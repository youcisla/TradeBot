"use client";

import { useAppShell } from "@/components/AppShell";
import { StatCard } from "@/components/ui/stat-card";

function fmtCurrency(v: number, sign = false) {
  return (
    (sign && v > 0 ? "+" : "") +
    "$" +
    Math.abs(v).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })
  );
}

export default function KpiRow() {
  const { status, isRunning } = useAppShell();

  const equity    = Number(status?.equity    ?? 0);
  const balance   = Number(status?.balance   ?? 0);
  const dailyPnl  = Number(status?.daily_pnl ?? 0);
  const loopCount = status?.loop_count ?? 0;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-6 gap-3">
      <StatCard
        label="Equity"
        value={fmtCurrency(equity)}
        color="neutral"
        size="lg"
      />
      <StatCard
        label="Balance"
        value={fmtCurrency(balance)}
        color="neutral"
      />
      <StatCard
        label="Daily P&L"
        value={fmtCurrency(dailyPnl, true)}
        color={dailyPnl >= 0 ? "positive" : "negative"}
        trend={dailyPnl > 0 ? "up" : dailyPnl < 0 ? "down" : "flat"}
      />
      <StatCard
        label="Loops"
        value={String(loopCount)}
        color="neutral"
        size="sm"
      />
      <StatCard
        label="Bot"
        value={isRunning ? "LIVE" : "IDLE"}
        color={isRunning ? "positive" : "negative"}
        pulse={isRunning}
      />
    </div>
  );
}