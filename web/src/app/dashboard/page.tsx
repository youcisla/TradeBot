"use client";

import { useState } from "react";
import BotStatusBar from "@/components/BotStatusBar";
import AgentFeed from "@/components/AgentFeed";
import OpenTradesTable from "@/components/OpenTradesTable";
import CommandPanel from "@/components/CommandPanel";
import EquityCurve from "@/components/EquityCurve";
import SymbolFilter from "@/components/SymbolFilter";

function SectionHeader({ title, sub }: { title: string; sub?: string }) {
  return (
    <div style={{ marginBottom: 10, display: "flex", alignItems: "baseline", gap: 10 }}>
      <span style={{
        fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
        color: "#607888", letterSpacing: "0.2em", textTransform: "uppercase", fontWeight: 600,
      }}>
        {title}
      </span>
      {sub && (
        <span style={{ fontSize: 8.5, color: "#1a2a2a", fontFamily: "'JetBrains Mono', monospace" }}>
          {sub}
        </span>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const [symbol, setSymbol] = useState<string | null>(null);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>

      {/* Status bar */}
      <BotStatusBar />

      {/* Symbol filter */}
      <SymbolFilter value={symbol} onChange={setSymbol} />

      {/* Main grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 18, alignItems: "start" }}>

        {/* Left: Agent feed */}
        <div>
          <SectionHeader title="Agent Orchestration" sub="live pipeline · polling 400ms" />
          <AgentFeed symbol={symbol} />
        </div>

        {/* Right: Commands + equity */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div>
            <SectionHeader title="Command Panel" />
            <CommandPanel />
          </div>
          <div>
            <SectionHeader title="Equity Curve" />
            <EquityCurve />
          </div>
        </div>
      </div>

      {/* Open trades */}
      <div>
        <SectionHeader title="Open Positions" />
        <OpenTradesTable symbol={symbol} />
      </div>

    </div>
  );
}
