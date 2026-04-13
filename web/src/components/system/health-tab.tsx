"use client";

import { useAppShell } from "@/components/AppShell";
import { useEvents } from "@/lib/swr";
import { relTime } from "@/lib/format";
import { Panel } from "@/components/ui/panel";
import { StatusBadge } from "@/components/ui/status-badge";

export default function HealthTab() {
  const { status, isRunning } = useAppShell();
  const { data: events = [] } = useEvents(50);

  const errors = events.filter((e) => e.level === "error").slice(0, 5);
  const warns  = events.filter((e) => e.level === "warn").slice(0, 5);

  return (
    <div className="flex flex-col gap-3">
      {/* Status row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatusCard
          label="Bot State"
          value={status?.state ?? "—"}
          color={isRunning ? "var(--green)" : "var(--text-3)"}
          pulse={isRunning}
        />
        <StatusCard
          label="Loop Count"
          value={String(status?.loop_count ?? "—")}
          color="var(--text-2)"
        />
        <StatusCard
          label="Last Tick"
          value={status?.last_tick ? relTime(status.last_tick) : "—"}
          color="var(--text-2)"
        />
        <StatusCard
          label="Scan Latency"
          value={
            status?.last_scan_latency_ms != null
              ? `${status.last_scan_latency_ms}ms`
              : "—"
          }
          color={
            status?.last_scan_latency_ms != null && status.last_scan_latency_ms > 30000
              ? "var(--orange)"
              : "var(--text-2)"
          }
        />
      </div>

      {/* Errors */}
      <Panel title="Recent Errors">
        {errors.length === 0 ? (
          <p className="font-mono text-sm" style={{ color: "var(--green)", margin: 0 }}>
            No errors
          </p>
        ) : (
          <div className="flex flex-col">
            {errors.map((e, i) => (
              <div
                key={i}
                className="flex gap-3 items-start py-2 border-b"
                style={{ borderColor: "var(--border)" }}
              >
                <span className="font-mono flex-shrink-0" style={{ color: "var(--text-3)", fontSize: 10, minWidth: 56 }}>
                  {relTime(e.created_at)}
                </span>
                <span className="font-mono flex-1" style={{ color: "var(--text-2)", fontSize: 11 }}>
                  {e.message ?? e.msg ?? "—"}
                </span>
              </div>
            ))}
          </div>
        )}
      </Panel>

      {/* Warnings */}
      <Panel title="Recent Warnings">
        {warns.length === 0 ? (
          <p className="font-mono text-sm" style={{ color: "var(--text-3)", margin: 0 }}>
            No warnings
          </p>
        ) : (
          <div className="flex flex-col">
            {warns.map((e, i) => (
              <div
                key={i}
                className="flex gap-3 items-start py-2 border-b"
                style={{ borderColor: "var(--border)" }}
              >
                <span className="font-mono flex-shrink-0" style={{ color: "var(--text-3)", fontSize: 10, minWidth: 56 }}>
                  {relTime(e.created_at)}
                </span>
                <span className="font-mono flex-1" style={{ color: "var(--text-2)", fontSize: 11 }}>
                  {e.message ?? e.msg ?? "—"}
                </span>
              </div>
            ))}
          </div>
        )}
      </Panel>
    </div>
  );
}

function StatusCard({
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
    <div
      className="rounded p-3 flex flex-col gap-1"
      style={{ background: "var(--bg-2)", border: "1px solid var(--border)" }}
    >
      <span
        className="font-mono text-xs font-bold uppercase tracking-widest"
        style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 9 }}
      >
        {label}
      </span>
      <div className="flex items-center gap-2">
        {pulse && (
          <span
            className="rounded-full flex-shrink-0"
            style={{
              width: 6, height: 6,
              background: color,
              boxShadow: `0 0 6px ${color}`,
            }}
          />
        )}
        <span className="font-mono font-bold" style={{ color, fontFamily: "var(--font-mono)", fontSize: 14 }}>
          {value}
        </span>
      </div>
    </div>
  );
}
