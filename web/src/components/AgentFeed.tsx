"use client";

import { useEffect, useRef, useState } from "react";
import { formatTime } from "@/lib/time";

interface AgentEvent {
  id?: number;
  agent: string;
  level: string;
  message?: string;
  msg?: string;
  created_at?: string;
  ts?: string;
}

interface NormEvent {
  id?: number;
  agent: string;
  level: string;
  msg: string;
  ts: string | null;
}

// Pipeline agents in execution order
const PIPELINE: { key: string; label: string; color: string }[] = [
  { key: "market",        label: "Market",   color: "#06b6d4" },
  { key: "analysis",      label: "Analysis", color: "#eab308" },
  { key: "strategy",      label: "Strategy", color: "#22c55e" },
  { key: "risk",          label: "Risk",     color: "#f97316" },
  { key: "execution",     label: "Exec",     color: "#e5e5e5" },
  { key: "trade_manager", label: "TradeMgr", color: "#d946ef" },
];

// Support agents (cross-cutting)
const SUPPORT: { key: string; label: string; color: string }[] = [
  { key: "learning", label: "Learning", color: "#3b82f6" },
  { key: "logging",  label: "Logging",  color: "#6b7280" },
];

const ALL_AGENTS = [...PIPELINE, ...SUPPORT];

// 6×8 pixel art robot sprite (each cell = 4px → 24×32 SVG)
const SPRITE: number[][] = [
  [0, 0, 1, 1, 0, 0],
  [0, 1, 1, 1, 1, 0],
  [1, 1, 0, 0, 1, 1],
  [0, 1, 1, 1, 1, 0],
  [0, 0, 1, 1, 0, 0],
  [0, 1, 1, 1, 1, 0],
  [0, 1, 0, 0, 1, 0],
  [1, 1, 0, 0, 1, 1],
];

type AgentState = "idle" | "active" | "alert";

function PixelBot({
  color,
  state,
  scale = 1,
}: {
  color: string;
  state: AgentState;
  scale?: number;
}) {
  const fill = state === "alert" ? "#ff4444" : color;
  const glow = state !== "idle" ? `drop-shadow(0 0 ${state === "alert" ? 6 : 3}px ${fill})` : undefined;
  const w = Math.round(24 * scale);
  const h = Math.round(32 * scale);
  return (
    <svg
      viewBox="0 0 24 32"
      width={w}
      height={h}
      style={{ imageRendering: "pixelated", filter: glow, display: "block" }}
    >
      {SPRITE.flatMap((row, ry) =>
        row.map((cell, cx) =>
          cell ? (
            <rect
              key={`${ry}-${cx}`}
              x={cx * 4}
              y={ry * 4}
              width={4}
              height={4}
              fill={fill}
              opacity={state === "idle" ? 0.4 : 1}
            />
          ) : null
        )
      )}
    </svg>
  );
}

// Animated flowing arrow between two pipeline agents
function PipeArrow({ color, active }: { color: string; active: boolean }) {
  return (
    <svg
      width="32"
      height="14"
      viewBox="0 0 32 14"
      style={{ display: "block", flexShrink: 0, marginBottom: 18 }}
    >
      <line
        x1="0" y1="7" x2="23" y2="7"
        stroke={active ? color : "#1e2e1e"}
        strokeWidth="2"
        strokeDasharray={active ? "4 2" : "none"}
      />
      <polygon
        points="23,3 31,7 23,11"
        fill={active ? color : "#1e2e1e"}
      />
      {active && (
        <circle r="2.5" fill={color} opacity="0.95">
          <animateMotion dur="0.55s" repeatCount="1" path="M0,7 L23,7" />
        </circle>
      )}
    </svg>
  );
}

