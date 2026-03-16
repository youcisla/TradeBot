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

const PIPELINE: { key: string; label: string; color: string }[] = [
  { key: "market",        label: "Market",   color: "#06b6d4" },
  { key: "analysis",      label: "Analysis", color: "#eab308" },
  { key: "strategy",      label: "Strategy", color: "#22c55e" },
  { key: "risk",          label: "Risk",     color: "#f97316" },
  { key: "execution",     label: "Exec",     color: "#e2e8f0" },
  { key: "trade_manager", label: "TradeMgr", color: "#d946ef" },
];

const SUPPORT: { key: string; label: string; color: string }[] = [
  { key: "learning", label: "Learning", color: "#3b82f6" },
  { key: "logging",  label: "Logging",  color: "#94a3b8" },
];

const ALL_AGENTS = [...PIPELINE, ...SUPPORT];

// 6×8 pixel-art robot (each cell = 4 px → 24×32 native SVG units)
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

function PixelBot({ color, state, size = 52 }: { color: string; state: AgentState; size?: number }) {
  const fill  = state === "alert" ? "#f87171" : color;
  const glow  = state === "idle"  ? undefined
    : `drop-shadow(0 0 ${state === "alert" ? 7 : 4}px ${fill})`;
  const alpha = state === "idle" ? 0.38 : 1;

  return (
    <svg
      viewBox="0 0 24 32"
      width={size}
      height={Math.round(size * 32 / 24)}
      style={{ imageRendering: "pixelated", filter: glow, display: "block" }}
    >
      {SPRITE.flatMap((row, ry) =>
        row.map((cell, cx) =>
          cell ? (
            <rect
              key={`${ry}-${cx}`}
              x={cx * 4} y={ry * 4} width={4} height={4}
              fill={fill} opacity={alpha}
            />
          ) : null
        )
      )}
    </svg>
  );
}

function PipeArrow({ color, active }: { color: string; active: boolean }) {
  return (
    <svg
      width="36" height="16" viewBox="0 0 36 16"
      style={{ display: "block", flexShrink: 0, marginBottom: 22 }}
    >
      <line
        x1="0" y1="8" x2="26" y2="8"
        stroke={active ? color : "#1a2a1a"}
        strokeWidth={active ? 2.5 : 1.5}
        strokeDasharray={active ? "5 2.5" : undefined}
      />
      <polygon points="26,3 35,8 26,13" fill={active ? color : "#1a2a1a"} />
      {active && (
        <circle r="3" fill={color} opacity="0.9">
          <animateMotion dur="0.5s" repeatCount="1" path="M0,8 L26,8" />
        </circle>
      )}
    </svg>
  );
}

// Tiny pulsing dot showing per-agent liveness
function LiveDot({ color, state }: { color: string; state: AgentState }) {
  return (
    <span
      style={{
        display: "inline-block",
        width: 6,
        height: 6,
        borderRadius: "50%",
        background: state === "idle" ? "#1e2e1e" : color,
        boxShadow: state !== "idle" ? `0 0 6px ${color}` : undefined,
        transition: "background 0.3s, box-shadow 0.3s",
        marginBottom: 3,
      }}
    />
  );
}

