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

// ── Agent definitions ────────────────────────────────────────────────────────

const PIPELINE: { key: string; label: string; color: string }[] = [
  { key: "market",        label: "Market",    color: "#00d4ff" },
  { key: "analysis",      label: "Analysis",  color: "#f5c518" },
  { key: "strategy",      label: "Strategy",  color: "#00ff88" },
  { key: "council",       label: "Council",   color: "#ff9d00" },
  { key: "risk",          label: "Risk",      color: "#ff4455" },
  { key: "execution",     label: "Exec",      color: "#f0f0f0" },
  { key: "trade_manager", label: "TradeMgr",  color: "#bf7fff" },
];

const SUPPORT: { key: string; label: string; color: string }[] = [
  { key: "learning", label: "Learning", color: "#4da6ff" },
  { key: "logging",  label: "Logging",  color: "#5c6a78" },
];

const ALL_AGENTS = [...PIPELINE, ...SUPPORT];

// ── Pixel sprite — 6×10 grid, each pixel = 3px (viewBox 18×30) ─────────────
const SPRITE: number[][] = [
  [0, 1, 1, 1, 1, 0],  // head top
  [1, 1, 1, 1, 1, 1],  // head wide
  [1, 0, 1, 1, 0, 1],  // eyes
  [1, 1, 0, 0, 1, 1],  // face — mouth gap
  [0, 1, 1, 1, 1, 0],  // chin / neck
  [1, 1, 1, 1, 1, 1],  // shoulders
  [0, 1, 1, 1, 1, 0],  // torso
  [0, 1, 0, 0, 1, 0],  // hips / side arms
  [0, 1, 0, 0, 1, 0],  // upper legs
  [1, 1, 0, 0, 1, 1],  // boots
];

type AgentState = "idle" | "active" | "alert";

function PixelBot({
  color,
  state,
  size = 54,
}: {
  color: string;
  state: AgentState;
  size?: number;
}) {
  const px   = 3;                        // pixel cell size in SVG units
  const cols = SPRITE[0].length;         // 6
  const rows = SPRITE.length;            // 10
  const vw   = cols * px;                // 18
  const vh   = rows * px;                // 30
  const h    = Math.round(size * vh / vw);

  const fill  = state === "alert" ? "#ff4455" : color;
  const alpha = state === "idle" ? 0.30 : 1;
  const glow  =
    state === "idle" ? undefined
    : `drop-shadow(0 0 ${state === "alert" ? 8 : 5}px ${fill}99)`;

  return (
    <svg
      viewBox={`0 0 ${vw} ${vh}`}
      width={size}
      height={h}
      style={{ imageRendering: "pixelated", filter: glow, display: "block" }}
    >
      {SPRITE.flatMap((row, ry) =>
        row.map((on, cx) =>
          on ? (
            <rect
              key={`${ry}-${cx}`}
              x={cx * px} y={ry * px}
              width={px} height={px}
              fill={fill} opacity={alpha}
            />
          ) : null
        )
      )}
    </svg>
  );
}

// ── Animated pipeline arrow ───────────────────────────────────────────────────

function PipeArrow({ color, active, id }: { color: string; active: boolean; id: string }) {
  return (
    <div
      className="pipe-arrow-wrap"
      style={{ position: "relative", width: 30, height: 14, flexShrink: 0, marginBottom: 28 }}
    >
      <svg width="30" height="14" viewBox="0 0 30 14" style={{ display: "block" }}>
        {/* Track */}
        <line x1="0" y1="7" x2="22" y2="7"
          stroke={active ? color : "#1a2a1a"}
          strokeWidth={active ? 2 : 1}
          strokeDasharray={active ? "none" : "3 2"}
          style={{ transition: "stroke 0.2s" }}
        />
        {/* Arrowhead */}
        <polygon
          points="22,2 29,7 22,12"
          fill={active ? color : "#1a2a1a"}
          style={{ transition: "fill 0.2s" }}
        />
      </svg>

      {/* Traveling pulse — CSS keyframe so it's silky smooth */}
      {active && (
        <div
          className="arrow-pulse"
          style={{
            position: "absolute",
            top: "50%",
            left: 0,
            transform: "translateY(-50%)",
            width: 5,
            height: 5,
            borderRadius: "50%",
            background: color,
            boxShadow: `0 0 6px ${color}`,
            animationName: `arrowTravel-${id}`,
            animationDuration: "0.35s",
            animationTimingFunction: "linear",
            animationFillMode: "forwards",
          }}
        />
      )}
      <style>{`
        @keyframes arrowTravel-${id} {
          from { left: 0px; opacity: 1; }
          to   { left: 22px; opacity: 0; }
        }
      `}</style>
    </div>
  );
}

