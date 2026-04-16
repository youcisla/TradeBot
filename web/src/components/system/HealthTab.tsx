"use client";

import { useAppShell } from "@/components/AppShell";
import { relTime } from "@/lib/format";

export default function HealthTab() {
  const { status, isRunning, wsEvents } = useAppShell();
  const events = wsEvents;

  const errors = events.filter((e) => e.level === "ERROR").slice(0, 5);
  const warns  = events.filter((e) => e.level === "WARN").slice(0, 5);

  return (
    <div className="flex flex-col gap-3">
      {/* Status row */}
      <div className="grid grid-cols-4 gap-3">
        <HealthPill
          label="Bot State"
          value={status?.state ?? "—"}
          color={isRunning ? "var(--positive)" : "var(--text-3)"}
          pulse={isRunning}
        />
        <HealthPill
          label="Loop Count"
          value={String(status?.loop_count ?? "—")}
          color="var(--text-2)"
        />
        <HealthPill
          label="Last Tick"
          value={status?.last_tick ? relTime(status.last_tick) : "—"}
          color="var(--text-2)"
        />
        <HealthPill
          label="Scan Latency"
          value={status?.last_scan_latency_ms != null ? `${status.last_scan_latency_ms}ms` : "—"}
          color={status?.last_scan_latency_ms != null && status.last_scan_latency_ms > 30000 ? "var(--warning)" : "var(--text-2)"}
        />
      </div>

      {/* Errors */}
      <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-4 py-3 flex flex-col gap-2">
        <span className="font-mono text-[9px] font-bold uppercase" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.06em" }}>
          Recent Errors
        </span>
        {errors.length === 0 ? (
          <p className="font-mono text-sm" style={{ fontFamily: "var(--font-mono)", color: "var(--positive)", margin: 0 }}>No errors</p>
        ) : (
          errors.map((e, i) => (
            <div key={i} className="flex gap-3 items-start py-1 border-b border-[var(--border)] last:border-b-0">
              <span className="font-mono text-[10px] text-[var(--text-3)] min-w-[60px] flex-shrink-0" style={{ fontFamily: "var(--font-mono)" }}>
                {relTime(e.created_at)}
              </span>
              <span className="font-mono text-sm text-[var(--text-2)] flex-1" style={{ fontFamily: "var(--font-mono)" }}>
                {e.message ?? e.msg ?? "—"}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Warnings */}
      <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-4 py-3 flex flex-col gap-2">
        <span className="font-mono text-[9px] font-bold uppercase" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.06em" }}>
          Recent Warnings
        </span>
        {warns.length === 0 ? (
          <p className="font-mono text-sm" style={{ fontFamily: "var(--font-mono)", color: "var(--positive)", margin: 0 }}>No warnings</p>
        ) : (
          warns.map((e, i) => (
            <div key={i} className="flex gap-3 items-start py-1 border-b border-[var(--border)] last:border-b-0">
              <span className="font-mono text-[10px] text-[var(--text-3)] min-w-[60px] flex-shrink-0" style={{ fontFamily: "var(--font-mono)" }}>
                {relTime(e.created_at)}
              </span>
              <span className="font-mono text-sm text-[var(--text-2)] flex-1" style={{ fontFamily: "var(--font-mono)" }}>
                {e.message ?? e.msg ?? "—"}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function HealthPill({
  label,
  value,
  color,
  pulse = false,
}: {
  label: string;
  value: string;
  color: string;
  pulse?: boolean;
}) {
  return (
    <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md px-4 py-3 flex flex-col gap-1">
      <span className="font-mono text-[9px] font-bold uppercase" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.06em" }}>
        {label}
      </span>
      <div className="flex items-center gap-1.5">
        {pulse && (
          <span className="rounded-full flex-shrink-0" style={{ width: 6, height: 6, background: color, boxShadow: `0 0 6px ${color}` }} />
        )}
        <span className="font-mono text-sm font-bold" style={{ fontFamily: "var(--font-mono)", color }}>
          {value}
        </span>
      </div>
    </div>
  );
}
