"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import TimeframeSelector from "@/components/TimeframeSelector";
import ChartSymbolSelector from "@/components/ChartSymbolSelector";

const TradingChart = dynamic(() => import("@/components/TradingChart"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full min-h-[400px] flex items-center justify-center bg-surface-container border border-outline-variant/10 text-[11px] text-outline tracking-widest uppercase">
      Initializing chart engine…
    </div>
  ),
});

export default function ChartPage() {
  const [symbol,    setSymbol]    = useState("EURUSD");
  const [timeframe, setTimeframe] = useState("H1");

  return (
    <div className="flex flex-col mt-6 gap-4" style={{ height: "calc(100vh - 108px)" }}>

      {/* ── Header Bar ── */}
      <div className="flex items-center justify-between flex-wrap gap-3 shrink-0">
        <div className="flex items-center gap-3">
          <ChartSymbolSelector value={symbol} onChange={setSymbol} />
          <TimeframeSelector value={timeframe} onChange={setTimeframe} />
        </div>

        <div className="flex items-center gap-2 text-[9px] text-outline tracking-[0.2em] uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-primary-fixed animate-pulse" />
          Live Chart · {symbol} · {timeframe}
        </div>
      </div>

      {/* ── Chart Container ── */}
      <div className="flex-1 min-h-0 bg-surface-container border border-outline-variant/10">
        <TradingChart symbol={symbol} timeframe={timeframe} count={500} />
      </div>
    </div>
  );
}
