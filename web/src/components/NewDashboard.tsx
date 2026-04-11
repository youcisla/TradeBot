"use client";

import { useCallback, useState } from "react";
import TopBar from "@/components/TopBar";
import SymbolSidebar from "@/components/SymbolSidebar";
import IntelligencePanel from "@/components/IntelligencePanel";
import TradingChart from "@/components/TradingChart";
import TradeTable from "@/components/TradeTable";
import SmartAlertFeed from "@/components/SmartAlertFeed";
import WorldStrip from "@/components/WorldStrip";

export default function DashboardPage() {
  const [symbol, setSymbol] = useState("BTCUSD");
  const [timeframe, setTimeframe] = useState("H1");

  const handleSymbolSelect = useCallback((s: string) => {
    setSymbol(s);
  }, []);

  return (
    <div style={styles.root}>
      <TopBar />

      <div style={styles.body}>
        {/* Left: symbol browser */}
        <SymbolSidebar selected={symbol} onSelect={handleSymbolSelect} />

        {/* Center: chart + trades */}
        <div style={styles.center}>
          {/* Chart controls bar */}
          <div style={styles.tfBar}>
            <div style={styles.tfRow}>
              {(["M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1"] as const).map((tf) => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  style={{
                    ...styles.tfBtn,
                    ...(timeframe === tf ? styles.tfBtnActive : {}),
                  }}
                >
                  {tf}
                </button>
              ))}
            </div>
            <span style={styles.symLabel}>{symbol}</span>
          </div>

          {/* Chart */}
          <div style={styles.chartArea}>
            <TradingChart symbol={symbol} timeframe={timeframe} count={500} />
          </div>

          {/* Smart alert feed */}
          <div style={styles.alertArea}>
            <SmartAlertFeed />
          </div>

          {/* Trade table */}
          <div style={styles.tableArea}>
            <TradeTable />
          </div>
        </div>

        {/* Right: intelligence panel */}
        <IntelligencePanel />
      </div>

      {/* Bottom: world strip */}
      <WorldStrip />
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flexDirection: "column",
    minHeight: "100vh",
    background: "#F8F8F8",
  },
  body: {
    display: "flex",
    flex: 1,
    minHeight: 0,
    marginTop: 48,
  },
  center: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    minWidth: 0,
    marginLeft: 180,
    marginRight: 264,
  },
  tfBar: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    padding: "0 16px",
    background: "#FFFFFF",
    borderBottom: "1px solid #F0F0F0",
    height: 36,
    flexShrink: 0,
  },
  tfRow: {
    display: "flex",
    gap: 2,
  },
  tfBtn: {
    background: "none",
    border: "none",
    borderRadius: 3,
    padding: "3px 8px",
    cursor: "pointer",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    color: "#9CA3AF",
    fontWeight: 500,
  },
  tfBtnActive: {
    background: "#F0F0F0",
    color: "#111111",
    fontWeight: 700,
  },
  symLabel: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 12,
    fontWeight: 700,
    color: "#111111",
    marginLeft: "auto",
  },
  chartArea: {
    flex: "1 1 55%",
    minHeight: 0,
    background: "#0D0D0F",
    overflow: "hidden",
  },
  alertArea: {
    flex: "0 0 auto",
    padding: "6px 12px",
    background: "#1C1C1E",
    borderTop: "1px solid rgba(95,122,158,0.2)",
    borderBottom: "1px solid rgba(95,122,158,0.2)",
  },
  tableArea: {
    flex: "0 0 45%",
    minHeight: 160,
    maxHeight: 340,
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
    background: "#FFFFFF",
  },
};
