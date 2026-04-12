"use client";

import EquityCurve from "@/components/history/EquityCurve";
import KPIRow from "@/components/history/KPIRow";
import TradeHistory from "@/components/history/TradeHistory";
import BreakdownChart from "@/components/history/BreakdownChart";

export default function HistoryPage() {
  return (
    <div style={styles.root}>
      {/* Top KPIs */}
      <KPIRow />

      {/* Equity curve + breakdown side by side */}
      <div style={styles.midRow}>
        <div style={styles.curveWrap}>
          <EquityCurve />
        </div>
        <div style={styles.breakdownWrap}>
          <BreakdownChart />
        </div>
      </div>

      {/* Trade history */}
      <TradeHistory />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-3)",
  },
  midRow: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "var(--space-3)",
    alignItems: "start",
  },
  curveWrap: {
    minWidth: 0,
  },
  breakdownWrap: {
    minWidth: 0,
  },
};
