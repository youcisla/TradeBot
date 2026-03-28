"use client";

import { useEffect, useMemo, useRef, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgentEvent {
  id: string; agent: string; event_type: string;
  message: string; created_at: string;
  metadata?: Record<string, unknown>;
}

// ── Log row helpers ────────────────────────────────────────────────────────────

function eventTypeColor(eventType: string): string {
  const t = (eventType ?? "").toLowerCase();
  if (t.includes("error") || t.includes("fail") || t.includes("reject"))  return "#ff5555";
  if (t.includes("warn"))                                                  return "#ffb86c";
  if (t.includes("trade") || t.includes("open") || t.includes("fill"))    return "#00fd87";
  if (t.includes("close") || t.includes("sl") || t.includes("tp"))        return "#a4ffb9";
  if (t.includes("signal") || t.includes("council") || t.includes("vote")) return "#e966ff";
  if (t.includes("info"))                                                  return "#79dfff";
  return "#adaaaa";
}

function LogRow({
  ev,
  isExpanded,
  onToggle,
}: {
  ev: AgentEvent;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const color       = agentColor(ev.agent);
  const lvlColor    = eventTypeColor(ev.event_type);
  const hasMetadata = ev.metadata && Object.keys(ev.metadata).length > 0;
  const isExecution = ev.agent === "execution";
  const isError     = (ev.event_type ?? "").toLowerCase().includes("error") ||
                      (ev.event_type ?? "").toLowerCase().includes("fail");

  return (
    <div
      style={{
        display:       "flex",
        flexDirection: "column",
        borderLeft:    isExecution ? `2px solid ${color}` : isError ? "2px solid #ff5555" : "2px solid transparent",
        marginBottom:  2,
        background:    isError ? "rgba(255,85,85,0.05)" : undefined,
        borderRadius:  2,
        cursor:        hasMetadata ? "pointer" : "default",
      }}
      onClick={hasMetadata ? onToggle : undefined}
    >
      {/* Main row */}
      <div
        style={{
          display:    "flex",
          alignItems: "flex-start",
          gap:        8,
          padding:    "5px 8px",
        }}
      >
        {/* Timestamp */}
        <span
          style={{
            color:      "#666",
            fontFamily: "monospace",
            fontSize:   10,
            flexShrink: 0,
            paddingTop: 1,
            minWidth:   58,
          }}
        >
          {fmtTime(ev.created_at)}
        </span>

        {/* Agent badge */}
        <span
          style={{
            background:   `${color}22`,
            border:       `1px solid ${color}55`,
            color,
            fontSize:     9,
            fontWeight:   700,
            letterSpacing: "0.08em",
            padding:      "1px 6px",
            borderRadius: 2,
            flexShrink:   0,
            textTransform: "uppercase",
            minWidth:      72,
            textAlign:     "center",
          }}
        >
          {ev.agent}
        </span>

        {/* Event type pill */}
        {ev.event_type && (
          <span
            style={{
              color:        lvlColor,
              fontSize:     9,
              fontWeight:   600,
              letterSpacing: "0.05em",
              padding:      "1px 5px",
              background:   `${lvlColor}18`,
              border:       `1px solid ${lvlColor}33`,
              borderRadius: 2,
              flexShrink:   0,
              textTransform: "uppercase",
              maxWidth:     100,
              overflow:     "hidden",
              whiteSpace:   "nowrap",
              textOverflow: "ellipsis",
            }}
          >
            {ev.event_type}
          </span>
        )}

        {/* Message */}
        <span
          style={{
            color:      isError ? "#ff8888" : "#d8d8d8",
            fontSize:   12,
            fontFamily: "monospace",
            flex:       1,
            lineHeight: 1.5,
            wordBreak:  "break-word",
          }}
        >
          {ev.message}
        </span>

        {/* Expand indicator */}
        {hasMetadata && (
          <span
            style={{
              color:      "#555",
              fontSize:   10,
              flexShrink: 0,
              paddingTop: 2,
              transition: "transform 0.1s",
              transform:  isExpanded ? "rotate(90deg)" : "rotate(0deg)",
              display:    "inline-block",
            }}
          >
            ▶
          </span>
        )}
      </div>

      {/* Expanded metadata panel */}
      {isExpanded && hasMetadata && (
        <div
          style={{
            margin:       "0 8px 6px 74px",
            background:   "#0a0a14",
            border:       "1px solid #1e1e2e",
            borderRadius: 3,
            padding:      "8px 10px",
            maxHeight:    200,
            overflowY:    "auto",
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <pre
            style={{
              margin:     0,
              fontFamily: "monospace",
              fontSize:   11,
              color:      "#c0e8ff",
              whiteSpace: "pre-wrap",
              wordBreak:  "break-word",
            }}
          >
            {JSON.stringify(ev.metadata, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

// ── Agent color map ────────────────────────────────────────────────────────────

const AGENT_COLORS: Record<string, string> = {
  crucix:        "#1cd5ff",
  market:        "#00d2fd",
  analysis:      "#ffffff",
  strategy:      "#00fd87",
  deepseek:      "#e966ff",
  council:       "#ffb86c",
  risk:          "#ff716c",
  execution:     "#ffffff",
  trade_manager: "#a4ffb9",
  learning:      "#79dfff",
  logging:       "#494847",
};

function agentColor(agent: string): string {
  return AGENT_COLORS[agent.toLowerCase()] ?? "#adaaaa";
}


function fmtTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toTimeString().slice(0, 8);
  } catch {
    return "00:00:00";
  }
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AgentTheaterPage() {
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [command, setCommand] = useState("");
  const [sending, setSending] = useState(false);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [agentFilter, setAgentFilter] = useState<string>("all");
  const logRef = useRef<HTMLDivElement>(null);

  function toggleExpanded(id: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  useEffect(() => {
    let active = true;
    const load = () =>
      fetch("/api/events?limit=100")
        .then((r) => r.json())
        .then((data) => {
          if (active && Array.isArray(data)) setEvents(data);
        })
        .catch(() => {});
    load();
    const id = setInterval(load, 2_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  // Auto-scroll log to bottom on new events
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [events]);

  // Metrics derived from events
  const agentSet = useMemo(() => new Set(events.map((e) => e.agent)), [events]);
  const agentCount = agentSet.size;

  const recentWindow = 5 * 60 * 1000; // 5 min
  const recentEvents = useMemo(
    () => events.filter((e) => Date.now() - new Date(e.created_at).getTime() < recentWindow),
    [events]
  );

  const agreementPct = useMemo(() => {
    const councilEvents = recentEvents.filter((e) => e.agent === "council");
    if (councilEvents.length === 0) return 0;
    const approved = councilEvents.filter(
      (e) => (e.metadata as { approved?: boolean })?.approved === true
    ).length;
    return Math.round((approved / councilEvents.length) * 100);
  }, [recentEvents]);

  const entropyScore = (1 - agentCount / 12).toFixed(3);

  async function sendCommand(cmd: string) {
    if (!cmd.trim()) return;
    setSending(true);
    try {
      await fetch("/api/commands", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: cmd.trim() }),
      });
    } catch { /* ignore */ } finally {
      setSending(false);
      setCommand("");
    }
  }

  const filteredEvents = useMemo(
    () => agentFilter === "all" ? events : events.filter((e) => e.agent === agentFilter),
    [events, agentFilter]
  );

  const uniqueAgents = useMemo(
    () => Array.from(new Set(events.map((e) => e.agent))).sort(),
    [events]
  );

  // Support node statuses
  const learningLast = useMemo(
    () => events.find((e) => e.agent === "learning"),
    [events]
  );
  const loggingLast = useMemo(
    () => events.find((e) => e.agent === "logging"),
    [events]
  );

  return (
    <div className="flex flex-col gap-6 mt-6">

      {/* ── Page Header ── */}
      <div className="border-l-4 border-primary-fixed pl-6 py-2 bg-surface-container-low">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-secondary text-[10px] font-bold tracking-[0.2em] uppercase">THEATER</span>
          <span className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
        </div>
        <h1 className="text-3xl md:text-5xl font-extrabold tracking-tighter uppercase mb-2">
          Active Multi-Agent Stream
        </h1>
        <div className="flex items-center gap-4">
          <span className="text-on-surface-variant font-mono text-sm">
            {agentCount} agents synchronized
          </span>
          <span className="h-px flex-1 bg-outline-variant opacity-20" />
          <span className="text-primary-fixed text-sm font-bold">[SYSTEM: NOMINAL]</span>
        </div>
      </div>

      {/* ── Theater Grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">

        {/* Log Stream — 8/12 */}
        <div className="lg:col-span-8 bg-surface-container flex flex-col h-[600px] border border-outline-variant/10">

          {/* Terminal titlebar */}
          <div className="flex items-center justify-between p-3 bg-surface-container-high border-b border-outline-variant/15">
            <div className="flex items-center gap-2">
              <span className="material-symbols-outlined text-primary text-sm" style={{ fontSize: 16 }}>
                terminal
              </span>
              <span className="text-xs font-bold tracking-widest text-on-surface">
                NEURAL_LOG_STREAM_V4
              </span>
              <span
                style={{
                  background: "#00fd8722",
                  border: "1px solid #00fd8755",
                  color: "#00fd87",
                  fontSize: 9,
                  fontWeight: 700,
                  padding: "1px 6px",
                  letterSpacing: "0.1em",
                }}
              >
                LIVE
              </span>
            </div>
            <div className="flex gap-2 items-center">
              <span style={{ color: "#666", fontSize: 10, fontFamily: "monospace" }}>
                {filteredEvents.length} events
              </span>
              <div className="w-3 h-3 bg-error-container" />
              <div className="w-3 h-3 bg-tertiary-container" />
              <div className="w-3 h-3 bg-primary-container" />
            </div>
          </div>

          {/* Agent filter bar */}
          <div
            style={{
              display:        "flex",
              gap:            4,
              padding:        "6px 10px",
              borderBottom:   "1px solid rgba(255,255,255,0.06)",
              background:     "#0d0d1a",
              overflowX:      "auto",
              flexShrink:     0,
            }}
          >
            {["all", ...uniqueAgents].map((a) => (
              <button
                key={a}
                onClick={() => setAgentFilter(a)}
                style={{
                  background:    agentFilter === a
                    ? (a === "all" ? "#ffffff22" : `${agentColor(a)}33`)
                    : "transparent",
                  border:        `1px solid ${agentFilter === a
                    ? (a === "all" ? "#ffffff55" : `${agentColor(a)}88`)
                    : "rgba(255,255,255,0.1)"}`,
                  color:         agentFilter === a
                    ? (a === "all" ? "#fff" : agentColor(a))
                    : "#666",
                  fontSize:      9,
                  fontWeight:    700,
                  letterSpacing: "0.08em",
                  padding:       "2px 8px",
                  cursor:        "pointer",
                  borderRadius:  2,
                  textTransform: "uppercase",
                  transition:    "all 0.1s",
                  flexShrink:    0,
                }}
              >
                {a}
              </button>
            ))}
          </div>

          {/* Log rows */}
          <div
            ref={logRef}
            style={{ flex: 1, overflowY: "auto", padding: "6px 4px" }}
          >
            {filteredEvents.length === 0 ? (
              <div
                style={{
                  color:      "#555",
                  fontSize:   11,
                  fontFamily: "monospace",
                  fontStyle:  "italic",
                  padding:    "16px 12px",
                }}
              >
                {events.length === 0
                  ? "Awaiting telemetry packets..."
                  : `No events from agent: ${agentFilter}`}
              </div>
            ) : (
              [...filteredEvents].reverse().map((ev) => (
                <LogRow
                  key={ev.id}
                  ev={ev}
                  isExpanded={expanded.has(ev.id)}
                  onToggle={() => toggleExpanded(ev.id)}
                />
              ))
            )}
          </div>

          {/* Command input */}
          <div className="p-3 bg-surface-container-lowest border-t border-outline-variant/15 flex items-center gap-3">
            <span className="text-primary-fixed text-xs font-bold">$</span>
            <input
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") sendCommand(command);
              }}
              disabled={sending}
              placeholder={sending ? "SENDING..." : "FORCE_COMMAND_OVERRIDE_ (status / kill / pause / resume)"}
              className="bg-transparent border-none text-xs font-mono focus:ring-0 focus:outline-none w-full p-0 text-primary placeholder:text-outline disabled:opacity-40"
            />
          </div>
        </div>

        {/* Right Column — 4/12 */}
        <div className="lg:col-span-4 flex flex-col gap-4">

          {/* Support Nodes */}
          <div className="bg-surface-container p-4 border border-outline-variant/10">
            <h3 className="text-xs font-bold tracking-widest text-on-surface-variant mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined" style={{ fontSize: 14 }}>hub</span>
              SUPPORT_NODES
            </h3>
            <div className="space-y-3">
              {[
                {
                  label: "Learning Agent",
                  sub:   "V-SYNAPSE-09",
                  ev:    learningLast,
                  tag:   "[ANALYZING]",
                  tagColor: "#00d2fd",
                },
                {
                  label: "Logging Node",
                  sub:   "DB-COLLECTOR",
                  ev:    loggingLast,
                  tag:   "[PERSISTING]",
                  tagColor: "#adaaaa",
                },
                {
                  label: "Encryption Hub",
                  sub:   "AES-256-GCM",
                  ev:    null,
                  tag:   "[SECURE]",
                  tagColor: "#a4ffb9",
                },
              ].map(({ label, sub, tag, tagColor }) => (
                <div
                  key={label}
                  className="flex justify-between items-center p-2 bg-surface-container-low border border-outline-variant/5"
                >
                  <div className="flex flex-col">
                    <span className="text-xs text-on-surface">{label}</span>
                    <span className="text-[10px] text-on-surface-variant">{sub}</span>
                  </div>
                  <span
                    className="text-[10px] font-bold px-2 py-0.5 border"
                    style={{
                      color: tagColor,
                      background: `${tagColor}18`,
                      borderColor: `${tagColor}33`,
                    }}
                  >
                    {tag}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* Latency Metric */}
          <div className="bg-surface-container-lowest p-6 border-2 border-outline-variant/20 relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-2 opacity-10 group-hover:opacity-100 transition-opacity duration-300">
              <span className="material-symbols-outlined text-4xl text-secondary">analytics</span>
            </div>
            <div className="relative z-10">
              <span className="text-[10px] uppercase tracking-widest text-on-surface-variant">
                SYNCH_LATENCY
              </span>
              <div className="text-5xl font-extrabold text-surface-tint tracking-tighter my-2">
                0.04<span className="text-lg">ms</span>
              </div>
              <div className="w-full bg-surface-container-high h-1 mt-4">
                <div
                  className="h-full w-3/4 neon-glow-primary-bar"
                  style={{ background: "#00fd87" }}
                />
              </div>
            </div>
          </div>

          {/* Neural Viz placeholder */}
          <div className="relative h-36 bg-surface-container-high border border-outline-variant/10 overflow-hidden">
            <div className="absolute inset-0 flex flex-col justify-between p-3 pointer-events-none select-none">
              {[...Array(8)].map((_, i) => (
                <div
                  key={i}
                  className="h-px"
                  style={{
                    background: `rgba(0,253,135,${0.04 + (i % 3) * 0.03})`,
                  }}
                />
              ))}
            </div>
            <div className="absolute inset-0 bg-gradient-to-t from-surface-container-lowest to-transparent z-10" />
            <div className="absolute bottom-3 left-3 z-20">
              <span className="text-[10px] font-bold text-primary-fixed bg-black/80 px-2 py-1">
                CORE_FEED: {events.length} events
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Neural Consensus Metrics ── */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-2 glass-panel p-6 border-l border-tertiary/30">
          <h4 className="text-tertiary-fixed text-xs font-bold tracking-widest mb-6 uppercase">
            Neural Consensus Metrics
          </h4>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-6">
            {[
              { label: "AGREEMENT",  value: `${agreementPct}%`,    color: agreementPct >= 80 ? "#00fd87" : "#adaaaa" },
              { label: "DIVERGENCE", value: agentCount > 6 ? "Low" : "High", color: "#ff716c" },
              { label: "EPOCH",      value: events.length.toLocaleString(), color: "#ffffff" },
              { label: "ENTROPY",    value: entropyScore,             color: "#00d2fd" },
            ].map(({ label, value, color }) => (
              <div key={label}>
                <div className="text-on-surface-variant text-[10px] mb-1">{label}</div>
                <div className="text-xl font-bold" style={{ color }}>{value}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-surface-container-high p-6 flex flex-col justify-center border-r-4 border-secondary">
          <p className="text-[11px] text-on-surface-variant font-mono leading-relaxed">
            Agent Theater utilizes a synchronized clock to ensure all sub-modules operate
            on a shared truth. Any deviation above 5ms triggers immediate reconciliation
            via the Learning Agent.
          </p>
          <button
            onClick={() => sendCommand("status")}
            className="mt-4 bg-secondary text-on-secondary font-bold text-[10px] py-2 px-4 uppercase tracking-widest hover:opacity-90 duration-0 self-start"
          >
            RECALIBRATE_NODES
          </button>
        </div>
      </section>
    </div>
  );
}
