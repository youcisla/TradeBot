"use client";

import { useRisk } from "@/lib/swr";
import { cn } from "@/lib/utils";

const STATUS_COLOR: Record<string, string> = {
  pass: "var(--positive)",
  warn: "var(--warning)",
  fail: "var(--negative)",
};

export default function GuardTable() {
  const { data: risk } = useRisk();
  const guards = risk?.guards ?? [];

  return (
    <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md overflow-hidden flex flex-col">
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] flex-shrink-0">
        <span className="text-xs font-bold uppercase tracking-widest" style={{ fontFamily: "var(--font-ui)", color: "var(--text-2)", letterSpacing: "0.08em" }}>
          Guard Pipeline
        </span>
        <span className="font-mono text-[10px]" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
          {guards.length} guards
        </span>
      </div>

      {guards.length === 0 ? (
        <p className="font-mono text-sm text-center py-5" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
          No guard data
        </p>
      ) : (
        <div className="overflow-y-auto flex-1">
          {guards.map((g) => (
            <div key={g.name} className="flex items-center gap-3 px-4 py-1.5 border-b border-[var(--border)]">
              <span
                className="rounded-full flex-shrink-0"
                style={{
                  width: 8,
                  height: 8,
                  background: STATUS_COLOR[g.status] ?? "var(--text-3)",
                  boxShadow: `0 0 6px ${STATUS_COLOR[g.status] ?? "transparent"}`,
                }}
              />
              <span className="font-mono text-sm font-semibold flex-1" style={{ fontFamily: "var(--font-mono)", color: "var(--text-1)" }}>
                {g.name}
              </span>
              <span className="font-mono text-sm min-w-[60px] text-right" style={{ fontFamily: "var(--font-mono)", color: "var(--text-2)" }}>
                {g.current}
              </span>
              <span className="font-mono text-[10px] text-[var(--text-3)] min-w-[60px]">
                / {g.threshold}
              </span>
              <span
                className="font-mono text-[9px] font-bold uppercase min-w-[36px] text-right"
                style={{
                  fontFamily: "var(--font-mono)",
                  color: STATUS_COLOR[g.status] ?? "var(--text-3)",
                  letterSpacing: "0.06em",
                }}
              >
                {g.status.toUpperCase()}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
