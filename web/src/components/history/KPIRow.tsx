"use client";

import { useAnalytics } from "@/lib/swr";
import { fmtUsd, fmtPct } from "@/lib/format";

interface KPIProps {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}

function KPI({ label, value, sub, color = "var(--text-1)" }: KPIProps) {
  return (
    <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-4 py-3 flex flex-col gap-1 items-center">
      <span
        className="font-mono text-[9px] font-bold uppercase"
        style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.06em" }}
      >
        {label}
      </span>
      <span
        className="font-mono text-base font-bold"
        style={{ fontFamily: "var(--font-mono)", color }}
      >
        {value}
      </span>
      {sub && (
        <span className="font-mono text-[9px]" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
          {sub}
        </span>
      )}
    </div>
  );
}

export default function KPIRow() {
  const { data: analytics } = useAnalytics();
  const k = analytics?.kpis;

  const winRate   = k ? fmtPct(k.winRate * 100)       : "—";
  const pf       = k && k.profitFactor != null ? k.profitFactor.toFixed(2) : "—";
  const total    = k && k.totalPnl  != null ? fmtUsd(k.totalPnl, false)  : "—";
  const avgWin   = k && k.avgWin     != null ? fmtUsd(k.avgWin, false)    : "—";
  const avgLoss  = k && k.avgLoss   != null ? fmtUsd(k.avgLoss, false)   : "—";
  const expect   = k && k.expectancy != null ? fmtUsd(k.expectancy, false) : "—";
  const trades   = k && k.totalTrades != null ? String(k.totalTrades) : "—";

  const pnlColor = k && k.totalPnl != null
    ? (k.totalPnl >= 0 ? "var(--positive)" : "var(--negative)")
    : "var(--text-1)";

  return (
    <div
      className="grid gap-3"
      style={{ gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))" }}
    >
      <KPI label="Win Rate"       value={winRate} />
      <KPI label="Profit Factor"  value={pf} />
      <KPI label="Total P&L"      value={total}  color={pnlColor} />
      <KPI label="Avg Win"        value={avgWin} color="var(--positive)" />
      <KPI label="Avg Loss"       value={avgLoss} color="var(--negative)" />
      <KPI label="Expectancy"      value={expect} />
      <KPI label="Total Trades"   value={trades} />
    </div>
  );
}
