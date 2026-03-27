"use client";

import { useEffect, useMemo, useRef, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgentEvent {
  id: string; agent: string; event_type: string;
  message: string; created_at: string;
  metadata?: Record<string, unknown>;
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

function agentLabel(agent: string): string {
  return `[${agent.toUpperCase()}]`;
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
  const logRef = useRef<HTMLDivElement>(null);

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
            </div>
            <div className="flex gap-2">
              <div className="w-3 h-3 bg-error-container" />
              <div className="w-3 h-3 bg-tertiary-container" />
              <div className="w-3 h-3 bg-primary-container" />
            </div>
          </div>

          {/* Log rows */}
          <div
            ref={logRef}
            className="flex-1 overflow-y-auto p-4 font-mono text-sm space-y-1"
          >
            {events.length === 0 ? (
              <div className="text-on-surface-variant text-[11px] opacity-50 italic p-2">
                Awaiting telemetry packets...
              </div>
            ) : (
              [...events].reverse().map((ev, i) => (
                <div
                  key={ev.id ?? i}
                  className={`group flex gap-3 hover:bg-surface-bright p-1 duration-0 ${
                    i % 7 === 0 ? "bg-surface-container-high" : ""
                  } ${ev.agent === "execution" ? "border-l-2 border-primary-fixed ml-1 pl-2" : ""}`}
                >
                  <span className="text-on-surface-variant shrink-0 text-[11px]">
                    [{fmtTime(ev.created_at)}]
                  </span>
                  <span
                    className="shrink-0 text-[11px] font-bold"
                    style={{ color: agentColor(ev.agent) }}
                  >
                    {agentLabel(ev.agent)}
                  </span>
                  <span className="text-on-surface text-[11px] break-all">
                    {ev.message}
                  </span>
                </div>
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
