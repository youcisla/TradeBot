"use client";

import { useEffect, useRef, useState } from "react";
import useSWR from "swr";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgentEvent {
  id?: number;
  agent: string;
  level: string;
  message?: string;
  msg?: string;
  created_at?: string;
  ts?: string;
  data?: Record<string, unknown>;
}

interface NormEvent {
  id?: number;
  agent: string;
  level: string;
  msg: string;
  ts: string | null;
}

// ── Agent color map ───────────────────────────────────────────────────────────

const AGENT_COLORS: Record<string, string> = {
  crucix:        "#64D2FF",
  market:        "#32ADE6",
  analysis:      "#FFFFFF",
  strategy:      "#30D158",
  neural:        "#BF5AF2",
  council:       "#FF9F0A",
  risk:          "#FF453A",
  execution:     "#FFFFFF",
  trade_manager: "#63E6E2",
  learning:      "#64D2FF",
  logging:       "#636366",
  model_manager: "#5E5CE6",
};

function agentColor(key: string): string {
  return AGENT_COLORS[key.toLowerCase()] ?? "#8E8E93";
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtTime(ts: string | null): string {
  if (!ts) return "--:--:--";
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString("en-US", {
      hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false,
    });
  } catch { return "--:--:--"; }
}

function levelBg(level: string): string {
  const l = level.toLowerCase();
  if (l === "error" || l === "critical") return "rgba(255,69,58,0.08)";
  if (l === "warn"  || l === "warning")  return "rgba(255,159,10,0.06)";
  return "transparent";
}

// ── Keyframes ─────────────────────────────────────────────────────────────────

const KEYFRAMES = `
  @keyframes feedPulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(48,209,88,0.5); }
    50%       { opacity: 0.6; box-shadow: 0 0 0 5px rgba(48,209,88,0); }
  }
`;

// ── Component ─────────────────────────────────────────────────────────────────

const fetcher = (url: string) => fetch(url).then(r => r.json());

export default function AgentFeed({
  limit       = 40,
  showHeader  = true,
}: {
  limit?:      number;
  showHeader?: boolean;
}) {
  const { data: rawEvents } = useSWR<AgentEvent[]>(
    `/api/events?limit=${limit}`,
    fetcher,
    { refreshInterval: 5_000, revalidateOnFocus: true, keepPreviousData: true }
  );

  const [events, setEvents] = useState<NormEvent[]>([]);
  const scrollRef           = useRef<HTMLDivElement>(null);
  const prevTopId           = useRef<number | string | undefined>(undefined);

  useEffect(() => {
    if (!rawEvents) return;
    const norm: NormEvent[] = rawEvents.map((ev) => ({
      id:    ev.id,
      agent: (ev.agent ?? "unknown").toLowerCase(),
      level: (ev.level ?? "info").toLowerCase(),
      msg:   String(ev.msg ?? ev.message ?? ""),
      ts:    String(ev.ts ?? ev.created_at ?? "") || null,
    }));
    setEvents(norm);
  }, [rawEvents]);

  // Scroll to top when new events arrive
  useEffect(() => {
    if (events.length === 0) return;
    const topId = events[0]?.id ?? undefined;
    if (topId !== prevTopId.current) {
      prevTopId.current = topId;
      if (scrollRef.current) scrollRef.current.scrollTop = 0;
    }
  }, [events]);

  return (
    <div style={{
      background: "linear-gradient(180deg, rgba(19,24,32,0.92) 0%, rgba(12,15,20,0.96) 100%)",
      borderRadius: 14,
      border: "1px solid rgba(95,122,158,0.32)",
      overflow:      "hidden",
      display:       "flex",
      flexDirection: "column",
      height:        "100%",
      minHeight:     500,
      boxShadow: "0 20px 34px rgba(0,0,0,0.35)",
      fontFamily:    '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif',
    }}>
      <style>{KEYFRAMES}</style>

      {/* ── Header ── */}
      {showHeader && (
        <div style={{
          display:        "flex",
          alignItems:     "center",
          justifyContent: "space-between",
          padding:        "14px 16px 12px",
          borderBottom:   "1px solid rgba(95,122,158,0.28)",
          flexShrink:     0,
        }}>
          <span style={{ fontSize: 15, fontWeight: 700, color: "#eff5ff" }}>
            Agent Feed
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{
              width:        8,
              height:       8,
              borderRadius: "50%",
              background:   "#66f6a5",
              display:      "inline-block",
              animation:    "feedPulse 2s ease-in-out infinite",
              flexShrink:   0,
            }} />
            <span style={{ fontSize: 12, color: "#66f6a5", fontWeight: 600 }}>Live</span>
          </div>
        </div>
      )}

      {/* ── Event list ── */}
      <div
        ref={scrollRef}
        style={{
          flex:       1,
          overflowY:  "auto",
          overflowX:  "hidden",
          scrollbarWidth: "thin",
          scrollbarColor: "rgba(84,84,88,0.4) transparent",
        }}
      >
        {events.length === 0 ? (
          <div style={{
            display:    "flex",
            alignItems: "center",
            justifyContent: "center",
            height:     120,
            fontSize:   14,
            color:      "rgba(235,235,245,0.3)",
          }}>
            No events yet
          </div>
        ) : (
          events.map((ev, i) => {
            const color    = agentColor(ev.agent);
            const isLast   = i === events.length - 1;

            return (
              <div
                key={ev.id ?? `${ev.ts}-${i}`}
                style={{
                  display:       "flex",
                  alignItems:    "center",
                  gap:           10,
                  minHeight:     44,
                  padding:       "8px 16px",
                  background:    levelBg(ev.level),
                  borderBottom:  isLast ? "none" : "0.5px solid rgba(84,84,88,0.3)",
                  boxSizing:     "border-box",
                }}
              >
                {/* Colored dot */}
                <span style={{
                  width:        8,
                  height:       8,
                  borderRadius: "50%",
                  background:   color,
                  display:      "inline-block",
                  flexShrink:   0,
                }} />

                {/* Agent badge */}
                <span style={{
                  fontSize:     11,
                  fontWeight:   600,
                  color:        color,
                  background:   `${color}18`,
                  borderRadius: 4,
                  padding:      "2px 6px",
                  flexShrink:   0,
                  letterSpacing: 0.1,
                }}>
                  {ev.agent}
                </span>

                {/* Message */}
                <span style={{
                  fontSize:     13,
                  color:        ev.level === "error" || ev.level === "critical"
                    ? "#FF453A"
                    : ev.level === "warn" || ev.level === "warning"
                    ? "#FF9F0A"
                    : "rgba(229,239,253,0.86)",
                  flex:         1,
                  overflow:     "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace:   "nowrap",
                }}>
                  {ev.msg}
                </span>

                {/* Timestamp */}
                <span style={{
                  fontSize:   11,
                  color:      "rgba(235,235,245,0.35)",
                  flexShrink: 0,
                  fontFamily: '"SF Mono", SFMono-Regular, ui-monospace, Menlo, monospace',
                  letterSpacing: 0.2,
                }}>
                  {fmtTime(ev.ts)}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