// ── Live status dot ──────────────────────────────────────────────────────────

function StatusDot({ color, state }: { color: string; state: AgentState }) {
  return (
    <span
      style={{
        display:      "inline-block",
        width:        7,
        height:       7,
        borderRadius: "50%",
        background:   state === "idle" ? "#1a2a1a" : color,
        boxShadow:    state !== "idle" ? `0 0 8px ${color}` : undefined,
        transition:   "background 0.25s, box-shadow 0.25s",
        marginBottom: 4,
      }}
    />
  );
}

// ── Main component ────────────────────────────────────────────────────────────

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
  const scrollRef  = useRef<HTMLDivElement>(null);

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

          const state: AgentState = ev.level === "error" || ev.level === "warn"
            ? "alert"
            : "active";

          setAgentStates((s) => ({ ...s, [key]: state }));

          const text = ev.msg.length > 60 ? ev.msg.slice(0, 57) + "…" : ev.msg;
          setBubbles((s) => ({ ...s, [key]: text }));
          clearTimeout(speechTOs.current[key]);
          speechTOs.current[key] = setTimeout(() => {
            setBubbles((s) => ({ ...s, [key]: "" }));
          }, 5000);

          clearTimeout(animTOs.current[key]);
          // Faster reset so theater matches the log in real-time
          animTOs.current[key] = setTimeout(() => {
            setAgentStates((s) => ({ ...s, [key]: "idle" }));
          }, state === "active" ? 600 : 1200);

          // Flow arrow to next pipeline agent
          const idx = PIPELINE.findIndex((a) => a.key === key);
          if (idx >= 0 && idx < PIPELINE.length - 1) {
            const ak = `${key}→${PIPELINE[idx + 1].key}`;
            setActiveArrows((s) => new Set([...s, ak]));
            clearTimeout(arrowTOs.current[ak]);
            arrowTOs.current[ak] = setTimeout(() => {
              setActiveArrows((s) => { const n = new Set(s); n.delete(ak); return n; });
            }, 400);
          }
        });
      } catch { /* silent */ }
    }

    poll();
    const id = setInterval(poll, 400);   // ← was 800ms; halved to match log feed
    return () => { mounted = false; clearInterval(id); };
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    // Only auto-scroll when already within 60px of the bottom
    if (distFromBottom <= 60) {
      el.scrollTop = el.scrollHeight;
    }
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
    <div className="border border-terminal-border rounded bg-terminal-surface flex flex-col h-[580px]">

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="px-3 py-2 border-b border-terminal-border flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          <span
            className="text-xs uppercase tracking-widest font-bold"
            style={{ color: "#00d4ff", letterSpacing: "0.18em" }}
          >
            Agent Orchestration
          </span>
          <span className="text-[10px] opacity-40" style={{ color: "#00d4ff" }}>
            PIPELINE ×{PIPELINE.length} · SUPPORT ×{SUPPORT.length}
          </span>
        </div>
        <button
          onClick={copyLog}
          title="Copy log"
          style={{ color: "#5c6a78" }}
          className="hover:text-white transition-colors p-1"
        >
          {copied ? (
            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24"
              fill="none" stroke="#00ff88" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" width="13" height="13" viewBox="0 0 24 24"
              fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
          )}
        </button>
      </div>

      {/* ── Theater ────────────────────────────────────────────────────── */}
      <div
        className="shrink-0 border-b border-terminal-border overflow-hidden"
        style={{
          background: "radial-gradient(ellipse at 50% 120%, #060f1a 0%, #050a05 60%, #030503 100%)",
          paddingTop: 48,
          paddingBottom: 16,
          position: "relative",
        }}
      >
        {/* Subtle pixel grid overlay */}
        <div
          aria-hidden
          style={{
            position: "absolute",
            inset: 0,
            pointerEvents: "none",
            backgroundImage: [
              "linear-gradient(rgba(0,255,65,0.018) 1px, transparent 1px)",
              "linear-gradient(90deg, rgba(0,255,65,0.018) 1px, transparent 1px)",
            ].join(","),
            backgroundSize: "20px 20px",
            zIndex: 0,
          }}
        />

        {/* Pipeline row */}
        <div
          className="relative flex items-end justify-center"
          style={{ zIndex: 1, gap: 0 }}
        >
          {PIPELINE.map((agent, i) => {
            const state    = agentStates[agent.key] ?? "idle";
            const bubble   = bubbles[agent.key];
            const arrowKey = i < PIPELINE.length - 1
              ? `${agent.key}→${PIPELINE[i + 1].key}`
              : null;

            return (
              <div key={agent.key} className="flex items-end">

                {/* Agent column */}
                <div
                  className="relative flex flex-col items-center"
                  style={{ width: 62 }}
                >
                  {/* Speech bubble */}
                  <div
                    style={{
                      position:     "absolute",
                      top:          -48,
                      left:         "50%",
                      transform:    "translateX(-50%)",
                      background:   "#06090d",
                      border:       `1px solid ${agent.color}55`,
                      borderRadius: 3,
                      padding:      "3px 7px",
                      fontSize:     9,
                      fontFamily:   "'JetBrains Mono', monospace",
                      color:        agent.color,
                      whiteSpace:   "nowrap",
                      opacity:      bubble ? 1 : 0,
                      transition:   "opacity 0.2s",
                      pointerEvents:"none",
                      zIndex:       20,
                      maxWidth:     170,
                      overflow:     "hidden",
                      textOverflow: "ellipsis",
                      letterSpacing:0.3,
                      boxShadow:    bubble ? `0 0 8px ${agent.color}22` : "none",
                    }}
                  >
                    {bubble || " "}
                  </div>

                  {/* Status dot */}
                  <StatusDot color={agent.color} state={state} />

                  {/* Bot */}
                  <div className={`pxbot pxbot-${state}`} style={{ transformOrigin: "bottom center" }}>
                    <PixelBot color={agent.color} state={state} size={48} />
                  </div>

                  {/* Ground shadow */}
                  <div
                    style={{
                      width:        32,
                      height:       4,
                      borderRadius: "50%",
                      background:   state === "idle"
                        ? "transparent"
                        : `radial-gradient(ellipse, ${agent.color}44 0%, transparent 70%)`,
                      marginTop:    2,
                      transition:   "background 0.3s",
                    }}
                  />

                  {/* Label */}
                  <span
                    style={{
                      marginTop:    2,
                      fontSize:     9,
                      fontFamily:   "'JetBrains Mono', monospace",
                      color:        agent.color,
                      opacity:      state === "idle" ? 0.35 : 1,
                      transition:   "opacity 0.25s",
                      letterSpacing:0.6,
                      fontWeight:   state !== "idle" ? 700 : 400,
                    }}
                  >
                    {agent.label}
                  </span>
                </div>

                {/* Arrow to next agent */}
                {arrowKey && (
                  <PipeArrow
                    color={PIPELINE[i + 1].color}
                    active={activeArrows.has(arrowKey)}
                    id={arrowKey.replace(/[→]/g, "_")}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Support agents row */}
        <div
          className="relative flex justify-center gap-10 mt-5"
          style={{ zIndex: 1 }}
        >
          <span
            style={{
              fontSize:     8,
              color:        "#1e2e1e",
              fontFamily:   "'JetBrains Mono', monospace",
              alignSelf:    "center",
              letterSpacing:1.5,
            }}
          >
            SUPPORT
          </span>

          {SUPPORT.map((agent) => {
            const state  = agentStates[agent.key] ?? "idle";
            const bubble = bubbles[agent.key];
            return (
              <div
                key={agent.key}
                className="flex items-center gap-2"
                style={{
                  opacity:    state === "idle" ? 0.32 : 1,
                  transition: "opacity 0.25s",
                }}
              >
                <div
                  className={`pxbot pxbot-${state}`}
                  style={{ transformOrigin: "bottom center" }}
                >
                  <PixelBot color={agent.color} state={state} size={34} />
                </div>
                <div>
                  <div
                    style={{
                      fontSize:     10,
                      color:        agent.color,
                      fontFamily:   "'JetBrains Mono', monospace",
                      letterSpacing:0.5,
                      fontWeight:   state !== "idle" ? 700 : 400,
                    }}
                  >
                    {agent.label}
                  </div>
                  <div
                    style={{
                      fontSize:     9,
                      color:        agent.color,
                      fontFamily:   "'JetBrains Mono', monospace",
                      opacity:      bubble ? 0.75 : 0,
                      transition:   "opacity 0.2s",
                      maxWidth:     160,
                      overflow:     "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace:   "nowrap",
                    }}
                  >
                    {bubble ? `» ${bubble}` : " "}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Event log ──────────────────────────────────────────────────── */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-2 pt-1.5 pb-1 space-y-px font-mono">
        {filtered.length === 0 && (
          <div className="text-xs py-3 text-center opacity-30" style={{ color: "#00d4ff" }}>
            awaiting events…
          </div>
        )}
        {filtered.map((e, i) => {
          const agentColor = ALL_AGENTS.find((a) => a.key === e.agent)?.color ?? "#5c6a78";
          const msgColor   =
            e.level === "error" ? "#ff4455"
            : e.level === "warn"  ? "#f5c518"
            : "#9aa8b8";
          const dot =
            e.level === "error" ? "#ff4455"
            : e.level === "warn"  ? "#f5c518"
            : "#2a3a4a";

          return (
            <div
              key={e.id ?? i}
              className="flex items-start gap-2 leading-snug px-1 py-px rounded"
              style={{ transition: "background 0.15s" }}
              onMouseEnter={(el) => { (el.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.025)"; }}
              onMouseLeave={(el) => { (el.currentTarget as HTMLElement).style.background = ""; }}
            >
              <span style={{ fontSize: 10, color: "#2a3a4a", flexShrink: 0, marginTop: 1 }}>
                {e.ts ? formatTime(e.ts) : "--:--:--"}
              </span>
              <span style={{ fontSize: 9, color: dot, flexShrink: 0, marginTop: 3 }}>●</span>
              <span
                style={{
                  fontSize:     10,
                  color:        agentColor,
                  flexShrink:   0,
                  fontWeight:   700,
                  width:        82,
                  letterSpacing:0.3,
                }}
              >
                [{e.agent}]
              </span>
              <span style={{ fontSize: 11, color: msgColor, lineHeight: 1.45 }}>
                {e.msg}
              </span>
            </div>
          );
        })}
      </div>

      {/* ── Animation keyframes ────────────────────────────────────────── */}
      <style>{`
        .pxbot { display: inline-block; }

        /* Idle — gentle breathing float */
        .pxbot-idle {
          animation: breathe 3s ease-in-out infinite;
        }
        @keyframes breathe {
          0%,100% { transform: translateY(0)   scaleX(1)    scaleY(1);    }
          45%     { transform: translateY(-5px) scaleX(1.04) scaleY(0.97); }
        }

        /* Active — spring jump with squash & stretch */
        .pxbot-active {
          animation: springJump 0.55s cubic-bezier(.2,1.6,.4,1) 1 forwards;
        }
        @keyframes springJump {
          0%   { transform: translateY(0)    scaleX(1)    scaleY(1);    }
          12%  { transform: translateY(0)    scaleX(1.15) scaleY(0.82); }
          35%  { transform: translateY(-20px) scaleX(0.88) scaleY(1.15); }
          65%  { transform: translateY(0)    scaleX(1.12) scaleY(0.85); }
          80%  { transform: translateY(-6px) scaleX(0.96) scaleY(1.05); }
          100% { transform: translateY(0)    scaleX(1)    scaleY(1);    }
        }

        /* Alert — rapid shake + brightness flash */
        .pxbot-alert {
          animation: alarmShake 0.15s linear 6, alarmFlash 0.15s linear 6;
        }
        @keyframes alarmShake {
          0%,100% { transform: translateX(0);   }
          25%     { transform: translateX(-7px); }
          75%     { transform: translateX(7px);  }
        }
        @keyframes alarmFlash {
          0%,100% { filter: brightness(1);   }
          50%     { filter: brightness(3.5) saturate(2); }
        }
      `}</style>
    </div>
  );
}
