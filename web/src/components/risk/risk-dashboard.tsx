"use client";

import { useAppShell } from "@/components/AppShell";
import { useRisk } from "@/lib/swr";
import { Panel } from "@/components/ui/panel";
import { StatCard } from "@/components/ui/stat-card";
import DrawdownGauge from "@/components/risk/DrawdownGauge";
import GuardTable from "@/components/risk/guard-table";

export default function RiskDashboard() {
  const { status } = useAppShell();
  const { data: risk } = useRisk();

  const openPos = risk?.open_trades ?? 0;
  const maxPos  = risk?.max_open_trades ?? 0;

  const posColor =
    openPos >= maxPos
      ? "var(--red)"
      : openPos >= maxPos * 0.7
      ? "var(--orange)"
      : "var(--green)";

  return (
    <div className="flex flex-col gap-3">

      {/* Position slot utilisation */}
      <Panel title="Position Slots">
        <div className="flex items-end gap-4">
          <div className="flex items-baseline gap-1">
            <span
              className="font-bold"
              style={{ color: posColor, fontFamily: "var(--font-mono)", fontSize: "var(--space-7)", lineHeight: 1 }}
            >
              {openPos}
            </span>
            <span
              className="font-bold"
              style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: "var(--space-5)" }}
            >
              /
            </span>
            <span
              className="font-bold"
              style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: "var(--space-5)" }}
            >
              {maxPos}
            </span>
          </div>
          <div className="flex flex-col gap-1 flex-1">
            <div
              className="h-1.5 rounded-full overflow-hidden"
              style={{ background: "var(--bg-3)" }}
            >
              <div
                className="h-full rounded-full transition-all duration-500"
                style={{
                  width: `${maxPos > 0 ? (openPos / maxPos) * 100 : 0}%`,
                  background: posColor,
                }}
              />
            </div>
            <span
              className="font-mono text-xs"
              style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 10 }}
            >
              {maxPos > 0 ? ((openPos / maxPos) * 100).toFixed(0) : 0}% utilisation
            </span>
          </div>
        </div>
      </Panel>

      {/* Drawdown gauges */}
      <DrawdownGauge />

      {/* Guard pipeline */}
      <GuardTable />
    </div>
  );
}
