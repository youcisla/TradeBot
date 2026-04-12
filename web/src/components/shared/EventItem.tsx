"use client";

import { AgentBadge } from "@/components/ui/Badges";
import { LevelBadge } from "@/components/ui/Badges";
import { relTime } from "@/lib/format";
import type { AgentEvent } from "@/lib/swr";

interface EventItemProps {
  event: AgentEvent;
  expanded?: boolean;
  onToggle?: () => void;
}

export default function EventItem({ event, expanded, onToggle }: EventItemProps) {
  const msg = event.message ?? event.msg ?? "—";
  const ts  = event.created_at ?? event.ts ?? null;

  return (
    <div style={styles.row} onClick={onToggle}>
      <span style={styles.ts}>{ts ? relTime(ts) : "—"}</span>
      <AgentBadge agent={event.agent} />
      <LevelBadge level={event.level} />
      <span style={styles.msg}>{msg}</span>
      {event.data && (
        <button style={styles.expandBtn} onClick={(e) => { e.stopPropagation(); onToggle?.(); }}>
          {expanded ? "▸" : "▾"}
        </button>
      )}
      {expanded && event.data && (
        <pre style={styles.data}>
          {JSON.stringify(event.data, null, 2)}
        </pre>
      )}
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  row: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-2)",
    padding: "6px var(--space-2)",
    borderBottom: "1px solid var(--border)",
    cursor: "pointer",
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    flexWrap: "wrap",
  },
  ts: {
    color: "var(--text-3)",
    width: 56,
    flexShrink: 0,
  },
  msg: {
    color: "var(--text-2)",
    flex: 1,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  expandBtn: {
    background: "none",
    border: "none",
    color: "var(--text-3)",
    cursor: "pointer",
    padding: "0 4px",
    fontSize: 10,
    flexShrink: 0,
  },
  data: {
    width: "100%",
    background: "var(--bg-3)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    padding: "var(--space-2)",
    fontSize: 10,
    color: "var(--text-2)",
    overflow: "auto",
    maxHeight: 120,
    marginTop: "var(--space-1)",
  },
};
