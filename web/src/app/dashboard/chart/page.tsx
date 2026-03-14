"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import TimeframeSelector from "@/components/TimeframeSelector";
import ChartSymbolSelector from "@/components/ChartSymbolSelector";

// Dynamic import to avoid SSR issues with lightweight-charts (uses canvas)
const TradingChart = dynamic(() => import("@/components/TradingChart"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[400px] rounded border border-terminal-border bg-terminal-surface flex items-center justify-center">
      <span className="text-matrix-dim text-xs animate-pulse">Loading chart...</span>
    </div>
  ),
});

export default function ChartPage() {
  const [symbol, setSymbol] = useState("BTCUSD");
  const [timeframe, setTimeframe] = useState("H1");

  return (
    <div className="flex flex-col h-[calc(100vh-65px)] gap-3">
      {/* Header bar */}
      <div className="flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-4">
          <ChartSymbolSelector value={symbol} onChange={setSymbol} />
          <TimeframeSelector value={timeframe} onChange={setTimeframe} />
        </div>
        <div className="text-matrix-dim text-[10px] uppercase tracking-widest">
          Live Chart · {symbol} · {timeframe}
        </div>
      </div>

      {/* Chart area — fills remaining space */}
      <div className="flex-1 min-h-0">
        <TradingChart symbol={symbol} timeframe={timeframe} count={500} />
      </div>
    </div>
  );
}
