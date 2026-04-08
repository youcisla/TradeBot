"use client";

import { useEffect, useRef, useState, useCallback } from "react";

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
  event_type?: string;   // from ws-server pg_notify
}

interface NormEvent {
  id?: number;
  agent: string;
  level: string;
  msg: string;
  ts: string | null;
}

// ── Config ────────────────────────────────────────────────────────────────────

/** WebSocket URL — set NEXT_PUBLIC_WS_URL env var to enable real-time push.
 *  Example: ws://localhost:3001  (ws-server.js must be running)
 *  When unset or unreachable, falls back to /api/events polling. */
const WS_URL =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_WS_URL || "")
    : "";

const POLL_INTERVAL_MS = 5_000;

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

function normalizeWsEvent(raw: AgentEvent): NormEvent | null {
  // WebSocket events from pg_notify have event_type at top level
  if (raw.event_type) {
    return {
      id:    raw.id,
      agent: (raw.agent ?? "unknown").toLowerCase(),
      level: (raw.level ?? "info").toLowerCase(),
      msg:   raw.msg ?? raw.message ?? `[${raw.event_type}]`,
      ts:    raw.ts ?? raw.created_at ?? null,
    };
  }
  // API response shape
  if (raw.agent !== undefined) {
    return {
      id:    raw.id,
      agent: (raw.agent ?? "unknown").toLowerCase(),
      level: (raw.level ?? "info").toLowerCase(),
      msg:   String(raw.msg ?? raw.message ?? ""),
      ts:    String(raw.ts ?? raw.created_at ?? "") || null,
    };
  }
  return null;
}

// ── WebSocket hook ───────────────────────────────────────────────────────────

type WsStatus = "connecting" | "connected" | "disconnected";

function useWebSocket(onEvents: (events: NormEvent[]) => void) {
  const wsRef        = useRef<WebSocket | null>(null);
  const timerRef     = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnect = useRef(true);
  const [wsStatus, setWsStatus] = useState<WsStatus>("disconnected");

  const connect = useCallback(() => {
    if (!WS_URL) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setWsStatus("connecting");
    const ws = new WebSocket(`${WS_URL}/ws/events`);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus("connected");
      console.log("[AgentFeed] WebSocket connected");
    };

    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        // 'events' array from polling fallback
        if (Array.isArray(data.events)) {
          const norm = data.events
            .map(normalizeWsEvent)
            .filter(Boolean) as NormEvent[];
          if (norm.length) onEvents(norm);
        }
        // Single event from pg_notify
        else if (data.event_type || data.agent) {
          const norm = normalizeWsEvent(data as AgentEvent);
          if (norm) onEvents([norm]);
        }
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      setWsStatus("disconnected");
      if (shouldReconnect.current) {
        // Exponential backoff: 1s, 2s, 4s, max 30s
        const delay = Math.min(
          (Number(timerRef.current) || 1000) * 2,
          30_000
        );
        timerRef.current = setTimeout(connect, delay) as unknown as ReturnType<typeof setTimeout>;
      }
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [onEvents]);

  useEffect(() => {
    if (!WS_URL) return;
    shouldReconnect.current = true;
    connect();
    return () => {
      shouldReconnect.current = false;
      if (timerRef.current) clearTimeout(timerRef.current as unknown as number);
      wsRef.current?.close();
    };
  }, [connect]);

  return wsStatus;
}

// ── Polling fallback ─────────────────────────────────────────────────────────

async function pollApi(limit: number): Promise<NormEvent[]> {
  const res = await fetch(`/api/events?limit=${limit}`);
  if (!res.ok) return [];
  const raw: AgentEvent[] = await res.json();
  return raw
    .map((ev) => ({
      id:    ev.id,
      agent: (ev.agent ?? "unknown").toLowerCase(),
      level: (ev.level ?? "info").toLowerCase(),
      msg:   String(ev.msg ?? ev.message ?? ""),
      ts:    String(ev.ts ?? ev.created_at ?? "") || null,
    }))
    .filter((ev) => ev.msg.length > 0);
}

