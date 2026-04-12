"use client";

import { useAnalytics } from "@/lib/swr";
import { fmtUsd, fmtPct } from "@/lib/format";

export default function BreakdownChart() {
  const { data: analytics } = useAnalytics();

  const symStats = analytics?.symbolStats ?? [];
  const dirStats = analytics?.directionStats ?? [];

  return (
    <div style={styles.wrapper}>
      <div style={styles.section}>
        <span style={styles.sectionTitle}>By Symbol</span>
        {symStats.length === 0 ? (
          <p style={styles.empty}>No data</p>
        ) : (
          symStats.map((s) => (
            <div key={s.symbol} style={styles.row}>
              <span style={styles.rowLabel}>{s.symbol}</span>
              <div style={styles.barWrap}>
                <div
                  style={{
                    ...styles.bar,
                    width: `${Math.min(s.winRate * 100, 100)}%`,
                    background: s.winRate >= 0.5 ? "var(--green)" : "var(--red)",
                  }}
                />
              </div>
              <span style={styles.rowValue}>{fmtPct(s.winRate * 100)}</span>
              <span style={{ ...styles.rowPnl, color: s.pnl >= 0 ? "var(--green)" : "var(--red)" }}>
                {fmtUsd(s.pnl, false)}
              </span>
            </div>
          ))
        )}
      </div>

      <div style={styles.divider} />

      <div style={styles.section}>
        <span style={styles.sectionTitle}>By Direction</span>
        {dirStats.length === 0 ? (
          <p style={styles.empty}>No data</p>
        ) : (
          dirStats.map((d) => (
            <div key={d.direction} style={styles.row}>
              <span style={styles.rowLabel}>{d.direction}</span>
              <div style={styles.barWrap}>
                <div
                  style={{
                    ...styles.bar,
                    width: `${Math.min(d.winRate * 100, 100)}%`,
                    background: d.winRate >= 0.5 ? "var(--green)" : "var(--red)",
                  }}
                />
              </div>
              <span style={styles.rowValue}>{fmtPct(d.winRate * 100)}</span>
              <span style={{ ...styles.rowPnl, color: d.pnl >= 0 ? "var(--green)" : "var(--red)" }}>
                {fmtUsd(d.pnl, false)}
              </span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    padding: "var(--space-4)",
    display: "flex",
    gap: "var(--space-4)",
    alignItems: "flex-start",
  },
  section: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
    minWidth: 0,
  },
  sectionTitle: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 700,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
    marginBottom: "var(--space-1)",
  },
  divider: {
    width: 1,
    background: "var(--border)",
    alignSelf: "stretch",
  },
  row: {
    display: "grid",
    gridTemplateColumns: "56px 1fr 40px 64px",
    alignItems: "center",
    gap: "var(--space-2)",
  },
  rowLabel: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    fontWeight: 700,
    color: "var(--text-1)",
  },
  barWrap: {
    height: 4,
    background: "var(--bg-3)",
    borderRadius: 2,
    overflow: "hidden",
  },
  bar: {
    height: "100%",
    borderRadius: 2,
    transition: "width 0.3s",
  },
  rowValue: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    fontWeight: 600,
    color: "var(--text-2)",
    textAlign: "right",
  },
  rowPnl: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    fontWeight: 700,
    textAlign: "right",
  },
  empty: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    color: "var(--text-3)",
    margin: 0,
  },
};
