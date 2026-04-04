"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import TimeframeSelector from "@/components/TimeframeSelector";
import ChartSymbolSelector from "@/components/ChartSymbolSelector";

const TradingChart = dynamic(() => import("@/components/TradingChart"), {
  ssr: false,
  loading: () => (
    <div style={{
      width: "100%",
      height: "100%",
      minHeight: 400,
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "#1C1C1E",
      borderRadius: 12,
      flexDirection: "column",
      gap: 12,
    }}>
      <div style={{
        width: 28,
        height: 28,
        border: "2px solid rgba(84,84,88,0.4)",
        borderTop: "2px solid #0A84FF",
        borderRadius: "50%",
        animation: "spin 0.8s linear infinite",
      }} />
      <span style={{
        fontFamily: `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`,
        fontSize: 13,
        color: "rgba(235,235,245,0.4)",
        letterSpacing: "0.02em",
      }}>
        Initializing chart engine…
      </span>
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  ),
});

export default function ChartPage() {
  const [symbol, setSymbol] = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("H1");

  return (
    <div style={{
      display: "flex",
      flexDirection: "column",
      gap: 12,
      paddingTop: 20,
      height: "calc(100vh - 80px)",
      fontFamily: `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`,
    }}>
      {/* Header bar */}
      <div style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: 10,
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <ChartSymbolSelector value={symbol} onChange={setSymbol} />
          <TimeframeSelector value={timeframe} onChange={setTimeframe} />
        </div>

        <div style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          fontSize: 12,
          color: "rgba(235,235,245,0.4)",
          letterSpacing: "0.02em",
        }}>
          <span style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "#30D158",
            display: "inline-block",
            boxShadow: "0 0 6px rgba(48,209,88,0.6)",
            animation: "pulse 2s ease-in-out infinite",
          }} />
          Live · {symbol} · {timeframe}
        </div>
      </div>

      {/* Chart container */}
      <div style={{
        flex: 1,
        minHeight: 0,
        background: "#1C1C1E",
        borderRadius: 12,
        overflow: "hidden",
        boxShadow: "0 4px 24px rgba(0,0,0,0.4)",
      }}>
        <TradingChart symbol={symbol} timeframe={timeframe} count={500} />
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  );
}
