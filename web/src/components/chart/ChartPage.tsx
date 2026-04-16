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
    <div className="flex flex-col" style={{ height: "calc(100vh - var(--header-h) - var(--space-5) * 2)" }}>
      {/* Controls bar */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <SymbolDrawer selected={symbol} onSelect={(s) => setSymbol(s)} />
        <TimeframeBar selected={timeframe} onChange={setTimeframe} />
        <span className="flex items-center gap-1.5 ml-auto font-mono text-[10px] font-bold uppercase" style={{ fontFamily: "var(--font-mono)", color: "var(--positive)", letterSpacing: "0.08em" }}>
          <span className="rounded-full" style={{ width: 6, height: 6, background: "var(--positive)", boxShadow: "0 0 6px var(--positive)" }} />
          LIVE
        </span>
      </div>

      {/* Chart area */}
      <div className="flex-1 min-h-0 bg-[var(--bg-2)] border border-[var(--border)] rounded-md overflow-hidden mt-3">
        <TradingChart
          symbol={symbol}
          timeframe={timeframe}
          count={500}
        />
      </div>
    </div>
  );
}
