"use client";

import { useEffect, useRef, useState } from "react";
import { useAppShell } from "@/components/AppShell";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgentEvent {
  id?: number;
  agent: string;
  event_type?: string;
  level?: string;
  message?: string;
  msg?: string;
  created_at?: string;
  ts?: string;
}

interface AgentHealth {
  key: string;
  label: string;
  color: string;
  last: string | null;
  badge: { label: string; color: string };
  msg: string;
  count: number;
  errors: number;
}

// ── Agent config ───────────────────────────────────────────────────────────────

const AGENTS = [
  { key: "crucix",        label: "Crucix",    color: "var(--accent)" },
  { key: "market",        label: "Market",    color: "var(--accent)" },
  { key: "analysis",      label: "Analysis",  color: "var(--text-primary)" },
  { key: "strategy",      label: "Strategy",  color: "var(--agent-strategy)" },
  { key: "neural",        label: "Neural",    color: "var(--agent-neural)" },
  { key: "council",       label: "Council",   color: "var(--health-warn)" },
  { key: "risk",          label: "Risk",      color: "var(--agent-risk)" },
  { key: "execution",     label: "Execution", color: "var(--text-primary)" },
  { key: "trade_manager", label: "TradeMgr",  color: "var(--accent)" },
  { key: "learning",      label: "Learning",  color: "var(--agent-strategy)" },
  { key: "model_manager", label: "Models",    color: "var(--agent-neural)" },
  { key: "logging",       label: "Logging",   color: "var(--text-muted)" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function relTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  const s  = Math.floor(ms / 1000);
  if (s < 60)  return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60)  return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24)  return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
  } catch { return "—"; }
}

function agentColor(key: string): string {
  return AGENTS.find(a => a.key === key)?.color ?? "var(--text-muted)";
}

function agentLabel(key: string): string {
  return AGENTS.find(a => a.key === key)?.label ?? key;
}

function healthBadge(lastSeen: string | null): { label: string; color: string } {
  if (!lastSeen) return { label: "DORMANT", color: "var(--text-muted)" };
  const ms   = Date.now() - new Date(lastSeen).getTime();
  const mins = ms / 60_000;
  if (mins < 2)  return { label: "ACTIVE",  color: "var(--buy)" };
  if (mins < 10) return { label: "IDLE",   color: "var(--health-warn)" };
  if (mins < 60) return { label: "SLOW",   color: "var(--health-warn)" };
  return            { label: "STALE",  color: "var(--sell)" };
}

function severityOf(evt: AgentEvent): string {
  const l = (evt.level ?? "").toLowerCase();
  if (l === "error" || l === "critical") return "error";
  if (l === "warn"  || l === "warning")  return "warn";
  return "info";
}

