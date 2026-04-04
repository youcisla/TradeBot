"use client";

import { useEffect, useMemo, useState } from "react";
import AgentFeed from "@/components/AgentFeed";
import CommandPanel from "@/components/CommandPanel";

// ── Types ─────────────────────────────────────────────────────────────────────

interface BotStatus {
  state: string;
  last_tick?: string;
  equity?: number | string;
  open_trades?: number;
  daily_pnl?: number | string;
  uptime_start?: string;
  broker_account?: string;
  broker_server?: string;
  broker_name?: string;
  balance?: number | string;
  leverage?: number | string;
}

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

// ── Agent pipeline definition ─────────────────────────────────────────────────

const PIPELINE_AGENTS = [
  { key: "crucix",        label: "Crucix",    color: "#64D2FF" },
  { key: "market",        label: "Market",    color: "#32ADE6" },
  { key: "analysis",      label: "Analysis",  color: "#FFFFFF" },
  { key: "strategy",      label: "Strategy",  color: "#30D158" },
  { key: "neural",        label: "Neural",    color: "#BF5AF2" },
  { key: "council",       label: "Council",   color: "#FF9F0A" },
  { key: "risk",          label: "Risk",      color: "#FF453A" },
  { key: "execution",     label: "Execution", color: "#FFFFFF" },
  { key: "trade_manager", label: "TradeMgr",  color: "#63E6E2" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtCurrency(v: number | string | undefined): string {
  const n = Number(v ?? 0);
  return "$" + n.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function fmtAge(ts: string | undefined): boolean {
  if (!ts) return false;
  return (Date.now() - new Date(ts).getTime()) < 60_000;
}

type RecencyTier = "fresh" | "warm" | "stale" | "cold";

function recencyTier(ts: string | undefined): RecencyTier {
  if (!ts) return "cold";
  const ageMs = Date.now() - new Date(ts).getTime();
  if (ageMs < 60_000) return "fresh";
  if (ageMs < 5 * 60_000) return "warm";
  return "stale";
}

function eventTs(ev: AgentEvent | undefined): string | undefined {
  if (!ev) return undefined;
  return ev.created_at ?? ev.ts;
}

function fmtTime(ts: string | undefined): string {
  if (!ts) return "--:--";
  const d = new Date(ts);
  return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
}

// ── Pulse animation style ─────────────────────────────────────────────────────

const PULSE_STYLE = `
  @keyframes livePulse {
    0%, 100% { opacity: 1; box-shadow: 0 0 0 0 rgba(48,209,88,0.6); }
    50% { opacity: 0.7; box-shadow: 0 0 0 6px rgba(48,209,88,0); }
  }
  @keyframes dotPulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.5; transform: scale(0.85); }
  }
  @keyframes pipelineGlow {
    0%, 100% { opacity: 0.35; transform: translateX(-6%); }
    50% { opacity: 0.85; transform: translateX(6%); }
  }
  @keyframes pipelineFlow {
    0% { transform: translateX(-90%); opacity: 0; }
    35% { opacity: 1; }
    100% { transform: translateX(110%); opacity: 0; }
  }
  @keyframes nodeLift {
    0%, 100% { transform: translateY(0px) rotateX(0deg) rotateY(0deg); }
    50% { transform: translateY(-4px) rotateX(2deg) rotateY(-2deg); }
  }
  @keyframes neutralFlow {
    0% { transform: translateX(-80%); opacity: 0; }
    30% { opacity: 0.6; }
    100% { transform: translateX(100%); opacity: 0; }
  }
`;

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CommandCenterPage() {
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [events, setEvents] = useState<AgentEvent[]>([]);

  // Poll status every 8s
  useEffect(() => {
    let active = true;
    const fetchStatus = async () => {
      try {
        const r = await fetch("/api/status");
        const d = await r.json();
        if (active) setStatus(d);
      } catch { /* silent */ }
    };
    fetchStatus();
    const id = setInterval(fetchStatus, 8_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  // Poll events every 10s (for pipeline)
  useEffect(() => {
    let active = true;
    const fetchEvents = async () => {
      try {
        const r = await fetch("/api/events?limit=50");
        const d = await r.json();
        if (active) setEvents(Array.isArray(d) ? d : (d.events ?? []));
      } catch { /* silent */ }
    };
    fetchEvents();
    const id = setInterval(fetchEvents, 10_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  // Latest event per agent
  const agentLatest = useMemo(() => {
    const map: Record<string, AgentEvent> = {};
    for (const ev of events) {
      const key = ev.agent?.toLowerCase();
      if (key && !map[key]) map[key] = ev;
    }
    return map;
  }, [events]);

  const isRunning = status?.state === "running";
  const equity    = Number(status?.equity ?? 0);
  const balance   = Number(status?.balance ?? 0);
  const dailyPnl  = Number(status?.daily_pnl ?? 0);
  const leverage  = status?.leverage ?? "—";

  const sendCommand = async (command: string) => {
    try {
      await fetch("/api/commands", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ command }),
      });
    } catch { /* silent */ }
  };

  return (
    <div style={{
      background: "#000000",
      minHeight:  "100vh",
      padding:    "20px 16px 40px",
      fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif',
      boxSizing:  "border-box",
    }}>
      <style>{PULSE_STYLE}</style>

      {/* ── Two-column grid ── */}
      <div style={{
        display:             "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
        gap:                 16,
        maxWidth:            1400,
        margin:              "0 auto",
      }}>

        {/* ═══ LEFT COLUMN ═══ */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>

          {/* ── Bot Status Hero Card ── */}
          <div style={{
            background:   "#1C1C1E",
            borderRadius: 12,
            padding:      20,
          }}>
            {/* Top row */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
              <span style={{ fontSize: 22, fontWeight: 700, color: "#FFFFFF", letterSpacing: -0.5 }}>
                NeuralFX
              </span>
              <div style={{
                display:      "flex",
                alignItems:   "center",
                gap:          6,
                background:   isRunning ? "rgba(48,209,88,0.15)" : "rgba(142,142,147,0.2)",
                borderRadius: 20,
                padding:      "4px 12px",
              }}>
                <span style={{
                  width:       8,
                  height:      8,
                  borderRadius: "50%",
                  background:  isRunning ? "#30D158" : "#8E8E93",
                  display:     "inline-block",
                  animation:   isRunning ? "livePulse 2s ease-in-out infinite" : undefined,
                  flexShrink:  0,
                }} />
                <span style={{
                  fontSize:   13,
                  fontWeight: 600,
                  color:      isRunning ? "#30D158" : "#8E8E93",
                  letterSpacing: 0.2,
                }}>
                  {isRunning ? "LIVE" : "STOPPED"}
                </span>
              </div>
            </div>

            {/* Equity display */}
            <div style={{ marginBottom: 20 }}>
              <div style={{
                fontSize:    34,
                fontWeight:  700,
                color:       "#FFFFFF",
                fontFamily:  '"SF Mono", SFMono-Regular, ui-monospace, Menlo, monospace',
                letterSpacing: -1,
                lineHeight:  1.1,
              }}>
                {fmtCurrency(equity)}
              </div>
              <div style={{ fontSize: 13, color: "#8E8E93", marginTop: 4 }}>Equity</div>
            </div>

            {/* Mini stats row */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr 1fr", gap: 8, marginBottom: 20 }}>
              {[
                { label: "Balance",     value: fmtCurrency(balance) },
                { label: "Leverage",    value: leverage ? `1:${leverage}` : "—" },
                { label: "Open Trades", value: String(status?.open_trades ?? 0) },
                {
                  label: "Daily PnL",
                  value: (dailyPnl >= 0 ? "+" : "") + fmtCurrency(dailyPnl),
                  color: dailyPnl > 0 ? "#30D158" : dailyPnl < 0 ? "#FF453A" : undefined,
                },
              ].map(({ label, value, color }) => (
                <div key={label} style={{
                  background:   "#2C2C2E",
                  borderRadius: 8,
                  padding:      "10px 8px",
                  textAlign:    "center",
                }}>
                  <div style={{
                    fontSize:   13,
                    fontWeight: 600,
                    color:      color ?? "#FFFFFF",
                    fontFamily: '"SF Mono", SFMono-Regular, ui-monospace, Menlo, monospace',
                    letterSpacing: -0.3,
                    overflow:   "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}>
                    {value}
                  </div>
                  <div style={{ fontSize: 11, color: "rgba(235,235,245,0.3)", marginTop: 3 }}>
                    {label}
                  </div>
                </div>
              ))}
            </div>

            {/* Broker info */}
            <div style={{
              borderTop:   "0.5px solid rgba(84,84,88,0.65)",
              paddingTop:  12,
              display:     "flex",
              alignItems:  "center",
              gap:         12,
            }}>
              <div style={{ fontSize: 11, color: "rgba(235,235,245,0.3)" }}>
                {status?.broker_name ?? "—"} · {status?.broker_server ?? "—"}
              </div>
              <div style={{ fontSize: 11, color: "rgba(235,235,245,0.3)", marginLeft: "auto" }}>
                #{status?.broker_account ?? "—"}
              </div>
            </div>
          </div>

          {/* ── Agent Pipeline Card ── */}
          <div style={{
            background:   "#1C1C1E",
            borderRadius: 12,
            padding:      20,
          }}>
            <div style={{
              display:       "flex",
              alignItems:    "center",
              justifyContent: "space-between",
              marginBottom:  16,
            }}>
              <span style={{ fontSize: 17, fontWeight: 700, color: "#FFFFFF" }}>
                Agent Pipeline
              </span>
              {isRunning && (
                <span style={{ fontSize: 11, color: "#30D158", fontWeight: 600 }}>Active</span>
              )}
            </div>

            {/* Pipeline pills */}
            <div style={{
              display:        "flex",
              flexWrap:       "wrap",
              gap:            8,
              alignItems:     "center",
              perspective:    900,
            }}>
              {PIPELINE_AGENTS.map((agent, i) => {
                const ev     = agentLatest[agent.key];
                const active = fmtAge(eventTs(ev));
                const tier = recencyTier(eventTs(ev));
                const hasSignal = Boolean(ev);
                const msg    = ev?.message ?? ev?.msg ?? "";

                return (
                  <div key={agent.key} style={{ display: "flex", alignItems: "center", gap: 4 }}>
                    <div style={{
                      display:      "flex",
                      flexDirection: "column",
                      gap:          4,
                      background:   active
                        ? `rgba(${hexToRgb(agent.color)},0.12)`
                        : "rgba(44,44,46,0.8)",
                      borderRadius: 20,
                      padding:      "5px 12px",
                      border:       `0.5px solid ${active ? agent.color + "60" : "rgba(84,84,88,0.4)"}`,
                      minWidth:     60,
                      textAlign:    "center",
                      position:     "relative",
                      overflow:     "hidden",
                      transformStyle: "preserve-3d",
                      transform:    active ? "translateZ(10px)" : tier === "warm" ? "translateZ(6px)" : "translateZ(3px)",
                      boxShadow:    active
                        ? `0 8px 24px ${agent.color}22, inset 0 1px 0 rgba(255,255,255,0.08)`
                        : tier === "warm"
                        ? `0 6px 16px ${agent.color}14, inset 0 1px 0 rgba(255,255,255,0.05)`
                        : "0 3px 12px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.03)",
                      animation:    `nodeLift ${active ? "2.2s" : tier === "warm" ? "2.8s" : "3.6s"} ease-in-out ${i * 0.12}s infinite`,
                      transition:   "transform 220ms ease, box-shadow 220ms ease, border-color 220ms ease",
                    }}>
                      {(active || tier === "warm") && (
                        <span
                          style={{
                            position: "absolute",
                            inset: 0,
                            background:
                              `linear-gradient(120deg, transparent 0%, ${agent.color}33 45%, transparent 75%)`,
                            animation: `pipelineGlow 1.8s ease-in-out ${i * 0.07}s infinite`,
                            pointerEvents: "none",
                          }}
                        />
                      )}
                      <div style={{ display: "flex", alignItems: "center", gap: 5, justifyContent: "center" }}>
                        <span style={{
                          width:       6,
                          height:      6,
                          borderRadius: "50%",
                          background:  active ? agent.color : tier === "warm" ? `${agent.color}CC` : hasSignal ? `${agent.color}99` : "rgba(84,84,88,0.65)",
                          display:     "inline-block",
                          flexShrink:  0,
                          animation:   `dotPulse ${active ? "1.9s" : tier === "warm" ? "2.4s" : "3.2s"} ease-in-out infinite`,
                        }} />
                        <span style={{ fontSize: 12, fontWeight: 600, color: active ? agent.color : tier === "warm" ? agent.color : "rgba(235,235,245,0.3)" }}>
                          {agent.label}
                        </span>
                      </div>
                      {msg && (
                        <div style={{
                          fontSize:     11,
                          color:        "rgba(235,235,245,0.45)",
                          overflow:     "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace:   "nowrap",
                          maxWidth:     120,
                        }} title={msg}>
                          {msg.slice(0, 44)}
                        </div>
                      )}
                    </div>
                    {i < PIPELINE_AGENTS.length - 1 && (
                      <div
                        style={{
                          width: 20,
                          height: 8,
                          borderRadius: 999,
                          background: active ? `${agent.color}33` : "rgba(84,84,88,0.3)",
                          position: "relative",
                          overflow: "hidden",
                          flexShrink: 0,
                        }}
                      >
                        {(active || tier === "warm") && (
                          <span
                            style={{
                              position: "absolute",
                              inset: 0,
                              background: active
                                ? `linear-gradient(90deg, transparent 0%, ${agent.color} 50%, transparent 100%)`
                                : tier === "warm"
                                ? `linear-gradient(90deg, transparent 0%, ${agent.color}CC 50%, transparent 100%)`
                                : "linear-gradient(90deg, transparent 0%, rgba(235,235,245,0.55) 50%, transparent 100%)",
                              animation: active
                                ? `pipelineFlow 1.4s linear ${i * 0.08}s infinite`
                                : tier === "warm"
                                ? `pipelineFlow 2.0s linear ${i * 0.08}s infinite`
                                : `neutralFlow 2.6s linear ${i * 0.1}s infinite`,
                            }}
                          />
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          {/* ── Quick Actions ── */}
          <div style={{
            background:   "#1C1C1E",
            borderRadius: 12,
            padding:      20,
          }}>
            <div style={{ fontSize: 17, fontWeight: 700, color: "#FFFFFF", marginBottom: 16 }}>
              Quick Actions
            </div>
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              {[
                { cmd: "pause",     label: "Pause",     color: "#FF9F0A", bg: "rgba(255,159,10,0.12)" },
                { cmd: "resume",    label: "Resume",    color: "#30D158", bg: "rgba(48,209,88,0.12)" },
                { cmd: "kill",      label: "Kill Bot",  color: "#FF453A", bg: "rgba(255,69,58,0.12)" },
                { cmd: "close_all", label: "Close All", color: "#FF453A", bg: "rgba(255,69,58,0.12)" },
              ].map(({ cmd, label, color, bg }) => (
                <button
                  key={cmd}
                  onClick={() => {
                    const dangerous = cmd === "kill" || cmd === "close_all";
                    if (dangerous && !window.confirm(`Are you sure you want to ${label}?`)) return;
                    sendCommand(cmd);
                  }}
                  style={{
                    height:       44,
                    padding:      "0 18px",
                    background:   bg,
                    border:       `0.5px solid ${color}40`,
                    borderRadius: 10,
                    color:        color,
                    fontSize:     15,
                    fontWeight:   600,
                    cursor:       "pointer",
                    fontFamily:   "inherit",
                    transition:   "opacity 0.15s",
                  }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "0.75"; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.opacity = "1"; }}
                  onMouseDown={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "scale(0.97)"; }}
                  onMouseUp={(e) => { (e.currentTarget as HTMLButtonElement).style.transform = "scale(1)"; }}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* ── Command Panel ── */}
          <CommandPanel />
        </div>

        {/* ═══ RIGHT COLUMN — Live Agent Feed ═══ */}
        <div>
          <AgentFeed limit={40} showHeader={true} />
        </div>
      </div>
    </div>
  );
}

// ── Hex to RGB helper ─────────────────────────────────────────────────────────

function hexToRgb(hex: string): string {
  const h = hex.replace("#", "");
  const r = parseInt(h.substring(0, 2), 16);
  const g = parseInt(h.substring(2, 4), 16);
  const b = parseInt(h.substring(4, 6), 16);
  return `${r},${g},${b}`;
}
