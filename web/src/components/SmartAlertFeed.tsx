"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import useSWR from "swr";
import { AgentEvent } from "@/lib/swr";

const fetcher = (url: string) => fetch(url).then((r) => r.json());

const AGENT_COLORS: Record<string, string> = {
  crucix: "#64D2FF", market: "#32ADE6", analysis: "#FFFFFF",
  strategy: "#16A34A", neural: "#9333EA", council: "#D97706",
  risk: "#DC2626", execution: "#6B7280", trade_manager: "#0EA5E9",
  learning: "#8B5CF6", logging: "#9CA3AF", model_manager: "#6366F1",
  debate: "#F59E0B", exposure: "#10B981", memory: "#14B8A6",
};

function agentColor(key: string): string {
  return AGENT_COLORS[key.toLowerCase()] ?? "#9CA3AF";
}

function fmtTime(ts: string | null | undefined): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleTimeString("en-US", {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
      hour12: false, timeZone: "Europe/Paris",
    });
  } catch { return "—"; }
}

type WsStatus = "connecting" | "connected" | "disconnected";

const WS_URL = typeof window !== "undefined"
  ? (process.env.NEXT_PUBLIC_WS_URL || "") : "";

function useWebSocket(onEvents: (ev: AgentEvent[]) => void) {
  const wsRef = useRef<WebSocket | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldReconnect = useRef(true);
  const [wsStatus, setWsStatus] = useState<WsStatus>("disconnected");

  const connect = useCallback(() => {
    if (!WS_URL) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;
    setWsStatus("connecting");
    const ws = new WebSocket(`${WS_URL}/ws/events`);
    wsRef.current = ws;
    ws.onopen = () => setWsStatus("connected");
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (Array.isArray(data.events)) {
          onEvents(data.events as AgentEvent[]);
        } else if (data.agent) {
          onEvents([data as AgentEvent]);
        }
      } catch { /* ignore */ }
    };
    ws.onclose = () => {
      setWsStatus("disconnected");
      if (shouldReconnect.current) {
        timerRef.current = setTimeout(connect, 5000) as unknown as ReturnType<typeof setTimeout>;
      }
    };
    ws.onerror = () => ws.close();
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

async function pollApi(limit: number): Promise<AgentEvent[]> {
  const res = await fetch(`/api/events?limit=${limit}`);
  if (!res.ok) return [];
  const raw: AgentEvent[] = await res.json();
  return raw.map((ev) => ({
    ...ev,
    message: ev.message ?? ev.msg ?? "",
  }));
}

type Level = "critical" | "error" | "warn" | "info";

function eventLevel(ev: AgentEvent): Level {
  const l = (ev.level ?? "info").toLowerCase();
  if (l === "critical") return "critical";
  if (l === "error") return "error";
  if (l === "warn" || l === "warning") return "warn";
  return "info";
}

interface Props {
  /** Height of the alert strip when collapsed and quiet (no critical/warn). */
  collapsedHeight?: number;
  maxEvents?: number;
}

export default function SmartAlertFeed({
  collapsedHeight = 44,
  maxEvents = 40,
}: Props) {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [wsStatus, setWsStatus] = useState<WsStatus>("disconnected");
  const [expanded, setExpanded] = useState(false);
  const lastCriticalRef = useRef<number | string | undefined>(undefined);
  const pollingTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Merge incoming events ────────────────────────────────────────────────
  const handleEvents = useCallback((incoming: AgentEvent[]) => {
    setEvents((prev) => {
      const existing = new Set(prev.map((e) => e.id));
      const newItems = incoming.filter((e) => !existing.has(e.id));
      if (!newItems.length) return prev;

      const next = [...newItems, ...prev].slice(0, maxEvents);

      // Auto-expand when a new critical/error arrives
      const hasNewCritical = newItems.some(
        (e) => eventLevel(e) === "critical" || eventLevel(e) === "error",
      );
      if (hasNewCritical) {
        const topId = next[0]?.id;
        if (topId !== lastCriticalRef.current) {
          lastCriticalRef.current = topId;
          setExpanded(true);
        }
      }
      return next;
    });
  }, [maxEvents]);

  const status = useWebSocket(handleEvents);

  useEffect(() => { setWsStatus(status); }, [status]);

  // ── Polling fallback ────────────────────────────────────────────────────
  useEffect(() => {
    if (wsStatus !== "disconnected") return;
    pollApi(maxEvents).then((fresh) => {
      handleEvents(fresh);
    });
    pollingTimerRef.current = setInterval(async () => {
      handleEvents(await pollApi(maxEvents));
    }, 8_000);
    return () => {
      if (pollingTimerRef.current) clearInterval(pollingTimerRef.current);
    };
  }, [wsStatus, maxEvents, handleEvents]);

  // ── Classification ────────────────────────────────────────────────────────
  const errors   = events.filter((e) => eventLevel(e) === "critical" || eventLevel(e) === "error");
  const warns    = events.filter((e) => eventLevel(e) === "warn");
  const infos    = events.filter((e) => eventLevel(e) === "info");

  const hasAlerts = errors.length > 0 || warns.length > 0;
  const isLive = wsStatus === "connected";

  const alertCount = errors.length + warns.length;
  const lastAlertTime = events.find(
    (e) => eventLevel(e) !== "info",
  )?.created_at;

  return (
    <div style={{
      background: hasAlerts
        ? "linear-gradient(180deg, rgba(19,24,32,0.97) 0%, rgba(12,15,20,0.99) 100%)"
        : "#1C1C1E",
      borderRadius: 10,
      border: `1px solid ${hasAlerts ? "rgba(220,38,38,0.4)" : "rgba(95,122,158,0.28)"}`,
      overflow: "hidden",
      display: "flex",
      flexDirection: "column",
      fontFamily: "'IBM Plex Mono', monospace",
      transition: "border-color 0.4s ease",
    }}>
      {/* ── Header ── */}
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "10px 14px",
        borderBottom: "1px solid rgba(95,122,158,0.2)",
        flexShrink: 0,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {hasAlerts ? (
            <span style={{
              width: 8, height: 8, borderRadius: "50%",
              background: "#DC2626", display: "inline-block",
              animation: "smartAlertPulse 1.5s ease-in-out infinite",
              boxShadow: "0 0 6px rgba(220,38,38,0.6)",
            }} />
          ) : (
            <span style={{
              width: 8, height: 8, borderRadius: "50%",
              background: isLive ? "#16A34A" : "#E5A200",
              display: "inline-block",
              boxShadow: isLive ? "0 0 6px rgba(22,163,74,0.5)" : undefined,
              animation: isLive ? "smartAlertPulse 2s ease-in-out infinite" : undefined,
            }} />
          )}
          <span style={{ fontSize: 12, fontWeight: 700, color: "#EFF5FF" }}>
            {hasAlerts
              ? `${alertCount} Alert${alertCount > 1 ? "s" : ""}`
              : "Agent Feed"}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          {lastAlertTime && (
            <span style={{ fontSize: 10, color: "#9CA3AF" }}>
              {fmtTime(lastAlertTime)}
            </span>
          )}
          <button
            onClick={() => setExpanded((v) => !v)}
            style={{
              background: "none", border: "1px solid rgba(95,122,158,0.4)",
              borderRadius: 4, padding: "2px 8px",
              fontSize: 10, color: "#9CA3AF", cursor: "pointer",
              fontFamily: "'IBM Plex Mono', monospace",
            }}
          >
            {expanded ? "Collapse" : `+${infos.length} info`}
          </button>
        </div>
      </div>

      <style>{`
        @keyframes smartAlertPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>

      {/* ── Critical / Error events ── */}
      {errors.map((ev) => (
        <EventRow key={ev.id} ev={ev} variant="error" />
      ))}

      {/* ── Warning events ── */}
      {warns.slice(0, 5).map((ev) => (
        <EventRow key={ev.id} ev={ev} variant="warn" />
      ))}

      {/* ── Info events (collapsed) ── */}
      {expanded && infos.slice(0, 10).map((ev) => (
        <EventRow key={ev.id} ev={ev} variant="info" />
      ))}
    </div>
  );
}

function EventRow({ ev, variant }: { ev: AgentEvent; variant: "error" | "warn" | "info" }) {
  const bg = variant === "error"
    ? "rgba(220,38,38,0.08)"
    : variant === "warn"
    ? "rgba(217,119,6,0.06)"
    : "transparent";

  const textColor = variant === "error"
    ? "#FCA5A5"
    : variant === "warn"
    ? "#FCD34D"
    : "rgba(229,239,253,0.55)";

  const accentColor = variant === "error" ? "#DC2626" : "#D97706";

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8,
      padding: "6px 14px",
      background: bg,
      borderBottom: "0.5px solid rgba(84,84,88,0.2)",
    }}>
      <span style={{
        width: 6, height: 6, borderRadius: "50%",
        background: agentColor(ev.agent),
        display: "inline-block", flexShrink: 0,
      }} />
      <span style={{
        fontSize: 9, fontWeight: 700,
        color: agentColor(ev.agent),
        background: `${agentColor(ev.agent)}18`,
        borderRadius: 3, padding: "1px 5px",
        flexShrink: 0, textTransform: "uppercase", letterSpacing: "0.04em",
      }}>
        {ev.agent}
      </span>
      <span style={{
        flex: 1, fontSize: 11, color: textColor,
        overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
      }}>
        {String(ev.message ?? ev.msg ?? "").slice(0, 80)}
      </span>
      <span style={{ fontSize: 10, color: "#9CA3AF", flexShrink: 0 }}>
        {fmtTime(ev.created_at ?? ev.ts)}
      </span>
    </div>
  );
}
