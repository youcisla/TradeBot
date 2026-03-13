"use client";

import { useEffect, useRef, useState } from "react";
import { formatTime } from "@/lib/time";

interface AgentEvent {
  id: number;
  agent: string;
  level: string;
  message: string;
  created_at: string;
}

const AGENT_CLASS: Record<string, string> = {
  market: "agent-market",
  analysis: "agent-analysis",
  strategy: "agent-strategy",
  risk: "agent-risk",
  execution: "agent-execution",
  trade_manager: "agent-trade_manager",
  learning: "agent-learning",
  logging: "agent-logging",
};

export default function AgentFeed({ symbol }: { symbol?: string | null }) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    const load = () =>
      fetch("/api/events?limit=80")
        .then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
        .then((data: AgentEvent[]) => { if (active) setEvents(data.reverse()); })
        .catch(() => {});
    load();
    const id = setInterval(load, 10_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const filtered = symbol
    ? events.filter((e) => e.message.includes(symbol))
    : events;

  return (
    <div className="border border-terminal-border rounded bg-terminal-surface flex flex-col h-[420px]">
      <div className="px-3 py-2 border-b border-terminal-border text-matrix-dim text-xs uppercase tracking-widest">
        Agent Feed
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-1 text-xs leading-relaxed">
        {filtered.map((e) => (
          <div key={e.id} className="flex gap-2">
            <span className="text-matrix-dim shrink-0">{formatTime(e.created_at)}</span>
            <span
              className={`shrink-0 font-bold uppercase w-[110px] ${AGENT_CLASS[e.agent] ?? "text-gray-500"}`}
            >
              [{e.agent}]
            </span>
            <span
              className={
                e.level === "error"
                  ? "text-red-500"
                  : e.level === "warn"
                    ? "text-yellow-400"
                    : "text-gray-300"
              }
            >
              {e.message}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
