"use client";

import { useRef, useEffect } from "react";
import type { AgentEvent } from "@/types/api";
import { AgentBadge } from "@/components/shared/AgentBadge";
import { LevelBadge } from "@/components/shared/LevelBadge";

interface EventFeedProps {
  events: AgentEvent[];
  /** Auto-scroll to newest event (new events prepend at top) */
  autoScroll?: boolean;
  /** Max height — scrolls internally */
  maxHeight?: string;
  /** Called when user clicks an event row */
  onEventClick?: (event: AgentEvent) => void;
  /** Show only events from this agent */
  filterAgent?: string;
  /** Placeholder when no events */
  emptyMessage?: string;
}

/**
 * Scrollable live event feed.
 * New events prepend at the top; auto-scrolls to show newest.
 */
export function EventFeed({
  events,
  autoScroll = true,
  maxHeight = "400px",
  onEventClick,
  filterAgent,
  emptyMessage = "No events recorded",
}: EventFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const userScrolledRef = useRef(false);

  const filtered = filterAgent
    ? events.filter((e) => e.agent.toLowerCase() === filterAgent.toLowerCase())
    : events;

  // Auto-scroll to top when new events arrive (prepend = newest at index 0)
  useEffect(() => {
    if (autoScroll && !userScrolledRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [events.length, autoScroll]);

  function handleScroll() {
    if (!scrollRef.current) return;
    // If user scrolled down (away from top), stop auto-scroll
    userScrolledRef.current = scrollRef.current.scrollTop > 60;
  }

  return (
    <div
      className="flex flex-col rounded overflow-hidden"
      style={{
        background: "var(--bg-2)",
        border: "1px solid var(--border)",
        height: maxHeight,
      }}
    >
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto py-1"
        onScroll={handleScroll}
        style={{ scrollBehavior: "auto" }}
      >
        {filtered.length === 0 ? (
          <div
            className="flex items-center justify-center h-full"
            style={{ color: "var(--text-3)", fontFamily: "var(--font-ui)", fontSize: 12 }}
          >
            {emptyMessage}
          </div>
        ) : (
          filtered.map((ev, i) => {
            const ts = ev.created_at ?? ev.ts ?? "";
            const timeStr = ts
              ? new Date(ts).toLocaleTimeString("en-US", {
                  hour12: false,
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                })
              : "—";

            const msg = ev.message ?? ev.msg ?? "";
            const level = (ev.level ?? "info").toLowerCase() as AgentEvent["level"];

            return (
              <div
                key={`${ev.id ?? i}-${ts}`}
                className="flex items-start gap-3 px-3 py-1.5 cursor-pointer transition-colors group"
                style={{
                  borderBottom: "1px solid var(--border-subtle)",
                  background: "transparent",
                }}
                onClick={() => onEventClick?.(ev)}
                onMouseEnter={(e) =>
                  ((e.currentTarget as HTMLElement).style.background = "var(--bg-3)")
                }
                onMouseLeave={(e) =>
                  ((e.currentTarget as HTMLElement).style.background = "transparent")
                }
              >
                {/* Timestamp */}
                <span
                  className="font-mono flex-shrink-0 tabular-nums"
                  style={{
                    color: "var(--text-3)",
                    fontFamily: "var(--font-mono)",
                    fontSize: 10,
                    minWidth: 52,
                  }}
                >
                  {timeStr}
                </span>

                {/* Agent badge */}
                <span className="flex-shrink-0">
                  <AgentBadge agent={ev.agent} />
                </span>

                {/* Level */}
                <span className="flex-shrink-0">
                  <LevelBadge level={level} />
                </span>

                {/* Message */}
                <span
                  className="flex-1 leading-snug"
                  style={{
                    color: "var(--text-2)",
                    fontFamily: "var(--font-ui)",
                    fontSize: 12,
                    transition: "color 0.1s",
                  }}
                  onMouseEnter={(e) =>
                    ((e.currentTarget as HTMLElement).style.color = "var(--text-1)")
                  }
                  onMouseLeave={(e) =>
                    ((e.currentTarget as HTMLElement).style.color = "var(--text-2)")
                  }
                >
                  {msg}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
