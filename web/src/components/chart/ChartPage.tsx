"use client";

import { useState } from "react";
import TradingChart from "@/components/TradingChart";
import SymbolDrawer from "@/components/chart/SymbolDrawer";
import TimeframeBar from "@/components/chart/TimeframeBar";

const DEFAULT_SYMBOL = "EURUSD";

export default function ChartPage() {
  const [symbol, setSymbol] = useState(DEFAULT_SYMBOL);
  const [timeframe, setTimeframe] = useState<"M1" | "M5" | "M15" | "M30" | "H1" | "H4" | "D1" | "W1">("H1");

  return (
    <div style={styles.root}>
      {/* Controls bar */}
      <div style={styles.controls}>
        <SymbolDrawer selected={symbol} onSelect={(s) => setSymbol(s)} />
        <TimeframeBar selected={timeframe} onChange={setTimeframe} />
        <span style={styles.chartStatus}>
          <span style={styles.dot} />
          LIVE
        </span>
      </div>

      {/* Chart area */}
      <div style={styles.chartArea}>
        <TradingChart
          symbol={symbol}
          timeframe={timeframe}
          count={500}
        />
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    display:        "flex",
    flexDirection: "column",
    height:        "calc(100vh - var(--header-h) - var(--space-5) * 2)",
    gap:           "var(--space-3)",
  },
  controls: {
    display:     "flex",
    alignItems:  "center",
    gap:         "var(--space-3)",
    flexShrink:  0,
  },
  chartStatus: {
    display:     "flex",
    alignItems:  "center",
    gap:         6,
    marginLeft:  "auto",
    fontFamily:  "var(--font-mono)",
    fontSize:    10,
    fontWeight:  700,
    color:       "var(--green)",
    letterSpacing: "0.08em",
  },
  dot: {
    width:        6,
    height:       6,
    borderRadius: "50%",
    background:   "var(--green)",
    boxShadow:    "0 0 6px var(--green)",
  },
  chartArea: {
    flex:       1,
    minHeight:  0,
    background: "var(--bg-2)",
    border:     "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    overflow:   "hidden",
  },
};
