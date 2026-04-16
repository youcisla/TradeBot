"use client";

import { useAnalytics } from "@/lib/swr";
import { fmtUsd, fmtPct } from "@/lib/format";

export default function BreakdownChart() {
  const { data: analytics } = useAnalytics();

  const symStats = analytics?.symbolStats ?? [];
  const dirStats = analytics?.directionStats ?? [];

  return (
    <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-4 py-4 flex gap-4 items-start">
      <div className="flex-1 flex flex-col gap-2 min-w-0">
        <span className="font-mono text-[9px] font-bold uppercase mb-1" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.08em" }}>
          By Symbol
        </span>
        {symStats.length === 0 ? (
          <p className="font-mono text-sm m-0" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>No data</p>
        ) : (
          symStats.map((s) => (
            <BreakdownRow key={s.symbol} label={s.symbol} winRate={s.winRate} pnl={s.pnl} />
          ))
        )}
      </div>

      <span className="w-px self-stretch flex-shrink-0" style={{ background: "var(--border)" }} />

      <div className="flex-1 flex flex-col gap-2 min-w-0">
        <span className="font-mono text-[9px] font-bold uppercase mb-1" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.08em" }}>
          By Direction
        </span>
        {dirStats.length === 0 ? (
          <p className="font-mono text-sm m-0" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>No data</p>
        ) : (
          dirStats.map((d) => (
            <BreakdownRow key={d.direction} label={d.direction} winRate={d.winRate} pnl={d.pnl} />
          ))
        )}
      </div>
    </div>
  );
}

function BreakdownRow({ label, winRate, pnl }: { label: string; winRate: number; pnl: number }) {
  const barColor = winRate >= 0.5 ? "var(--positive)" : "var(--negative)";
  return (
    <div className="grid items-center gap-2" style={{ gridTemplateColumns: "56px 1fr 40px 64px" }}>
      <span className="font-mono text-sm font-bold" style={{ fontFamily: "var(--font-mono)", color: "var(--text-1)" }}>
        {label}
      </span>
      <div className="h-1 bg-[var(--bg-3)] rounded overflow-hidden">
        <div
          className="h-full rounded transition-all"
          style={{ width: `${Math.min(winRate * 100, 100)}%`, background: barColor }}
        />
      </div>
      <span className="font-mono text-[10px] font-semibold text-right" style={{ fontFamily: "var(--font-mono)", color: "var(--text-2)" }}>
        {fmtPct(winRate * 100)}
      </span>
      <span
        className="font-mono text-[10px] font-bold text-right"
        style={{ fontFamily: "var(--font-mono)", color: pnl >= 0 ? "var(--green)" : "var(--red)" }}
      >
        {fmtUsd(pnl, false)}
      </span>
    </div>
  );
}
