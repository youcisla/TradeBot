"use client";

import { useAppShell } from "@/components/AppShell";
import { AgentBadge } from "@/components/ui/Badges";

// Known agents from the pipeline
const AGENTS = [
  "crucix", "market", "analysis", "strategy",
  "neural", "council", "risk", "execution",
  "manager", "learning", "logging",
];

export default function AgentsTab() {
  const { wsEvents } = useAppShell();

  // Count events per agent in the last 100 events
  const counts: Record<string, number> = {};
  for (const e of wsEvents.slice(0, 100)) {
    counts[e.agent] = (counts[e.agent] ?? 0) + 1;
  }

  return (
    <div style={styles.wrapper}>
      <div style={styles.header}>
        <span style={styles.title}>Agent</span>
        <span style={styles.title}>Events (last 100)</span>
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
