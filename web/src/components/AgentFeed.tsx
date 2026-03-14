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
  const [copied, setCopied] = useState(false);
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

  const copyLog = () => {
    const text = filtered
      .map((e) => `${formatTime(e.created_at)} [${e.agent}] ${e.message}`)
      .join("\n");
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="border border-terminal-border rounded bg-terminal-surface flex flex-col h-[420px]">
      <div className="px-3 py-2 border-b border-terminal-border flex items-center justify-between">
        <span className="text-matrix-dim text-xs uppercase tracking-widest">
          Agent Feed
        </span>
        <button
          onClick={copyLog}
          title="Copy log to clipboard"
          className="text-matrix-dim hover:text-matrix transition-colors p-1"
        >
          {copied ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
          )}
        </button>
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
