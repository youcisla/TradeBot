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
    <>
      <div
        className="flex items-center gap-2 px-2 py-1.5 border-b border-[var(--border)] cursor-pointer font-mono text-sm flex-wrap"
        style={{ fontFamily: "var(--font-mono)" }}
        onClick={onToggle}
      >
        <span className="text-[var(--text-3)] w-14 flex-shrink-0" style={{ fontFamily: "var(--font-mono)" }}>
          {ts ? relTime(ts) : "—"}
        </span>
        <AgentBadge agent={event.agent} />
        <LevelBadge level={event.level} />
        <span className="text-[var(--text-2)] flex-1 overflow-hidden text-ellipsis whitespace-nowrap">
          {msg}
        </span>
        {event.data && (
          <button
            className="bg-none border-none text-[var(--text-3)] cursor-pointer px-1 text-[10px] flex-shrink-0"
            style={{ background: "none", border: "none", color: "var(--text-3)", cursor: "pointer", padding: "0 4px", fontSize: 10 }}
            onClick={(e) => { e.stopPropagation(); onToggle?.(); }}
          >
            {expanded ? "▸" : "▾"}
          </button>
        )}
      </div>
      {expanded && event.data && (
        <pre
          className="w-full text-[10px] overflow-auto"
          style={{
            background: "var(--bg-3)",
            border: "1px solid var(--border)",
            borderRadius: "var(--radius-sm)",
            padding: "var(--space-2)",
            color: "var(--text-2)",
            maxHeight: 120,
            marginTop: "var(--space-1)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {JSON.stringify(event.data, null, 2)}
        </pre>
      )}
    </>
  );
}