function normEvent(evt: AgentEvent): { id: number; agent: string; level: string; msg: string; ts: string | null } {
  return {
    id:    evt.id ?? 0,
    agent: (evt.agent ?? "unknown").toLowerCase(),
    level: severityOf(evt),
    msg:   String(evt.msg ?? evt.message ?? ""),
    ts:    String(evt.ts ?? evt.created_at ?? "") || null,
  };
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function SkeletonCard() {
  return (
    <div style={{
      borderRadius: 10,
      background: "var(--surface-2)",
      border: "1px solid var(--surface-2)",
      padding: "12px 14px",
      height: 90,
      overflow: "hidden",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
        <div style={{ height: 11, width: 52, borderRadius: 3, background: "var(--border)" }} />
        <div style={{ height: 11, width: 48, borderRadius: 3, background: "var(--surface-2)" }} />
      </div>
      <div style={{ height: 9, width: "80%", borderRadius: 3, background: "var(--surface-1)", marginBottom: 6 }} />
      <div style={{ height: 9, width: "55%", borderRadius: 3, background: "var(--surface-2)" }} />
    </div>
  );
}

function AgentDetailDrawer({
  agent,
  health,
  events,
  onClose,
}: {
  agent: { key: string; label: string; color: string };
  health: AgentHealth;
  events: AgentEvent[];
  onClose: () => void;
}) {
  const agentEvents = events
    .filter(e => e.agent === agent.key)
    .slice(0, 20)
    .map(normEvent);

  const errors = agentEvents.filter(e => e.level === "error").length;

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: "fixed", inset: 0, zIndex: 200,
          background: "rgba(0,0,0,0.4)",
          animation: "fadeIn 150ms ease",
        }}
      />

      {/* Drawer */}
      <div style={{
        position: "fixed", top: 64, right: 0, bottom: 0, width: 420,
        zIndex: 201,
        background: "var(--surface-2)",
        borderLeft: "1px solid var(--border)",
        display: "flex", flexDirection: "column",
        animation: "slideInRight 200ms ease",
        boxShadow: "-20px 0 40px rgba(0,0,0,0.4)",
      }}>
        {/* Header */}
        <div style={{
          padding: "18px 20px 16px",
          borderBottom: "1px solid var(--border)",
          display: "flex", alignItems: "center", gap: 12,
          flexShrink: 0,
        }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: agent.color, textTransform: "uppercase", letterSpacing: 0.4 }}>
            {agent.label}
          </span>
          <span style={{
            fontSize: 9, fontWeight: 700,
            color: health.badge.color,
            background: health.badge.color + "20",
            padding: "2px 7px", borderRadius: 4,
            letterSpacing: 0.5,
          }}>
            {health.badge.label}
          </span>
          <div style={{ flex: 1 }} />
          <button
            onClick={onClose}
            style={{
              background: "none", border: "none", cursor: "pointer",
              color: "var(--text-secondary)", fontSize: 20, lineHeight: 1,
              padding: "2px 6px", borderRadius: 4,
            }}
          >
            ✕
          </button>
        </div>

        {/* Stats row */}
        <div style={{
          display: "grid", gridTemplateColumns: "repeat(3, 1fr)",
          gap: 1, padding: "14px 20px",
          borderBottom: "1px solid var(--border)",
          flexShrink: 0,
        }}>
          {[
            { label: "Events",     value: health.count },
            { label: "Errors",     value: errors,        color: errors > 0 ? "var(--sell)" : undefined },
            { label: "Last Seen",  value: relTime(health.last) },
          ].map(({ label, value, color }) => (
            <div key={label} style={{ textAlign: "center" }}>
              <div style={{ fontSize: 18, fontWeight: 700, color: color ?? "var(--text-primary)", fontFamily: "var(--font-mono-stack)" }}>
                {value}
              </div>
              <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginTop: 2 }}>
                {label}
              </div>
            </div>
          ))}
        </div>

        {/* Latest message */}
        {health.msg && health.msg !== "—" && (
          <div style={{ padding: "14px 20px", borderBottom: "1px solid var(--border)", flexShrink: 0 }}>
            <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 6 }}>
              Latest Message
            </div>
            <div style={{ fontSize: 12, color: "var(--text-secondary)", lineHeight: 1.6, wordBreak: "break-word" }}>
              {health.msg}
            </div>
          </div>
        )}

        {/* Event history */}
        <div style={{ flex: 1, overflowY: "auto", padding: "12px 20px", display: "flex", flexDirection: "column", gap: 2 }}>
          <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
            Event History · {agentEvents.length}
          </div>
          {agentEvents.length === 0 && (
            <div style={{ fontSize: 13, color: "var(--text-muted)", textAlign: "center", padding: "40px 0" }}>
              No events recorded
            </div>
          )}
          {agentEvents.map((ev, i) => (
            <div
              key={ev.id ?? i}
              style={{
                display: "flex", gap: 10, padding: "8px 10px",
                borderRadius: 6,
                background: ev.level === "error" ? "rgba(239,68,68,0.06)" : "transparent",
                borderLeft: ev.level === "error" ? `2px solid var(--sell)` : "2px solid transparent",
                alignItems: "flex-start",
              }}
            >
              <span style={{ fontSize: 10, color: "var(--text-muted)", flexShrink: 0, fontFamily: "var(--font-mono-stack)", marginTop: 1 }}>
                {fmtTime(ev.ts)}
              </span>
              <span style={{
                fontSize: 12, color: ev.level === "error" ? "var(--sell)" : ev.level === "warn" ? "var(--health-warn)" : "var(--text-secondary)",
                flex: 1, lineHeight: 1.5, wordBreak: "break-word",
              }}>
                {ev.msg}
              </span>
              {ev.level !== "info" && (
                <span style={{
                  fontSize: 9, fontWeight: 700, flexShrink: 0,
                  color: ev.level === "error" ? "var(--sell)" : "var(--health-warn)",
                  textTransform: "uppercase", letterSpacing: 0.4, marginTop: 2,
                }}>
                  {ev.level}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      <style>{`
        @keyframes fadeIn { from { opacity: 0 } to { opacity: 1 } }
        @keyframes slideInRight { from { transform: translateX(100%) } to { transform: translateX(0) } }
      `}</style>
    </>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function BrainPage() {
  const { status: shellStatus, isRunning } = useAppShell();

  const [rawEvents,  setRawEvents]  = useState<AgentEvent[]>([]);
  const [agentFilter, setAgentFilter] = useState<string>("ALL");
  const [sevFilter,   setSevFilter]   = useState<string>("ALL");
  const [search,      setSearch]      = useState("");
  const [autoScroll,  setAutoScroll]  = useState(true);
  const [loading,     setLoading]     = useState(true);
  const [selectedAgent, setSelectedAgent] = useState<{ key: string; label: string; color: string } | null>(null);

  const feedRef = useRef<HTMLDivElement>(null);

  // Data fetch
  useEffect(() => {
    const load = async () => {
      try {
        const res  = await fetch("/api/events?limit=400");
        const data = await res.json();
        const evts: AgentEvent[] = Array.isArray(data) ? data : (data.events ?? []);
        setRawEvents(evts);
      } catch { /* silent */ }
      finally { setLoading(false); }
    };
    load();
    const t = setInterval(load, 8_000);
    return () => clearInterval(t);
  }, []);

  // Auto-scroll feed
  useEffect(() => {
    if (autoScroll && feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [rawEvents, autoScroll]);

  // Agent health grid
  const agentHealth: AgentHealth[] = AGENTS.map(a => {
    const evts   = rawEvents.filter(e => (e.agent ?? "").toLowerCase() === a.key);
    const last   = evts.length > 0 ? (evts[0]?.ts ?? evts[0]?.created_at ?? null) : null;
    const badge  = healthBadge(last);
    const msg    = evts.length > 0 ? String(evts[0]?.msg ?? evts[0]?.message ?? "—") : "—";
    const errors = evts.filter(e => severityOf(e) === "error").length;
    return { ...a, last, badge, msg, count: evts.length, errors };
  });

  // Normalized events for display
  const allNormEvents = rawEvents.map(normEvent);

  // Filtered feed
  const filteredEvents = allNormEvents.filter(e => {
    const matchAgent = agentFilter === "ALL" || e.agent === agentFilter;
    const matchSev   = sevFilter   === "ALL" || e.level === sevFilter;
    const matchSearch = !search     || e.msg.toLowerCase().includes(search.toLowerCase());
    return matchAgent && matchSev && matchSearch;
  }).slice(0, 250);

  // Selected agent health
  const selectedHealth = selectedAgent
    ? agentHealth.find(h => h.key === selectedAgent.key) ?? null
    : null;

  // Styles
  const MONO = "var(--font-mono-stack)";

  return (
    <>
      {/* Agent detail drawer */}
      {selectedAgent && selectedHealth && (
        <AgentDetailDrawer
          agent={selectedAgent}
          health={selectedHealth}
          events={rawEvents}
          onClose={() => setSelectedAgent(null)}
        />
      )}

      {/* Agent health grid */}
      <div style={{
        background: "var(--surface-2)",
        border: "1px solid var(--border)",
        borderRadius: 10,
        padding: "20px",
        marginBottom: 20,
      }}>
        <div style={{
          display: "flex", alignItems: "center", justifyContent: "space-between",
          marginBottom: 16,
        }}>
          <div style={{ fontSize: 11, fontWeight: 600, color: "var(--text-muted)", letterSpacing: 0.5, textTransform: "uppercase" }}>
            Pipeline Health · {AGENTS.length} agents
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {/* Bot status */}
            {shellStatus && (
              <span style={{
                fontSize: 10, fontWeight: 700,
                color: isRunning ? "var(--buy)" : shellStatus.state === "paused" ? "var(--health-warn)" : "var(--sell)",
                background: isRunning ? "var(--surface-2)" : shellStatus.state === "paused" ? "var(--surface-2)" : "var(--surface-2)",
                padding: "2px 8px", borderRadius: 4, letterSpacing: 0.5,
                textTransform: "uppercase",
              }}>
                {isRunning ? "RUNNING" : shellStatus.state?.toUpperCase() ?? "OFFLINE"}
              </span>
            )}
          </div>
        </div>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
          gap: 10,
          minWidth: 0,
        }}>
          {loading
            ? Array.from({ length: 12 }).map((_, i) => <SkeletonCard key={i} />)
            : agentHealth.map(a => (
              <div
                key={a.key}
                onClick={() => setSelectedAgent({ key: a.key, label: a.label, color: a.color })}
                style={{
                  padding: "12px 14px",
                  borderRadius: 10,
                  cursor: "pointer",
                  transition: "all 150ms ease",
                  background: selectedAgent?.key === a.key ? "var(--border)" : "var(--surface-2)",
                  border: `1px solid ${selectedAgent?.key === a.key ? a.color + "55" : "var(--border)"}`,
                  overflow: "hidden",
                  minWidth: 0,
                }}
                onMouseEnter={e => {
                  if (selectedAgent?.key !== a.key) {
                    (e.currentTarget as HTMLDivElement).style.background = "var(--border)";
                  }
                }}
                onMouseLeave={e => {
                  if (selectedAgent?.key !== a.key) {
                    (e.currentTarget as HTMLDivElement).style.background = "var(--surface-2)";
                  }
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                  <span style={{ fontSize: 11, fontWeight: 600, color: a.color, textTransform: "uppercase", letterSpacing: 0.3 }}>
                    {a.label}
                  </span>
                  <span style={{
                    fontSize: 9, fontWeight: 700, color: a.badge.color, letterSpacing: 0.5,
                    background: a.badge.color + "20", padding: "1px 5px", borderRadius: 4,
                  }}>
                    {a.badge.label}
                  </span>
                </div>
                <div style={{
                  fontSize: 11, color: "var(--text-muted)",
                  whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                  marginBottom: 4, minWidth: 0,
                }}>
                  {a.msg.slice(0, 42)}{a.msg.length > 42 ? "…" : ""}
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 10, color: "var(--text-muted)", fontFamily: MONO }}>
                    {a.count} evt{a.count !== 1 ? "s" : ""}
                    {a.errors > 0 && <span style={{ color: "var(--sell)" }}> · {a.errors} err</span>}
                  </span>
                  <span style={{ fontSize: 10, color: "var(--text-muted)" }}>
                    {a.last ? relTime(a.last) : "—"}
                  </span>
                </div>
              </div>
            ))
          }
        </div>
      </div>

      {/* Event stream */}
      <div style={{
        background: "var(--surface-2)",
        border: "1px solid var(--border)",
        borderRadius: 10,
        display: "flex",
        flexDirection: "column",
        minHeight: 480,
        overflow: "hidden",
      }}>
        {/* Controls */}
        <div style={{
          padding: "16px 20px 12px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          flexWrap: "wrap",
          gap: 10,
          alignItems: "center",
        }}>
          <div style={{
            fontSize: 11, fontWeight: 600, color: "var(--text-muted)",
            letterSpacing: 0.5, textTransform: "uppercase",
            flex: "0 0 auto",
          }}>
            Event Stream · {filteredEvents.length}
          </div>

          {/* Severity filter */}
          <div style={{ display: "flex", gap: 4 }}>
            {(["ALL", "error", "warn", "info"] as const).map(sev => (
              <button
                key={sev}
                onClick={() => setSevFilter(sev)}
                style={{
                  padding: "3px 9px", borderRadius: 5, fontSize: 10, fontWeight: 700,
                  cursor: "pointer", border: "none", letterSpacing: 0.4, textTransform: "uppercase",
                  background: sevFilter === sev
                    ? sev === "error" ? "rgba(239,68,68,0.18)" : sev === "warn" ? "rgba(255,159,10,0.18)" : "rgba(34,197,94,0.15)"
                    : "var(--surface-1)",
                  color: sevFilter === sev
                    ? sev === "error" ? "var(--sell)" : sev === "warn" ? "var(--health-warn)" : "var(--buy)"
                    : "var(--text-muted)",
                  transition: "all 100ms ease",
                }}
              >
                {sev === "ALL" ? "All" : sev}
              </button>
            ))}
          </div>

          {/* Search */}
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search events…"
            style={{
              background: "var(--surface-2)",
              border: "1px solid var(--border)",
              borderRadius: 8, padding: "5px 11px", fontSize: 12,
              color: "var(--text-primary)", outline: "none",
              width: 160, flex: "0 0 auto",
              fontFamily: "var(--font-system)",
            }}
          />

          {/* Agent filter pills */}
          <div style={{ display: "flex", gap: 4, flexWrap: "wrap", flex: "1 1 auto", justifyContent: "flex-end" }}>
            {["ALL", ...AGENTS.map(a => a.key)].map(k => {
              const a = AGENTS.find(x => x.key === k);
              return (
                <button
                  key={k}
                  onClick={() => setAgentFilter(k)}
                  style={{
                    padding: "3px 9px", borderRadius: 5, fontSize: 10, fontWeight: 600,
                    cursor: "pointer", border: "none",
                    background: agentFilter === k
                      ? (a?.color ?? "var(--text-primary)") + "22"
                      : "var(--surface-1)",
                    color: agentFilter === k
                      ? (a?.color ?? "var(--text-primary)")
                      : "var(--text-muted)",
                    outline: agentFilter === k ? `1px solid ${a?.color ?? "var(--text-primary)"}44` : "none",
                    transition: "all 100ms ease",
                    letterSpacing: 0.3,
                  }}
                >
                  {k === "ALL" ? "All" : (a?.label ?? k)}
                </button>
              );
            })}
          </div>

          {/* Auto-scroll toggle */}
          <button
            onClick={() => setAutoScroll(s => !s)}
            style={{
              padding: "3px 9px", borderRadius: 5, fontSize: 10, fontWeight: 600,
              cursor: "pointer", border: "none",
              background: autoScroll ? "rgba(34,197,94,0.12)" : "var(--surface-1)",
              color: autoScroll ? "var(--buy)" : "var(--text-muted)",
              outline: autoScroll ? "1px solid rgba(34,197,94,0.3)" : "none",
              transition: "all 100ms ease",
              letterSpacing: 0.3,
            }}
          >
            {autoScroll ? "● Live" : "○ Paused"}
          </button>
        </div>

        {/* Feed */}
        <div
          ref={feedRef}
          onScroll={() => {
            if (!feedRef.current) return;
            const { scrollTop, scrollHeight, clientHeight } = feedRef.current;
            setAutoScroll(scrollHeight - scrollTop - clientHeight < 40);
          }}
          style={{ flex: 1, overflowY: "auto", padding: "10px 20px", display: "flex", flexDirection: "column", gap: 1 }}
        >
          {loading && (
            <div style={{ display: "flex", flexDirection: "column", gap: 2, padding: "20px 0" }}>
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} style={{
                  height: 36, borderRadius: 6,
                  background: "var(--surface-2)",
                  animation: "shimmer 1.4s ease-in-out infinite",
                  animationDelay: `${i * 80}ms`,
                }} />
              ))}
            </div>
          )}
          {!loading && filteredEvents.length === 0 && (
            <div style={{ fontSize: 13, color: "var(--text-muted)", padding: "60px 0", textAlign: "center" }}>
              No events match the current filter
            </div>
          )}
          {filteredEvents.map((evt, idx) => (
            <div
              key={evt.id ?? idx}
              style={{
                display: "flex", alignItems: "flex-start", gap: 10,
                padding: "7px 10px", borderRadius: 6, transition: "background 100ms ease",
                background: evt.level === "error"
                  ? "rgba(239,68,68,0.05)"
                  : evt.level === "warn"
                  ? "rgba(255,159,10,0.04)"
                  : "transparent",
                borderLeft: evt.level === "error"
                  ? "2px solid var(--sell)"
                  : evt.level === "warn"
                  ? "2px solid var(--health-warn)"
                  : "2px solid transparent",
              }}
              onMouseEnter={e => (e.currentTarget.style.background = evt.level === "error" ? "rgba(239,68,68,0.09)" : evt.level === "warn" ? "rgba(255,159,10,0.07)" : "var(--surface-2)")}
              onMouseLeave={e => (e.currentTarget.style.background = evt.level === "error" ? "rgba(239,68,68,0.05)" : evt.level === "warn" ? "rgba(255,159,10,0.04)" : "transparent")}
            >
              {/* Agent badge */}
              <span style={{
                fontSize: 9, fontWeight: 700, color: agentColor(evt.agent), letterSpacing: 0.4,
                background: agentColor(evt.agent) + "18",
                padding: "2px 6px", borderRadius: 4,
                flexShrink: 0, marginTop: 1, textTransform: "uppercase",
              }}>
                {agentLabel(evt.agent)}
              </span>
              {/* Message */}
              <span style={{
                fontSize: 12, color: "var(--text-secondary)",
                flex: 1, lineHeight: 1.5, wordBreak: "break-word", minWidth: 0,
              }}>
                {evt.msg}
              </span>
              {/* Level badge */}
              {evt.level !== "info" && (
                <span style={{
                  fontSize: 9, fontWeight: 700, flexShrink: 0, marginTop: 1,
                  color: evt.level === "error" ? "var(--sell)" : "var(--health-warn)",
                  textTransform: "uppercase", letterSpacing: 0.4,
                }}>
                  {evt.level}
                </span>
              )}
              {/* Time */}
              <span style={{ fontSize: 10, color: "var(--text-muted)", flexShrink: 0, marginTop: 1, fontFamily: MONO }}>
                {relTime(evt.ts ?? null)}
              </span>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        @keyframes shimmer {
          0%, 100% { opacity: 0.4; }
          50%       { opacity: 0.8; }
        }
      `}</style>
    </>
  );
}