// ── Keyframes ─────────────────────────────────────────────────────────────────

const KEYFRAMES = `
  @keyframes feedPulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(48,209,88,0.5); }
    50%       { opacity: 0.6; box-shadow: 0 0 0 5px rgba(48,209,88,0); }
  }
  @keyframes wsPulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.4; }
  }
`;

// ── Component ─────────────────────────────────────────────────────────────────

export default function AgentFeed({
  limit       = 40,
  showHeader  = true,
}: {
  limit?:      number;
  showHeader?: boolean;
}) {
  const [events, setEvents]         = useState<NormEvent[]>([]);
  const [wsStatus, setWsStatus]     = useState<WsStatus>("disconnected");
  const scrollRef                   = useRef<HTMLDivElement>(null);
  const prevTopId                   = useRef<number | string | undefined>(undefined);
  const pollingTimerRef              = useRef<ReturnType<typeof setInterval> | null>(null);
  const isLocalManualScroll          = useRef(false);

  // ── Merge new events from WebSocket ──────────────────────────────────────────
  const handleWsEvents = useCallback((incoming: NormEvent[]) => {
    setEvents((prev) => {
      const existingIds = new Set(prev.map((e) => e.id));
      const newEvents = incoming.filter((e) => !existingIds.has(e.id));
      if (!newEvents.length) return prev;
      return [...newEvents, ...prev].slice(0, limit);
    });
  }, [limit]);

  // ── WebSocket connection ────────────────────────────────────────────────────
  const status = useWebSocket(handleWsEvents);

  // Sync wsStatus to local state (hook return is captured in closure)
  useEffect(() => { setWsStatus(status); }, [status]);

  // ── Polling fallback (when WS is unavailable) ──────────────────────────────
  useEffect(() => {
    if (wsStatus !== "disconnected") return; // WS active — no polling needed

    // Initial fetch
    pollApi(limit).then((fresh) => {
      setEvents((prev) => {
        const existingIds = new Set(prev.map((e) => e.id));
        const newEvents = fresh.filter((e) => !existingIds.has(e.id));
        return newEvents.length ? [...newEvents, ...prev].slice(0, limit) : prev;
      });
    });

    // Periodic poll
    pollingTimerRef.current = setInterval(async () => {
      const fresh = await pollApi(limit);
      setEvents((prev) => {
        const existingIds = new Set(prev.map((e) => e.id));
        const newEvents = fresh.filter((e) => !existingIds.has(e.id));
        return newEvents.length ? [...newEvents, ...prev].slice(0, limit) : prev;
      });
    }, POLL_INTERVAL_MS);

    return () => {
      if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);
    };
  }, [wsStatus, limit]);

  // ── Auto-scroll to top when new events arrive ──────────────────────────────
  useEffect(() => {
    if (events.length === 0) return;
    const topId = events[0]?.id ?? undefined;
    if (topId !== prevTopId.current) {
      prevTopId.current = topId;
      if (!isLocalManualScroll.current && scrollRef.current) {
        scrollRef.current.scrollTop = 0;
      }
    }
  }, [events]);

  const isLive = wsStatus === "connected";

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
              background:   isLive ? "#66f6a5" : "#e5a200",
              display:      "inline-block",
              animation:    isLive ? "feedPulse 2s ease-in-out infinite" : "wsPulse 1.5s ease-in-out infinite",
              flexShrink:   0,
            }} />
            <span style={{
              fontSize: 12,
              color:    isLive ? "#66f6a5" : "#e5a200",
              fontWeight: 600,
            }}>
              {isLive ? "Live" : wsStatus === "connecting" ? "Connecting…" : "Poll"}
            </span>
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
        onScroll={() => {
          if (!scrollRef.current) return;
          // Detect manual scroll (user scrolled away from top)
          isLocalManualScroll.current = scrollRef.current.scrollTop > 20;
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
