"use client";

import { useAppShell } from "@/components/AppShell";
import { relTime } from "@/lib/format";

export default function HealthTab() {
  const { status, isRunning, wsEvents } = useAppShell();
  const events = wsEvents;

  const errors = events.filter((e) => e.level === "ERROR").slice(0, 5);
  const warns  = events.filter((e) => e.level === "WARN").slice(0, 5);

  return (
    <div style={styles.root}>
      {/* Status row */}
      <div style={styles.statusRow}>
        <HealthPill
          label="Bot State"
          value={status?.state ?? "—"}
          color={isRunning ? "var(--green)" : "var(--text-3)"}
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
          color={status?.last_scan_latency_ms != null && status.last_scan_latency_ms > 30000 ? "var(--orange)" : "var(--text-2)"}
        />
      </div>

      {/* Errors */}
      <div style={styles.section}>
        <span style={styles.sectionTitle}>Recent Errors</span>
        {errors.length === 0 ? (
          <p style={styles.ok}>No errors</p>
        ) : (
          errors.map((e, i) => (
            <div key={i} style={styles.eventRow}>
              <span style={styles.eventTime}>{relTime(e.created_at)}</span>
              <span style={styles.eventMsg}>{e.message ?? e.msg ?? "—"}</span>
            </div>
          ))
        )}
      </div>

      {/* Warnings */}
      <div style={styles.section}>
        <span style={styles.sectionTitle}>Recent Warnings</span>
        {warns.length === 0 ? (
          <p style={styles.ok}>No warnings</p>
        ) : (
          warns.map((e, i) => (
            <div key={i} style={styles.eventRow}>
              <span style={styles.eventTime}>{relTime(e.created_at)}</span>
              <span style={styles.eventMsg}>{e.message ?? e.msg ?? "—"}</span>
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
    <div style={styles.pill}>
      <span style={styles.pillLabel}>{label}</span>
      <div style={styles.pillValueRow}>
        {pulse && <span style={{ ...styles.dot, background: color, boxShadow: `0 0 6px ${color}` }} />}
        <span style={{ ...styles.pillValue, color }}>{value}</span>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-3)",
  },
  statusRow: {
    display: "grid",
    gridTemplateColumns: "repeat(4, 1fr)",
    gap: "var(--space-3)",
  },
  pill: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    padding: "var(--space-3)",
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  pillLabel: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 700,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  pillValueRow: {
    display: "flex",
    alignItems: "center",
    gap: 6,
  },
  dot: {
    width: 6,
    height: 6,
    borderRadius: "50%",
    flexShrink: 0,
  },
  pillValue: {
    fontFamily: "var(--font-mono)",
    fontSize: 13,
    fontWeight: 700,
  },
  section: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    padding: "var(--space-3)",
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
  },
  sectionTitle: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 700,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  ok: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    color: "var(--green)",
    margin: 0,
  },
  eventRow: {
    display: "flex",
    gap: "var(--space-3)",
    alignItems: "flex-start",
    padding: "4px 0",
    borderBottom: "1px solid var(--border)",
  },
  eventTime: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    color: "var(--text-3)",
    minWidth: 60,
    flexShrink: 0,
  },
  eventMsg: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    color: "var(--text-2)",
    flex: 1,
  },
};
