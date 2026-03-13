"use client";

import { useState } from "react";
import BotStatusBar from "@/components/BotStatusBar";
import AgentFeed from "@/components/AgentFeed";
import OpenTradesTable from "@/components/OpenTradesTable";
import CommandPanel from "@/components/CommandPanel";
import EquityCurve from "@/components/EquityCurve";
import SymbolFilter from "@/components/SymbolFilter";

export default function DashboardPage() {
  const [symbol, setSymbol] = useState<string | null>(null);

  return (
    <div className="space-y-6">
      <BotStatusBar />
      <SymbolFilter value={symbol} onChange={setSymbol} />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Agent feed (2 cols) */}
        <div className="lg:col-span-2">
          <AgentFeed symbol={symbol} />
        </div>

        {/* Right: Commands + equity curve */}
        <div className="space-y-6">
          <CommandPanel />
          <EquityCurve />
        </div>
      </div>

      <OpenTradesTable symbol={symbol} />
    </div>
  );
}
