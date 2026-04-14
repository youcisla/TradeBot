"use client";

import { useAnalytics } from "@/lib/swr";
import { fmtUsd, fmtPct } from "@/lib/format";

interface KPIProps {
  label: string;
  value: string;
  sub?: string;
  color?: string;
}

function KPI({ label, value, sub, color = "var(--text-1)" }: KPIProps) {
  return (
    <div style={styles.kpi}>
      <span style={styles.kpiLabel}>{label}</span>
      <span style={{ ...styles.kpiValue, color }}>{value}</span>
      {sub && <span style={styles.kpiSub}>{sub}</span>}
    </div>
  );
}

export default function KPIRow() {
  const { data: analytics } = useAnalytics();
  const k = analytics?.kpis;

  const winRate   = k ? fmtPct(k.winRate * 100)       : "—";
  const pf       = k && k.profitFactor != null ? k.profitFactor.toFixed(2) : "—";
  const total    = k && k.totalPnl  != null ? fmtUsd(k.totalPnl, false)  : "—";
  const avgWin   = k && k.avgWin     != null ? fmtUsd(k.avgWin, false)    : "—";
  const avgLoss  = k && k.avgLoss   != null ? fmtUsd(k.avgLoss, false)   : "—";
  const expect   = k && k.expectancy != null ? fmtUsd(k.expectancy, false) : "—";
  const trades   = k && k.totalTrades != null ? String(k.totalTrades) : "—";

  const pnlColor = k && k.totalPnl != null
    ? (k.totalPnl >= 0 ? "var(--positive)" : "var(--negative)")
    : "var(--text-1)";

  return (
    <div style={styles.wrapper}>
      <KPI label="Win Rate"    value={winRate} />
      <KPI label="Profit Factor" value={pf} />
      <KPI label="Total P&L"   value={total}  color={pnlColor} />
      <KPI label="Avg Win"     value={avgWin} color="var(--positive)" />
      <KPI label="Avg Loss"    value={avgLoss} color="var(--negative)" />
      <KPI label="Expectancy"  value={expect} />
      <KPI label="Total Trades" value={trades} />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: "grid",
    gridTemplateColumns: "repeat(7, 1fr)",
    gap: "var(--space-3)",
  },
  kpi: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    padding: "var(--space-3) var(--space-4)",
    display: "flex",
    flexDirection: "column",
    gap: 4,
    alignItems: "center",
  },
  kpiLabel: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 700,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  kpiValue: {
    fontFamily: "var(--font-mono)",
    fontSize: 16,
    fontWeight: 700,
  },
  kpiSub: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    color: "var(--text-3)",
  },
};
