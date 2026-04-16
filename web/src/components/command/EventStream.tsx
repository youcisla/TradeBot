"use client";

import { useState } from "react";
import { useAppShell } from "@/components/AppShell";
import EventItem from "@/components/shared/EventItem";
import type { AgentEvent } from "@/lib/swr";
import { cn } from "@/lib/utils";

const LEVELS = ["all", "info", "warn", "error"];

export default function EventStream() {
  const { wsEvents } = useAppShell();
  const [filter, setFilter] = useState("all");
  const [expanded, setExpanded] = useState<number | null>(null);

  const filtered = wsEvents.filter(
    (e: AgentEvent) => filter === "all" || e.level === filter
  );

  return (
    <div className="bg-[var(--bg-2)] border border-[var(--border)] rounded-md overflow-hidden flex flex-col" style={{ height: 400 }}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] flex-shrink-0">
        <span className="text-xs font-bold uppercase tracking-widest" style={{ fontFamily: "var(--font-ui)", color: "var(--text-2)", letterSpacing: "0.08em" }}>
          Live Events
        </span>
        <div className="flex gap-1">
          {LEVELS.map((l) => (
            <button
              key={l}
              className={cn(
                "rounded px-1.5 py-0.5 text-[9px] font-mono font-bold uppercase tracking-wider cursor-pointer transition-all border",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent)]",
                filter === l
                  ? "bg-[var(--bg-3)] border-[var(--border-active)] text-[var(--text-1)]"
                  : "bg-transparent border-[var(--border)] text-[var(--text-3)]"
              )}
              onClick={() => setFilter(l)}
            >
              {l}
            </button>
          ))}
        </div>
      </div>

      {/* Event list */}
      <div className="overflow-y-auto flex-1">
        {filtered.length === 0 ? (
          <p className="font-mono text-sm text-center py-5" style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)" }}>
            No events
          </p>
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
