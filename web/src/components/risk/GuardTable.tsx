"use client";

import { useRisk } from "@/lib/swr";
import { relTime } from "@/lib/format";

const STATUS_COLOR: Record<string, string> = {
  pass: "var(--green)",
  warn: "var(--orange)",
  fail: "var(--red)",
};

export default function GuardTable() {
  const { data: risk } = useRisk();
  const guards = risk?.guards ?? [];

  return (
    <div style={styles.wrapper}>
      <div style={styles.header}>
        <span style={styles.title}>Guard Pipeline</span>
        <span style={styles.count}>{guards.length} guards</span>
      </div>

      {guards.length === 0 ? (
        <p style={styles.empty}>No guard data</p>
      ) : (
        <div style={styles.table}>
          {guards.map((g) => (
            <div key={g.name} style={styles.row}>
              <span
                style={{
                  ...styles.statusDot,
                  background: STATUS_COLOR[g.status] ?? "var(--text-3)",
                  boxShadow: `0 0 6px ${STATUS_COLOR[g.status] ?? "transparent"}`,
                }}
              />
              <span style={styles.name}>{g.name}</span>
              <span style={styles.current}>{g.current}</span>
              <span style={styles.threshold}>/ {g.threshold}</span>
              <span
                style={{
                  ...styles.statusLabel,
                  color: STATUS_COLOR[g.status] ?? "var(--text-3)",
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

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "var(--space-3) var(--space-4)",
    borderBottom: "1px solid var(--border)",
    flexShrink: 0,
  },
  title: {
    fontFamily: "var(--font-ui)",
    fontSize: 11,
    fontWeight: 700,
    color: "var(--text-2)",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  count: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    color: "var(--text-3)",
  },
  table: {
    overflowY: "auto",
    flex: 1,
  },
  row: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-3)",
    padding: "6px var(--space-4)",
    borderBottom: "1px solid var(--border)",
  },
  statusDot: {
    width: 8,
    height: 8,
    borderRadius: "50%",
    flexShrink: 0,
  },
  name: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    fontWeight: 600,
    color: "var(--text-1)",
    flex: 1,
  },
  current: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    color: "var(--text-2)",
    minWidth: 60,
    textAlign: "right",
  },
  threshold: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    color: "var(--text-3)",
    minWidth: 60,
  },
  statusLabel: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 700,
    letterSpacing: "0.06em",
    minWidth: 36,
    textAlign: "right",
  },
  empty: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    color: "var(--text-3)",
    textAlign: "center",
    padding: "var(--space-5)",
    margin: 0,
  },
};
