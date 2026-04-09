"use client";

import { useCallback, useEffect, useState } from "react";
import StatusStrip from "@/components/StatusStrip";
import SymbolSidebar from "@/components/SymbolSidebar";
import NewsTicker from "@/components/NewsTicker";
import TradingChart from "@/components/TradingChart";
import TradesWidget from "@/components/TradesWidget";

// ── Layout constants ───────────────────────────────────────────────────────────

const HEADER_H = 48;    // px — matches StatusStrip height
const SIDEBAR_W = 180;  // px — matches SymbolSidebar width

// ── Page ───────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [symbol, setSymbol] = useState("BTCUSD");
  const [timeframe, setTimeframe] = useState("M1");

  const handleSymbolSelect = useCallback((s: string) => {
    setSymbol(s);
  }, []);

  return (
    <div style={styles.root}>
      {/* Fixed header */}
      <StatusStrip />

      {/* Left sidebar */}
      <SymbolSidebar selected={symbol} onSelect={handleSymbolSelect} />

      {/* Main content area */}
      <main style={styles.main}>
        {/* News ticker */}
        <NewsTicker symbol={symbol} />

        {/* Timeframe selector */}
        <div style={styles.tfBar}>
          <span style={styles.tfLabel}>Chart</span>
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

        {/* Chart + Trades stacked */}
        <div style={styles.content}>
          {/* Chart area */}
          <div style={styles.chartArea}>
            <TradingChart
              symbol={symbol}
              timeframe={timeframe}
              count={500}
            />
          </div>

          {/* Trades widget */}
          <div style={styles.tradesArea}>
            <TradesWidget />
          </div>
        </div>
      </main>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flexDirection: "column",
    minHeight: "100vh",
    background: "#FFFFFF",
  },
  main: {
    marginTop: HEADER_H,
    marginLeft: SIDEBAR_W,
    display: "flex",
    flexDirection: "column",
    flex: 1,
    minHeight: 0,
    overflow: "hidden",
  },
  tfBar: {
    display: "flex",
    alignItems: "center",
    gap: 14,
    padding: "0 16px",
    background: "#FFFFFF",
    borderBottom: "1px solid #F5F5F7",
    height: 38,
    flexShrink: 0,
  },
  tfLabel: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  tfRow: {
    display: "flex",
    gap: 2,
  },
  tfBtn: {
    background: "none",
    border: "none",
    borderRadius: 3,
    padding: "3px 7px",
    cursor: "pointer",
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    color: "#9CA3AF",
    fontWeight: 500,
  },
  tfBtnActive: {
    background: "#F5F5F7",
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
  content: {
    display: "flex",
    flexDirection: "column",
    flex: 1,
    minHeight: 0,
    overflow: "hidden",
  },
  chartArea: {
    flex: "1 1 60%",
    minHeight: 0,
    background: "#0D0D0F",
    overflow: "hidden",
  },
  tradesArea: {
    flex: "0 0 40%",
    minHeight: 200,
    maxHeight: 340,
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
    borderTop: "1px solid #F5F5F7",
  },
};
