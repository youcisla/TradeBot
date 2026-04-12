"use client";

import { useAppShell } from "@/components/AppShell";
import { useRisk } from "@/lib/swr";
import DrawdownGauge from "@/components/risk/DrawdownGauge";
import GuardTable from "@/components/risk/GuardTable";

export default function RiskDashboard() {
  const { status } = useAppShell();
  const { data: risk } = useRisk();

  const openPos  = risk?.openPositions  ?? 0;
  const maxPos   = risk?.maxPositions   ?? 0;

  const posColor = openPos >= maxPos ? "var(--red)" : openPos >= maxPos * 0.7 ? "var(--orange)" : "var(--green)";

  return (
    <div style={styles.root}>
      {/* Position slot utilisation */}
      <div style={styles.slotCard}>
        <span style={styles.slotLabel}>Open Slots</span>
        <div style={styles.slotNumbers}>
          <span style={{ ...styles.slotValue, color: posColor }}>
            {openPos}
          </span>
          <span style={styles.slotSep}>/</span>
          <span style={styles.slotMax}>{maxPos}</span>
        </div>
        <div style={styles.slotTrack}>
          <div
            style={{
              ...styles.slotFill,
              width: `${maxPos > 0 ? (openPos / maxPos) * 100 : 0}%`,
              background: posColor,
            }}
          />
        </div>
        <span style={styles.slotPct}>
          {maxPos > 0 ? ((openPos / maxPos) * 100).toFixed(0) : 0}% utilisation
        </span>
      </div>

      {/* Drawdown gauges */}
      <DrawdownGauge />

      {/* Guard pipeline */}
      <GuardTable />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-3)",
  },
  slotCard: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    padding: "var(--space-4)",
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-2)",
  },
  slotLabel: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 700,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  slotNumbers: {
    display: "flex",
    alignItems: "baseline",
    gap: 6,
  },
  slotValue: {
    fontFamily: "var(--font-mono)",
    fontSize: 40,
    fontWeight: 700,
    lineHeight: 1,
  },
  slotSep: {
    fontFamily: "var(--font-mono)",
    fontSize: 24,
    color: "var(--text-3)",
  },
  slotMax: {
    fontFamily: "var(--font-mono)",
    fontSize: 20,
    fontWeight: 700,
    color: "var(--text-3)",
  },
  slotTrack: {
    height: 6,
    background: "var(--bg-3)",
    borderRadius: 3,
    overflow: "hidden",
  },
  slotFill: {
    height: "100%",
    borderRadius: 3,
    transition: "width 0.4s, background 0.3s",
  },
  slotPct: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    color: "var(--text-3)",
  },
};