export default function AgentFeed({ symbol }: { symbol?: string | null }) {
  const [events,       setEvents]       = useState<NormEvent[]>([]);
  const [agentStates,  setAgentStates]  = useState<Record<string, AgentState>>({});
  const [bubbles,      setBubbles]      = useState<Record<string, string>>({});
  const [activeArrows, setActiveArrows] = useState<Set<string>>(new Set());
  const [copied,       setCopied]       = useState(false);

  const lastRef   = useRef<Record<string, NormEvent>>({});
  const animTOs   = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const speechTOs = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const arrowTOs  = useRef<Record<string, ReturnType<typeof setTimeout>>>({});
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let mounted = true;

    async function poll() {
      try {
        const res  = await fetch("/api/events?limit=40");
        const data = await res.json();
        const raw: AgentEvent[] = Array.isArray(data) ? data : (data.events ?? []);

        const norm: NormEvent[] = raw.map((ev) => ({
          id:    ev.id,
          agent: (ev.agent ?? "").toLowerCase(),
          level: ev.level ?? "info",
          msg:   String(ev.msg ?? ev.message ?? ""),
          ts:    String(ev.ts ?? ev.created_at ?? "") || null,
        }));

        if (!mounted) return;
        setEvents(norm);

        // Latest event per agent
        const latest: Record<string, NormEvent> = {};
        norm.forEach((ev) => { if (!latest[ev.agent]) latest[ev.agent] = ev; });

        Object.entries(latest).forEach(([key, ev]) => {
          const prev = lastRef.current[key];
          if (prev?.ts === ev.ts) return;
          lastRef.current[key] = ev;

          const state: AgentState = ev.level === "error" || ev.level === "warn" ? "alert" : "active";
          setAgentStates((s) => ({ ...s, [key]: state }));

          const text = ev.msg.length > 55 ? ev.msg.slice(0, 52) + "…" : ev.msg;
          setBubbles((s) => ({ ...s, [key]: text }));
          clearTimeout(speechTOs.current[key]);
          speechTOs.current[key] = setTimeout(() => {
            setBubbles((s) => ({ ...s, [key]: "" }));
          }, 4000);

          clearTimeout(animTOs.current[key]);
          animTOs.current[key] = setTimeout(() => {
            setAgentStates((s) => ({ ...s, [key]: "idle" }));
          }, state === "active" ? 900 : 1600);

          // Flow arrow to next pipeline agent
          const idx = PIPELINE.findIndex((a) => a.key === key);
          if (idx >= 0 && idx < PIPELINE.length - 1) {
            const ak = `${key}→${PIPELINE[idx + 1].key}`;
            setActiveArrows((s) => new Set([...s, ak]));
            clearTimeout(arrowTOs.current[ak]);
            arrowTOs.current[ak] = setTimeout(() => {
              setActiveArrows((s) => { const n = new Set(s); n.delete(ak); return n; });
            }, 650);
          }
        });
      } catch { /* silent */ }
    }

    poll();
    const id = setInterval(poll, 800);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events]);

  const filtered = symbol ? events.filter((e) => e.msg.includes(symbol)) : events;

  const copyLog = () => {
    const text = filtered.map((e) =>
      `${e.ts ? formatTime(e.ts) : "--:--"} [${e.agent}] ${e.msg}`
    ).join("\n");
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="border border-terminal-border rounded bg-terminal-surface flex flex-col h-[580px]">

      {/* ── Header ── */}
      <div className="px-3 py-2 border-b border-terminal-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <span className="text-matrix-dim text-xs uppercase tracking-widest">Agent Orchestration</span>
          <span className="text-[10px] text-matrix-dim opacity-50">PIPELINE ×{PIPELINE.length} · SUPPORT ×{SUPPORT.length}</span>
        </div>
        <button
          onClick={copyLog}
          title="Copy log"
          className="text-matrix-dim hover:text-matrix transition-colors p-1"
        >
          {copied ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
          )}
        </button>
      </div>

      {/* ── Theater ── */}
      <div
        className="shrink-0 border-b border-terminal-border overflow-hidden"
        style={{ background: "linear-gradient(180deg,#060c06 0%,#0a120a 100%)", paddingTop: 54, paddingBottom: 14 }}
      >
        {/* CRT scanline overlay */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            backgroundImage: "repeating-linear-gradient(0deg,transparent,transparent 3px,rgba(0,255,65,0.025) 3px,rgba(0,255,65,0.025) 4px)",
            zIndex: 1,
          }}
        />

        {/* Pipeline row */}
        <div className="relative flex items-end justify-center" style={{ zIndex: 2 }}>
          {PIPELINE.map((agent, i) => {
            const state    = agentStates[agent.key] ?? "idle";
            const bubble   = bubbles[agent.key];
            const arrowKey = i < PIPELINE.length - 1 ? `${agent.key}→${PIPELINE[i + 1].key}` : null;

            return (
              <div key={agent.key} className="flex items-end">
                {/* Agent column */}
                <div className="relative flex flex-col items-center" style={{ width: 70 }}>

                  {/* Speech bubble */}
                  <div style={{
                    position: "absolute",
                    top: -50,
                    left: "50%",
                    transform: "translateX(-50%)",
                    background: "#0a120a",
                    border: `1px solid ${agent.color}`,
                    borderRadius: 4,
                    padding: "3px 7px",
                    fontSize: 10,
                    fontFamily: "'JetBrains Mono', monospace",
                    color: agent.color,
                    whiteSpace: "nowrap",
                    opacity: bubble ? 1 : 0,
                    transition: "opacity 0.25s",
                    pointerEvents: "none",
                    zIndex: 20,
                    maxWidth: 160,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    letterSpacing: 0.3,
                  }}>
                    {bubble || " "}
                  </div>

                  {/* Live dot */}
                  <LiveDot color={agent.color} state={state} />

                  {/* Pixel bot */}
                  <div className={`pxbot pxbot-${state}`}>
                    <PixelBot color={agent.color} state={state} size={44} />
                  </div>

                  {/* Label */}
                  <span style={{
                    marginTop: 5,
                    fontSize: 10,
                    fontFamily: "'JetBrains Mono', monospace",
                    color: agent.color,
                    opacity: state === "idle" ? 0.4 : 1,
                    transition: "opacity 0.3s",
                    letterSpacing: 0.5,
                  }}>
                    {agent.label}
                  </span>
                </div>

                {/* Arrow */}
                {arrowKey && (
                  <PipeArrow color={agent.color} active={activeArrows.has(arrowKey)} />
                )}
              </div>
            );
          })}
        </div>

        {/* Support agents row */}
        <div className="relative flex justify-center gap-12 mt-4" style={{ zIndex: 2 }}>
          <span style={{ fontSize: 9, color: "#1e3a1e", fontFamily: "'JetBrains Mono', monospace", alignSelf: "center", marginRight: 4, letterSpacing: 1 }}>
            SUPPORT
          </span>
          {SUPPORT.map((agent) => {
            const state  = agentStates[agent.key] ?? "idle";
            const bubble = bubbles[agent.key];
            return (
              <div
                key={agent.key}
                className="flex items-center gap-2"
                style={{ opacity: state === "idle" ? 0.38 : 1, transition: "opacity 0.3s" }}
              >
                <div className={`pxbot pxbot-${state}`}>
                  <PixelBot color={agent.color} state={state} size={30} />
                </div>
                <div>
                  <div style={{ fontSize: 10, color: agent.color, fontFamily: "'JetBrains Mono', monospace", letterSpacing: 0.5 }}>
                    {agent.label}
                  </div>
                  <div style={{
                    fontSize: 9,
                    color: agent.color,
                    fontFamily: "'JetBrains Mono', monospace",
                    opacity: bubble ? 0.8 : 0,
                    transition: "opacity 0.25s",
                    maxWidth: 150,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}>
                    {bubble ? `» ${bubble}` : " "}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Event log ── */}
      <div className="flex-1 overflow-y-auto px-2 pt-1.5 pb-1 space-y-px font-mono">
        {filtered.length === 0 && (
          <div className="text-matrix-dim text-xs py-3 text-center opacity-40">awaiting events…</div>
        )}
        {filtered.map((e, i) => {
          const agentColor = ALL_AGENTS.find((a) => a.key === e.agent)?.color ?? "#64748b";
          const msgColor   =
            e.level === "error" ? "#f87171"
            : e.level === "warn"  ? "#fbbf24"
            : "#cbd5e1";
          const dot =
            e.level === "error" ? "#f87171"
            : e.level === "warn"  ? "#fbbf24"
            : "#334155";
          return (
            <div key={e.id ?? i} className="flex items-start gap-2 leading-snug hover:bg-white/[0.02] rounded px-1 py-px transition-colors">
              <span style={{ fontSize: 10, color: "#334155", flexShrink: 0, marginTop: 1 }}>
                {e.ts ? formatTime(e.ts) : "--:--:--"}
              </span>
              <span style={{ fontSize: 9, color: dot, flexShrink: 0, marginTop: 3 }}>●</span>
              <span style={{ fontSize: 10, color: agentColor, flexShrink: 0, fontWeight: 700, width: 82, letterSpacing: 0.3 }}>
                [{e.agent}]
              </span>
              <span style={{ fontSize: 11, color: msgColor, lineHeight: 1.4 }}>
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
        .pxbot-idle   { animation: pxfloat 2.4s ease-in-out infinite; }
        .pxbot-active { animation: pxbounce 0.5s cubic-bezier(.3,1.8,.4,1) 1; }
        .pxbot-alert  { animation: pxshake 0.3s linear 4, pxflash 0.3s linear 4; }
        @keyframes pxfloat  { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }
        @keyframes pxbounce { 0%{transform:translateY(0)} 30%{transform:translateY(-15px)} 65%{transform:translateY(0)} 100%{transform:translateY(-3px)} }
        @keyframes pxshake  { 0%,100%{transform:translateX(0)} 25%{transform:translateX(-6px)} 75%{transform:translateX(6px)} }
        @keyframes pxflash  { 0%,100%{filter:brightness(1)} 50%{filter:brightness(3)} }
      `}</style>
    </div>
  );
}
