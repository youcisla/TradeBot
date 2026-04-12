"use client";

import { useEffect, useState } from "react";
import { AgentBadge } from "@/components/ui/Badges";

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
    <div style={styles.wrapper}>
      <div style={styles.header}>
        <span style={styles.title}>Agent</span>
        <span style={styles.title}>Events (last 200)</span>
      </div>

      {AGENTS.map((agent) => (
        <div key={agent} style={styles.row}>
          <AgentBadge agent={agent} />
          <span style={styles.eventCount}>{counts[agent] ?? 0}</span>
        </div>
      ))}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    overflow: "hidden",
  },
  header: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    padding: "var(--space-3) var(--space-4)",
    borderBottom: "1px solid var(--border)",
    background: "var(--bg-3)",
    gap: "var(--space-3)",
  },
  title: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    fontWeight: 700,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  row: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    alignItems: "center",
    padding: "var(--space-3) var(--space-4)",
    borderBottom: "1px solid var(--border)",
    gap: "var(--space-3)",
  },
  eventCount: {
    fontFamily: "var(--font-mono)",
    fontSize: 13,
    fontWeight: 700,
    color: "var(--text-2)",
  },
};
