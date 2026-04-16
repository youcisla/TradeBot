"use client";

import { useEffect, useState } from "react";
import { AgentBadge } from "@/components/ui/Badges";
import { cn } from "@/lib/utils";

// All documented pipeline agents + support agents
const AGENTS = [
  "crucix", "market", "analysis", "strategy",
  "neural", "council", "risk", "execution",
  "trade_manager", "learning", "model_manager",
  "logging", "debate", "exposure", "memory",
  "hku", "tool_system",
];

interface AgentEvent {
  id?: string | number;
  agent: string;
  level: string;
  message?: string;
  msg?: string;
  created_at?: string;
}

export default function AgentsTab() {
  const [events, setEvents] = useState<AgentEvent[]>([]);

  useEffect(() => {
    fetch("/api/events?limit=200")
      .then((r) => r.json())
      .then((d: AgentEvent[]) => setEvents(Array.isArray(d) ? d : []))
      .catch(() => setEvents([]));
  }, []);

  // Count events per agent in the last 200 events
  const counts: Record<string, number> = {};
  for (const e of events) {
    counts[e.agent] = (counts[e.agent] ?? 0) + 1;
  }

  return (
    <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md overflow-hidden">
      <div className="grid grid-cols-2 gap-3 px-4 py-3 border-b border-[var(--border)] bg-[var(--bg-3)]">
        <span className="font-mono text-[9px] font-bold uppercase tracking-widest" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.06em" }}>
          Agent
        </span>
        <span className="font-mono text-[9px] font-bold uppercase tracking-widest" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.06em" }}>
          Events (last 200)
        </span>
      </div>

      {AGENTS.map((agent) => (
        <div key={agent} className="grid grid-cols-2 gap-3 px-4 py-3 border-b border-[var(--border)] items-center">
          <AgentBadge agent={agent} />
          <span className="font-mono text-sm font-bold" style={{ fontFamily: "var(--font-mono)", color: "var(--text-2)" }}>
            {counts[agent] ?? 0}
          </span>
        </div>
      ))}
    </div>
  );
}
