"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import TimeframeSelector from "@/components/TimeframeSelector";
import ChartSymbolSelector from "@/components/ChartSymbolSelector";

const TradingChart = dynamic(() => import("@/components/TradingChart"), {
  ssr: false,
  loading: () => (
    <div style={{
      width: "100%", height: "100%", minHeight: 400,
      display: "flex", alignItems: "center", justifyContent: "center",
      background: "#0a0a12", border: "1px solid #1c1c28", borderRadius: 8,
      fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
      color: "#607888", letterSpacing: "0.06em",
    }}>
      Initializing chart engine…
    </div>
  ),
});

export default function ChartPage() {
  const [symbol, setSymbol]       = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("H1");

  return (
    <div style={{
      display: "flex", flexDirection: "column",
      height: "calc(100vh - 94px)", gap: 12,
    }}>
      {/* Header bar */}
      <div style={{
        display: "flex", alignItems: "center",
        justifyContent: "space-between",
        flexShrink: 0, flexWrap: "wrap", gap: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <ChartSymbolSelector value={symbol} onChange={setSymbol} />
          <TimeframeSelector value={timeframe} onChange={setTimeframe} />
        </div>
        <div style={{
          display: "flex", alignItems: "center", gap: 8,
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9, letterSpacing: "0.2em",
          textTransform: "uppercase", color: "#607888",
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: "50%",
            background: "#00ff88",
            boxShadow: "0 0 6px #00ff88",
            display: "inline-block",
          }} />
          Live Chart · {symbol} · {timeframe}
        </div>
      </div>

      {/* Chart */}
      <div style={{ flex: 1, minHeight: 0 }}>
        <TradingChart symbol={symbol} timeframe={timeframe} count={500} />
      </div>
    </div>
  );
}
