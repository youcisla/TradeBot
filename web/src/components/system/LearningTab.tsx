"use client";

import { useLearning, useRisk } from "@/lib/swr";
import { fmtPct } from "@/lib/format";

export default function LearningTab() {
  const { data: ld } = useLearning();
  const { data: risk } = useRisk();

  return (
    <div style={styles.root}>
      {/* WFO scores — from /api/risk */}
      <div style={styles.wfoRow}>
        <WFOCard
          label="Overfitting Score"
          value={risk?.wfo_overfitting != null ? fmtPct(risk.wfo_overfitting * 100) : "—"}
          color={risk?.wfo_overfitting != null && risk.wfo_overfitting > 0.7 ? "var(--red)" : "var(--green)"}
        />
        <WFOCard
          label="Stability Score"
          value={risk?.wfo_stability != null ? fmtPct(risk.wfo_stability * 100) : "—"}
          color={risk?.wfo_stability != null && risk.wfo_stability < 0.5 ? "var(--orange)" : "var(--green)"}
        />
      </div>

      {/* Strategy confidences */}
      <div style={styles.tableCard}>
        <span style={styles.tableTitle}>Strategy Confidence</span>
        {(ld?.confidences ?? []).length === 0 ? (
          <p style={styles.empty}>No strategy data</p>
        ) : (
          ld?.confidences.map((s) => (
            <div key={s.strategy} style={styles.row}>
              <span style={styles.strategy}>{s.strategy}</span>
              <div style={styles.confBar}>
                <div
                  style={{
                    ...styles.confFill,
                    width: `${Math.min(s.confidence * 100, 100)}%`,
                    background: s.confidence >= 0.6 ? "var(--green)" : s.confidence >= 0.4 ? "var(--orange)" : "var(--red)",
                  }}
                />
              </div>
              <span style={styles.confPct}>{fmtPct(s.confidence * 100)}</span>
              <span style={styles.trades}>{s.total_trades}t</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

function WFOCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={styles.wfoCard}>
      <span style={styles.wfoLabel}>{label}</span>
      <span style={{ ...styles.wfoValue, color }}>{value}</span>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-3)",
  },
  wfoRow: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "var(--space-3)",
  },
  wfoCard: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    padding: "var(--space-4)",
    display: "flex",
    flexDirection: "column",
    gap: 4,
    alignItems: "center",
  },
  wfoLabel: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 700,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  wfoValue: {
    fontFamily: "var(--font-mono)",
    fontSize: 24,
    fontWeight: 700,
  },
  tableCard: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    padding: "var(--space-3)",
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
  },
  tableTitle: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 700,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  empty: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    color: "var(--text-3)",
    margin: 0,
  },
  row: {
    display: "grid",
    gridTemplateColumns: "100px 1fr 48px 32px",
    alignItems: "center",
    gap: "var(--space-2)",
    padding: "4px 0",
    borderBottom: "1px solid var(--border)",
  },
  strategy: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    fontWeight: 700,
    color: "var(--text-1)",
  },
  confBar: {
    height: 4,
    background: "var(--bg-3)",
    borderRadius: 2,
    overflow: "hidden",
  },
  confFill: {
    height: "100%",
    borderRadius: 2,
    transition: "width 0.3s",
  },
  confPct: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    fontWeight: 600,
    color: "var(--text-2)",
    textAlign: "right",
  },
  trades: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    color: "var(--text-3)",
    textAlign: "right",
  },
  trend: {
    fontFamily: "var(--font-mono)",
    fontSize: 12,
    fontWeight: 700,
    textAlign: "center",
  },
};
