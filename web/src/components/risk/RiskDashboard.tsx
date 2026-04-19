"use client";

import { useAppShell } from "@/components/AppShell";
import { useRisk } from "@/lib/swr";
import DrawdownGauge from "@/components/risk/DrawdownGauge";
import GuardTable from "@/components/risk/GuardTable";

export default function RiskDashboard() {
  const { status } = useAppShell();
  const { data: risk } = useRisk();

  const openPos  = risk?.open_trades  ?? 0;
  const maxPos   = risk?.max_open_trades   ?? 0;

  const posColor = openPos >= maxPos ? "var(--red)" : openPos >= maxPos * 0.7 ? "var(--orange)" : "var(--green)";
  const pct = maxPos > 0 ? ((openPos / maxPos) * 100).toFixed(0) : "0";

  return (
    <div className="flex flex-col gap-3">
      {/* Position slot utilisation */}
      <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-4 py-4 flex flex-col gap-2">
        <span
          className="font-mono text-[9px] font-bold uppercase tracking-[0.06em]"
        >
          Open Slots
        </span>
        <div className="flex items-baseline gap-1.5">
          <span className="font-mono text-4xl font-bold leading-none" style={{ fontFamily: "var(--font-mono)", color: posColor }}>
            {openPos}
          </span>
          <span className="font-mono text-2xl" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>/</span>
          <span className="font-mono text-xl font-bold" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
            {maxPos}
          </span>
        </div>
        <div className="h-1.5 bg-[var(--bg-3)] rounded overflow-hidden">
          <div
            className="h-full rounded transition-all"
            style={{
              width: `${maxPos > 0 ? (openPos / maxPos) * 100 : 0}%`,
              background: posColor,
            }}
          />
        </div>
        <span className="font-mono text-[10px]" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
          {pct}% utilisation
        </span>
      </div>

      {/* Drawdown gauges */}
      <DrawdownGauge />

      {/* Guard pipeline */}
      <GuardTable />
    </div>
  );
}
