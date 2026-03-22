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
  { key: "neural",        label: "Neural",    color: "#d500f9" },
  { key: "council",       label: "Council",   color: "#ff9d00" },
  { key: "risk",          label: "Risk",      color: "#ff4455" },
  { key: "execution",     label: "Exec",      color: "#f0f0f0" },
  { key: "trade_manager", label: "TradeMgr",  color: "#bf7fff" },
];

const SUPPORT: { key: string; label: string; color: string }[] = [
  { key: "learning",      label: "Learning",  color: "#4da6ff" },
  { key: "model_manager", label: "ModelMgr",  color: "#76ff03" },
  { key: "logging",       label: "Logging",   color: "#5c6a78" },
];

const ALL_AGENTS = [...PIPELINE, ...SUPPORT];

// ── Pixel sprite — 6×10 grid ─────────────────────────────────────────────────
const SPRITE: number[][] = [
  [0, 1, 1, 1, 1, 0],
  [1, 1, 1, 1, 1, 1],
  [1, 0, 1, 1, 0, 1],
  [1, 1, 0, 0, 1, 1],
  [0, 1, 1, 1, 1, 0],
  [1, 1, 1, 1, 1, 1],
  [0, 1, 1, 1, 1, 0],
  [0, 1, 0, 0, 1, 0],
  [0, 1, 0, 0, 1, 0],
  [1, 1, 0, 0, 1, 1],
];

type AgentState = "idle" | "active" | "alert";

function PixelBot({ color, state, size = 54 }: { color: string; state: AgentState; size?: number }) {
  const px   = 3;
  const cols = SPRITE[0].length;
  const rows = SPRITE.length;
  const vw   = cols * px;
  const vh   = rows * px;
  const h    = Math.round(size * vh / vw);

  const fill  = state === "alert" ? "#ff4455" : color;
  const alpha = state === "idle" ? 0.28 : 1;
  const glow  = state === "idle" ? undefined : `drop-shadow(0 0 ${state === "alert" ? 10 : 6}px ${fill}cc)`;

  return (
    <svg viewBox={`0 0 ${vw} ${vh}`} width={size} height={h}
      style={{ imageRendering: "pixelated", filter: glow, display: "block" }}>
      {SPRITE.flatMap((row, ry) =>
        row.map((on, cx) => on ? (
          <rect key={`${ry}-${cx}`} x={cx * px} y={ry * px} width={px} height={px} fill={fill} opacity={alpha} />
        ) : null)
      )}
    </svg>
  );
}

// ── Animated pipeline arrow ───────────────────────────────────────────────────

function PipeArrow({ color, active, id }: { color: string; active: boolean; id: string }) {
  return (
    <div style={{ position: "relative", width: 26, height: 14, flexShrink: 0, marginBottom: 28 }}>
      <svg width="26" height="14" viewBox="0 0 26 14" style={{ display: "block" }}>
        <line x1="0" y1="7" x2="18" y2="7"
          stroke={active ? color : "#1a2a1a"}
          strokeWidth={active ? 2 : 1}
          strokeDasharray={active ? "none" : "3 2"}
          style={{ transition: "stroke 0.2s" }}
        />
        <polygon points="18,2 25,7 18,12"
          fill={active ? color : "#1a2a1a"}
          style={{ transition: "fill 0.2s" }}
        />
      </svg>
      {active && (
        <div style={{
          position: "absolute", top: "50%", left: 0,
          transform: "translateY(-50%)",
          width: 4, height: 4, borderRadius: "50%",
          background: color, boxShadow: `0 0 6px ${color}`,
          animationName: `arrowTravel-${id}`,
          animationDuration: "0.35s",
          animationTimingFunction: "linear",
          animationFillMode: "forwards",
        }} />
      )}
      <style>{`@keyframes arrowTravel-${id} { from { left:0; opacity:1; } to { left:18px; opacity:0; } }`}</style>
    </div>
  );
}

// ── Status dot ────────────────────────────────────────────────────────────────

