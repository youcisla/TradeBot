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
    <div
      className="flex flex-col gap-3"
      style={{ height: "calc(100vh - var(--header-h) - var(--space-5) * 2)" }}
    >
      {/* Controls bar */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <SymbolDrawer selected={symbol} onSelect={(s) => setSymbol(s)} />
        <TimeframeBar selected={timeframe} onChange={setTimeframe} />
        <div className="flex items-center gap-1.5 ml-auto">
          <span
            className="rounded-full"
            style={{
              width: 6, height: 6,
              background: "var(--green)",
              boxShadow: "0 0 6px var(--green)",
            }}
          />
          <span
            className="font-mono font-bold tracking-widest"
            style={{
              color: "var(--green)",
              fontFamily: "var(--font-mono)",
              fontSize: 10,
              letterSpacing: "0.08em",
            }}
          >
            LIVE
          </span>
        </div>
      </div>

      {/* Chart area */}
      <div
        className="flex-1 rounded overflow-hidden"
        style={{
          background: "var(--bg-2)",
          border: "1px solid var(--border)",
          minHeight: 400,
        }}
      >
        <TradingChart symbol={symbol} timeframe={timeframe} count={500} />
      </div>
    </div>
  );
}