export default function AgentFeed({ symbol }: { symbol?: string | null }) {
  const [events, setEvents] = useState<NormEvent[]>([]);
  const [agentStates, setAgentStates] = useState<Record<string, AgentState>>({});
  const [speechBubbles, setSpeechBubbles] = useState<Record<string, string>>({});
  const [activeArrows, setActiveArrows] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState(false);

  const lastRef = useRef<Record<string, NormEvent>>({});
  const animTOs = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const speechTOs = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const arrowTOs = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let mounted = true;

    async function poll() {
      try {
        const res = await fetch("/api/events?limit=40");
        const data = await res.json();
        const raw: AgentEvent[] = Array.isArray(data) ? data : (data.events ?? []);

        const norm: NormEvent[] = raw.map((ev) => ({
          id: ev.id,
          agent: (ev.agent ?? "").toLowerCase(),
          level: ev.level ?? "info",
          msg: ((ev.msg ?? ev.message ?? "") as string),
          ts: ((ev.ts ?? ev.created_at ?? null) as string | null),
        }));

        if (!mounted) return;
        setEvents(norm);

        // Latest event per agent
        const latest: Record<string, NormEvent> = {};
        norm.forEach((ev) => {
          if (!latest[ev.agent]) latest[ev.agent] = ev;
        });

        Object.entries(latest).forEach(([key, ev]) => {
          const prev = lastRef.current[key];
          if (prev && prev.ts === ev.ts) return;
          lastRef.current[key] = ev;

          const state: AgentState =
            ev.level === "error" || ev.level === "warn" ? "alert" : "active";

          setAgentStates((s) => ({ ...s, [key]: state }));

          const bubble = ev.msg.length > 52 ? ev.msg.slice(0, 49) + "…" : ev.msg;
          setSpeechBubbles((s) => ({ ...s, [key]: bubble }));
          clearTimeout(speechTOs.current[key]);
          speechTOs.current[key] = setTimeout(() => {
            setSpeechBubbles((s) => ({ ...s, [key]: "" }));
          }, 3500);

          clearTimeout(animTOs.current[key]);
          animTOs.current[key] = setTimeout(() => {
            setAgentStates((s) => ({ ...s, [key]: "idle" }));
          }, state === "active" ? 900 : 1500);

          // Animate outgoing arrow
          const pipeIdx = PIPELINE.findIndex((a) => a.key === key);
          if (pipeIdx >= 0 && pipeIdx < PIPELINE.length - 1) {
            const ak = `${key}→${PIPELINE[pipeIdx + 1].key}`;
            setActiveArrows((s) => new Set([...s, ak]));
            clearTimeout(arrowTOs.current[ak]);
            arrowTOs.current[ak] = setTimeout(() => {
              setActiveArrows((s) => { const n = new Set(s); n.delete(ak); return n; });
            }, 700);
          }
        });
      } catch {
        // network error — silently ignore
      }
    }

    poll();
    const id = setInterval(poll, 2500);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const filtered = symbol
    ? events.filter((e) => e.msg.includes(symbol))
    : events;

  const copyLog = () => {
    const text = filtered
      .map((e) => `${e.ts ? formatTime(e.ts) : "--:--"} [${e.agent}] ${e.msg}`)
      .join("\n");
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="border border-terminal-border rounded bg-terminal-surface flex flex-col h-[540px]">
      {/* ── Header ── */}
      <div className="px-3 py-2 border-b border-terminal-border flex items-center justify-between shrink-0">
        <span className="text-matrix-dim text-xs uppercase tracking-widest">
          Agent Orchestration
        </span>
        <button
          onClick={copyLog}
          title="Copy log"
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

      {/* ── Theater ── */}
      <div
        className="shrink-0 border-b border-terminal-border"
        style={{ background: "#080d08", paddingTop: 48, paddingBottom: 10, paddingLeft: 8, paddingRight: 8 }}
      >
        {/* Pipeline row */}
        <div className="flex items-end justify-center">
          {PIPELINE.map((agent, i) => {
            const state = agentStates[agent.key] ?? "idle";
            const bubble = speechBubbles[agent.key];
            const arrowKey = i < PIPELINE.length - 1
              ? `${agent.key}→${PIPELINE[i + 1].key}`
              : null;

            return (
              <div key={agent.key} className="flex items-end">
                {/* Agent column */}
                <div className="relative flex flex-col items-center" style={{ width: 58 }}>
                  {/* Speech bubble */}
                  <div
                    style={{
                      position: "absolute",
                      top: -42,
                      left: "50%",
                      transform: "translateX(-50%)",
                      background: "#0e150e",
                      border: `1px solid ${agent.color}`,
                      borderRadius: 3,
                      padding: "2px 5px",
                      fontSize: 8,
                      fontFamily: "'JetBrains Mono', monospace",
                      color: agent.color,
                      whiteSpace: "nowrap",
                      opacity: bubble ? 1 : 0,
                      transition: "opacity 0.3s",
                      pointerEvents: "none",
                      zIndex: 20,
                      maxWidth: 130,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                  >
                    {bubble || " "}
                  </div>

                  {/* Pixel bot with animation class */}
                  <div className={`pxbot pxbot-${state}`}>
                    <PixelBot color={agent.color} state={state} scale={1.25} />
                  </div>

                  {/* Label */}
                  <span
                    style={{
                      marginTop: 4,
                      fontSize: 9,
                      fontFamily: "'JetBrains Mono', monospace",
                      color: agent.color,
                      opacity: state === "idle" ? 0.45 : 1,
                      transition: "opacity 0.3s",
                    }}
                  >
                    {agent.label}
                  </span>
                </div>

                {/* Arrow to next */}
                {arrowKey && (
                  <PipeArrow
                    color={agent.color}
                    active={activeArrows.has(arrowKey)}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Support agents row */}
        <div className="flex justify-center gap-10 mt-3">
          {SUPPORT.map((agent) => {
            const state = agentStates[agent.key] ?? "idle";
            const bubble = speechBubbles[agent.key];
            return (
              <div
                key={agent.key}
                className="flex items-center gap-2"
                style={{ opacity: state === "idle" ? 0.4 : 1, transition: "opacity 0.3s" }}
              >
                <div className={`pxbot pxbot-${state}`}>
                  <PixelBot color={agent.color} state={state} scale={0.9} />
                </div>
                <div>
                  <div style={{ fontSize: 9, color: agent.color, fontFamily: "'JetBrains Mono', monospace" }}>
                    {agent.label}
                  </div>
                  {bubble && (
                    <div style={{ fontSize: 8, color: agent.color, fontFamily: "'JetBrains Mono', monospace", opacity: 0.75, maxWidth: 140, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      » {bubble}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Event log ── */}
      <div className="flex-1 overflow-y-auto p-2 space-y-0.5 font-mono">
        {filtered.length === 0 && (
          <div className="text-matrix-dim text-xs py-2 text-center">no events</div>
        )}
        {filtered.map((e, i) => {
          const agentColor = ALL_AGENTS.find((a) => a.key === e.agent)?.color ?? "#6b7280";
          const msgColor =
            e.level === "error" ? "#f87171"
            : e.level === "warn" ? "#facc15"
            : "#9ca3af";
          return (
            <div key={e.id ?? i} className="flex gap-2 leading-tight">
              <span className="text-matrix-dim shrink-0" style={{ fontSize: 10 }}>
                {e.ts ? formatTime(e.ts) : "--:--:--"}
              </span>
              <span
                className="shrink-0 font-bold uppercase"
                style={{ fontSize: 10, color: agentColor, width: 90 }}
              >
                [{e.agent}]
              </span>
              <span style={{ fontSize: 10, color: msgColor }}>
                {e.msg}
              </span>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>

      {/* ── Pixel animation keyframes ── */}
      <style>{`
        .pxbot { display: inline-block; }
        .pxbot-idle  { animation: pxfloat 2.3s ease-in-out infinite; }
        .pxbot-active { animation: pxbounce 0.55s cubic-bezier(.3,1.7,.4,1) 1; }
        .pxbot-alert  { animation: pxshake 0.35s linear 3, pxflash 0.35s linear 3; }
        @keyframes pxfloat  { 0%,100% { transform: translateY(0); }  50% { transform: translateY(-5px); } }
        @keyframes pxbounce { 0% { transform: translateY(0); } 35% { transform: translateY(-13px); } 65% { transform: translateY(0); } 100% { transform: translateY(-3px); } }
        @keyframes pxshake  { 0%,100% { transform: translateX(0); } 25% { transform: translateX(-5px); } 75% { transform: translateX(5px); } }
        @keyframes pxflash  { 0%,100% { filter: brightness(1); } 50% { filter: brightness(2.8); } }
      `}</style>
    </div>
  );
}