function StatusDot({ color, state }: { color: string; state: AgentState }) {
  return (
    <span style={{
      display: "inline-block", width: 6, height: 6, borderRadius: "50%",
      background: state === "idle" ? "#1a2a1a" : color,
      boxShadow: state !== "idle" ? `0 0 8px ${color}, 0 0 16px ${color}55` : undefined,
      transition: "background 0.25s, box-shadow 0.25s",
      marginBottom: 3,
    }} />
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
  const scrollRef = useRef<HTMLDivElement>(null);

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
          }, 5000);

          clearTimeout(animTOs.current[key]);
          animTOs.current[key] = setTimeout(() => {
            setAgentStates((s) => ({ ...s, [key]: "idle" }));
          }, state === "active" ? 600 : 1200);

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
    const id = setInterval(poll, 400);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  // Auto-scroll — only the log div, never the page
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    if (distFromBottom <= 80) {
      el.scrollTop = el.scrollHeight - el.clientHeight;
    }
  }, [events]);

  const filtered = symbol ? events.filter((e) => e.msg.includes(symbol)) : events;

  const copyLog = () => {
    const text = filtered.map((e) => `${e.ts ? formatTime(e.ts) : "--:--"} [${e.agent}] ${e.msg}`).join("\n");
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div style={{
      border: "1px solid #1c1c28",
      borderRadius: 8,
      background: "#0a0a0f",
      display: "flex",
      flexDirection: "column",
      height: 620,
      overflow: "hidden",
    }}>

      {/* ── Header ─────────────────────────────────────────────────── */}
      <div style={{
        padding: "10px 14px",
        borderBottom: "1px solid #1c1c28",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexShrink: 0,
        background: "linear-gradient(90deg, #0a0a18 0%, #0a0a0f 100%)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{
            width: 6, height: 6, borderRadius: "50%",
            background: "#00ff41",
            boxShadow: "0 0 8px #00ff4188",
            flexShrink: 0,
            animation: "pulseGlow 2s ease-in-out infinite",
          }} />
          <span style={{
            fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 700, letterSpacing: "0.22em",
            color: "#00d4ff", textTransform: "uppercase",
          }}>
            Agent Orchestration
          </span>
          <span style={{
            fontSize: 9, color: "#2a3a4a",
            fontFamily: "'JetBrains Mono', monospace",
            letterSpacing: "0.08em",
          }}>
            PIPELINE ×{PIPELINE.length} · SUPPORT ×{SUPPORT.length}
          </span>
        </div>
        <button onClick={copyLog} title="Copy log"
          style={{ color: "#3a4a5a", background: "none", border: "none", cursor: "pointer", padding: 4 }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.color = "#00d4ff"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.color = "#3a4a5a"; }}
        >
          {copied ? (
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#00ff88" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
          ) : (
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
          )}
        </button>
      </div>

      {/* ── Theater ─────────────────────────────────────────────────── */}
      <div style={{
        flexShrink: 0,
        borderBottom: "1px solid #1c1c28",
        overflow: "hidden",
        background: "radial-gradient(ellipse at 50% 110%, #06101a 0%, #050910 50%, #030508 100%)",
        paddingTop: 44,
        paddingBottom: 14,
        position: "relative",
      }}>
        {/* Grid overlay */}
        <div aria-hidden style={{
          position: "absolute", inset: 0, pointerEvents: "none", zIndex: 0,
          backgroundImage: [
            "linear-gradient(rgba(0,212,255,0.012) 1px, transparent 1px)",
            "linear-gradient(90deg, rgba(0,212,255,0.012) 1px, transparent 1px)",
          ].join(","),
          backgroundSize: "24px 24px",
        }} />

        {/* Pipeline row — horizontally scrollable */}
        <div style={{
          position: "relative", zIndex: 1,
          overflowX: "auto", overflowY: "visible",
          paddingBottom: 4,
          scrollbarWidth: "none",
        }}>
          <div style={{
            display: "flex",
            alignItems: "flex-end",
            justifyContent: "center",
            gap: 0,
            minWidth: "max-content",
            padding: "0 16px",
          }}>
            {PIPELINE.map((agent, i) => {
              const state    = agentStates[agent.key] ?? "idle";
              const bubble   = bubbles[agent.key];
              const arrowKey = i < PIPELINE.length - 1 ? `${agent.key}→${PIPELINE[i + 1].key}` : null;

              return (
                <div key={agent.key} style={{ display: "flex", alignItems: "flex-end" }}>
                  <div style={{ position: "relative", display: "flex", flexDirection: "column", alignItems: "center", width: 58 }}>

                    {/* Speech bubble */}
                    <div style={{
                      position: "absolute", top: -46, left: "50%",
                      transform: "translateX(-50%)",
                      background: "#06090e",
                      border: `1px solid ${agent.color}44`,
                      borderRadius: 4, padding: "3px 7px",
                      fontSize: 8.5, fontFamily: "'JetBrains Mono', monospace",
                      color: agent.color, whiteSpace: "nowrap",
                      opacity: bubble ? 1 : 0, transition: "opacity 0.2s",
                      pointerEvents: "none", zIndex: 20,
                      maxWidth: 160, overflow: "hidden", textOverflow: "ellipsis",
                      letterSpacing: 0.2,
                      boxShadow: bubble ? `0 0 10px ${agent.color}22, inset 0 0 8px ${agent.color}08` : "none",
                    }}>
                      {bubble || " "}
                    </div>

                    <StatusDot color={agent.color} state={state} />

                    <div className={`pxbot pxbot-${state}`} style={{ transformOrigin: "bottom center" }}>
                      <PixelBot color={agent.color} state={state} size={44} />
                    </div>

                    {/* Ground glow */}
                    <div style={{
                      width: 28, height: 3, borderRadius: "50%",
                      background: state === "idle" ? "transparent"
                        : `radial-gradient(ellipse, ${agent.color}55 0%, transparent 70%)`,
                      marginTop: 2, transition: "background 0.3s",
                    }} />

                    <span style={{
                      marginTop: 2, fontSize: 8.5,
                      fontFamily: "'JetBrains Mono', monospace",
                      color: agent.color,
                      opacity: state === "idle" ? 0.28 : 1,
                      transition: "opacity 0.25s", letterSpacing: 0.5,
                      fontWeight: state !== "idle" ? 700 : 400,
                      textShadow: state !== "idle" ? `0 0 8px ${agent.color}` : undefined,
                    }}>
                      {agent.label}
                    </span>
                  </div>

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
        </div>

        {/* Support agents */}
        <div style={{
          position: "relative", zIndex: 1,
          display: "flex", justifyContent: "center",
          alignItems: "center", gap: 24, marginTop: 14,
          flexWrap: "wrap", padding: "0 12px",
        }}>
          <span style={{
            fontSize: 7.5, color: "#1a2a1a",
            fontFamily: "'JetBrains Mono', monospace",
            letterSpacing: 1.8, textTransform: "uppercase",
          }}>
            SUPPORT
          </span>

          {SUPPORT.map((agent) => {
            const state  = agentStates[agent.key] ?? "idle";
            const bubble = bubbles[agent.key];
            return (
              <div key={agent.key} style={{
                display: "flex", alignItems: "center", gap: 8,
                opacity: state === "idle" ? 0.30 : 1,
                transition: "opacity 0.25s",
              }}>
                <div className={`pxbot pxbot-${state}`} style={{ transformOrigin: "bottom center" }}>
                  <PixelBot color={agent.color} state={state} size={32} />
                </div>
                <div>
                  <div style={{
                    fontSize: 9.5, color: agent.color,
                    fontFamily: "'JetBrains Mono', monospace",
                    letterSpacing: 0.4,
                    fontWeight: state !== "idle" ? 700 : 400,
                    textShadow: state !== "idle" ? `0 0 6px ${agent.color}` : undefined,
                  }}>
                    {agent.label}
                  </div>
                  <div style={{
                    fontSize: 8.5, color: agent.color,
                    fontFamily: "'JetBrains Mono', monospace",
                    opacity: bubble ? 0.70 : 0, transition: "opacity 0.2s",
                    maxWidth: 150, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}>
                    {bubble ? `» ${bubble}` : " "}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* ── Event log ──────────────────────────────────────────────── */}
      <div
        ref={scrollRef}
        style={{
          flex: 1, overflowY: "auto", overflowX: "hidden",
          padding: "6px 8px 4px",
          fontFamily: "'JetBrains Mono', monospace",
        }}
      >
        {filtered.length === 0 && (
          <div style={{
            fontSize: 11, padding: "16px 0", textAlign: "center",
            opacity: 0.25, color: "#00d4ff",
          }}>
            awaiting events…
          </div>
        )}
        {filtered.map((e, i) => {
          const agentColor = ALL_AGENTS.find((a) => a.key === e.agent)?.color ?? "#4a5568";
          const msgColor   = e.level === "error" ? "#ff4455" : e.level === "warn" ? "#f5c518" : "#7a8a9a";
          const dot        = e.level === "error" ? "#ff4455" : e.level === "warn" ? "#f5c518" : "#1e2e3e";

          return (
            <div key={e.id ?? i}
              style={{ display: "flex", alignItems: "flex-start", gap: 7, padding: "1.5px 4px", borderRadius: 3, transition: "background 0.12s" }}
              onMouseEnter={(el) => { (el.currentTarget as HTMLElement).style.background = "rgba(0,212,255,0.04)"; }}
              onMouseLeave={(el) => { (el.currentTarget as HTMLElement).style.background = ""; }}
            >
              <span style={{ fontSize: 9.5, color: "#253545", flexShrink: 0, marginTop: 1.5, letterSpacing: 0.3 }}>
                {e.ts ? formatTime(e.ts) : "--:--:--"}
              </span>
              <span style={{ fontSize: 8.5, color: dot, flexShrink: 0, marginTop: 3 }}>●</span>
              <span style={{
                fontSize: 9.5, color: agentColor,
                flexShrink: 0, fontWeight: 700, width: 86, letterSpacing: 0.2,
              }}>
                [{e.agent}]
              </span>
              <span style={{ fontSize: 10.5, color: msgColor, lineHeight: 1.45 }}>
                {e.msg}
              </span>
            </div>
          );
        })}
      </div>

      {/* ── Animation keyframes ─────────────────────────────────────── */}
      <style>{`
        .pxbot { display: inline-block; }

        .pxbot-idle {
          animation: breathe 3.2s ease-in-out infinite;
        }
        @keyframes breathe {
          0%,100% { transform: translateY(0) scaleX(1) scaleY(1); }
          45%     { transform: translateY(-5px) scaleX(1.04) scaleY(0.97); }
        }

        .pxbot-active {
          animation: springJump 0.55s cubic-bezier(.2,1.6,.4,1) 1 forwards;
        }
        @keyframes springJump {
          0%   { transform: translateY(0) scaleX(1) scaleY(1); }
          12%  { transform: translateY(0) scaleX(1.15) scaleY(0.82); }
          35%  { transform: translateY(-22px) scaleX(0.88) scaleY(1.15); }
          65%  { transform: translateY(0) scaleX(1.12) scaleY(0.85); }
          80%  { transform: translateY(-6px) scaleX(0.96) scaleY(1.05); }
          100% { transform: translateY(0) scaleX(1) scaleY(1); }
        }

        .pxbot-alert {
          animation: alarmShake 0.15s linear 6, alarmFlash 0.15s linear 6;
        }
        @keyframes alarmShake {
          0%,100% { transform: translateX(0); }
          25%     { transform: translateX(-7px); }
          75%     { transform: translateX(7px); }
        }
        @keyframes alarmFlash {
          0%,100% { filter: brightness(1); }
          50%     { filter: brightness(3.5) saturate(2); }
        }

        @keyframes pulseGlow {
          0%,100% { opacity: 1; box-shadow: 0 0 8px #00ff4188; }
          50%     { opacity: 0.7; box-shadow: 0 0 16px #00ff41cc; }
        }

        /* Hide scrollbar on theater pipeline */
        div::-webkit-scrollbar { height: 0; width: 6px; }
        div::-webkit-scrollbar-track { background: transparent; }
        div::-webkit-scrollbar-thumb { background: #1a2a2a; border-radius: 3px; }
      `}</style>
    </div>
  );
}
