"use client";

import { useState } from "react";
import { useAppShell } from "@/components/AppShell";
import EventItem from "@/components/shared/EventItem";
import type { AgentEvent } from "@/lib/swr";

const LEVELS = ["all", "info", "warn", "error"];

export default function EventStream() {
  const { wsEvents } = useAppShell();
  const [filter, setFilter] = useState("all");
  const [expanded, setExpanded] = useState<number | null>(null);

  const filtered = wsEvents.filter(
    (e: AgentEvent) => filter === "all" || e.level === filter
  );

  return (
    <div style={styles.wrapper}>
      {/* Header */}
      <div style={styles.header}>
        <span style={styles.title}>Live Events</span>
        <div style={styles.filters}>
          {LEVELS.map((l) => (
            <button
              key={l}
              style={{
                ...styles.filterBtn,
                ...(filter === l ? styles.filterBtnActive : {}),
              }}
              onClick={() => setFilter(l)}
            >
              {l.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* Event list */}
      <div style={styles.list}>
        {filtered.length === 0 ? (
          <p style={styles.empty}>No events</p>
        ) : (
          filtered.slice(0, 50).map((event: AgentEvent, i: number) => (
            <EventItem
              key={event.id ?? i}
              event={event}
              expanded={expanded === i}
              onToggle={() => setExpanded(expanded === i ? null : i)}
            />
          ))
        )}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    overflow: "hidden",
    display: "flex",
    flexDirection: "column",
    height: 400,
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "var(--space-3) var(--space-4)",
    borderBottom: "1px solid var(--border)",
    flexShrink: 0,
  },
  title: {
    fontFamily: "var(--font-ui)",
    fontSize: 11,
    fontWeight: 700,
    color: "var(--text-2)",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  filters: {
    display: "flex",
    gap: "var(--space-1)",
  },
  filterBtn: {
    background: "none",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-sm)",
    color: "var(--text-3)",
    cursor: "pointer",
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    padding: "2px 6px",
    letterSpacing: "0.05em",
  },
  filterBtnActive: {
    background: "var(--bg-3)",
    border: "1px solid var(--border-active)",
    color: "var(--text-1)",
  },
  list: {
    overflowY: "auto",
    flex: 1,
  },
  empty: {
    fontFamily: "var(--font-mono)",
    fontSize: 11,
    color: "var(--text-3)",
    textAlign: "center",
    padding: "var(--space-5)",
  },
};
