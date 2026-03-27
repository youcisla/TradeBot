"use client";

import { useEffect, useMemo, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface BotStatus {
  state: string; equity: number; daily_pnl: number;
  open_trades: number; balance: number; last_tick: string | null;
}

interface WorldData {
  available: boolean; riskTier?: string; vix?: number;
  osintSentiment?: string;
}

interface Confidence {
  strategy: string; confidence: number; wins: number; losses: number;
}

interface AgentEvent {
  agent: string; event_type: string; message: string;
  created_at: string; metadata?: Record<string, unknown>;
}

// ── Pipeline agents shown in the Neural Pipeline strip ────────────────────────

const PIPELINE_AGENTS = [
  { key: "crucix",        label: "Crucix",    color: "#1cd5ff" },
  { key: "market",        label: "Market",    color: "#00d2fd" },
  { key: "analysis",      label: "Analysis",  color: "#ffffff" },
  { key: "strategy",      label: "Strategy",  color: "#00fd87" },
  { key: "deepseek",      label: "DeepSeek",  color: "#e966ff" },
  { key: "council",       label: "Council",   color: "#ffb86c" },
  { key: "risk",          label: "Risk",      color: "#ff716c" },
  { key: "execution",     label: "Execution", color: "#ffffff" },
  { key: "trade_manager", label: "TradeMgr",  color: "#a4ffb9" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function statusIcon(msg: string, ts: string | undefined): { icon: string; color: string } {
  if (!ts) return { icon: "💤", color: "#494847" };
  const ageMin = (Date.now() - new Date(ts).getTime()) / 60_000;
  if (ageMin > 10) return { icon: "💤", color: "#494847" };
  const lower = msg.toLowerCase();
  if (lower.includes("error") || lower.includes("fail") || lower.includes("reject"))
    return { icon: "❌", color: "#ff716c" };
  if (lower.includes("warn") || lower.includes("spread") || lower.includes("stale"))
    return { icon: "⚠️", color: "#ffb86c" };
  if (lower.includes("processing") || lower.includes("analyzing") || lower.includes("waiting"))
    return { icon: "🔄", color: "#00d2fd" };
  return { icon: "✅", color: "#00fd87" };
}

function lotScaleFromTier(tier?: string): string {
  if (tier === "FLASH")    return "0.50x";
  if (tier === "PRIORITY") return "0.75x";
  return "1.00x";
}

function tierColor(tier?: string): string {
  if (tier === "FLASH")    return "#ff716c";
  if (tier === "PRIORITY") return "#ffb86c";
  if (tier === "ROUTINE")  return "#00d2fd";
  return "#00fd87";
}

function sentimentColor(s?: string): string {
  if (s === "bearish") return "#ff716c";
  if (s === "bullish") return "#00fd87";
  return "#adaaaa";
}

// ── Sub-components ────────────────────────────────────────────────────────────

function CardHeader({ label, icon }: { label: string; icon: string }) {
  return (
    <div className="flex justify-between items-start mb-6">
      <span className="text-[10px] font-bold tracking-[0.2em] uppercase text-on-surface-variant">
        {label}
      </span>
      <span className="material-symbols-outlined text-on-surface-variant" style={{ fontSize: 18 }}>
        {icon}
      </span>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function CommandCenterPage() {
  const [status, setStatus]           = useState<BotStatus | null>(null);
  const [world, setWorld]             = useState<WorldData | null>(null);
  const [confidences, setConfidences] = useState<Confidence[]>([]);
  const [events, setEvents]           = useState<AgentEvent[]>([]);

  useEffect(() => {
    let active = true;

    const fetchAll = () => {
      Promise.allSettled([
        fetch("/api/status").then((r) => r.json()),
        fetch("/api/world").then((r) => r.json()),
        fetch("/api/learning").then((r) => r.json()),
        fetch("/api/events?limit=200").then((r) => r.json()),
      ]).then(([s, w, l, e]) => {
        if (!active) return;
        if (s.status === "fulfilled") setStatus(s.value);
        if (w.status === "fulfilled") setWorld(w.value);
        if (l.status === "fulfilled") setConfidences(l.value?.confidences ?? []);
        if (e.status === "fulfilled") setEvents(Array.isArray(e.value) ? e.value : []);
      });
    };

    fetchAll();
    const id = setInterval(fetchAll, 5_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  // Latest event per agent key
  const agentLatest = useMemo(() => {
    const map: Record<string, AgentEvent> = {};
    for (const ev of events) {
      if (!map[ev.agent]) map[ev.agent] = ev;
    }
    return map;
  }, [events]);

  const dailyPnl  = Number(status?.daily_pnl ?? 0);
  const equity    = Number(status?.equity ?? 0);
  const isRunning = status?.state === "running";

  // Strategy confidence helpers
  const confMap = useMemo(() => {
    const m: Record<string, number> = {};
    for (const c of confidences) m[c.strategy] = Number(c.confidence);
    return m;
  }, [confidences]);

  const STRATS = [
    { key: "deepseek", label: "deepseek_engine",  color: "#00fd87" },
    { key: "ict",      label: "ict_internal",      color: "#00fd87" },
    { key: "sma",      label: "sma_convergence",   color: "#494847" },
  ];

  return (
    <div className="flex flex-col gap-6 mt-6">

      {/* ── Page Header ── */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="text-[10px] font-bold text-primary-fixed tracking-widest uppercase">
              OVERVIEW
            </span>
            <div className="h-px w-8 bg-primary-fixed/30" />
          </div>
          <h1 className="text-3xl md:text-4xl font-extrabold uppercase tracking-tighter text-on-surface">
            Command Center
          </h1>
        </div>
        <div className="flex items-center gap-4 text-[10px] font-bold">
          <div className="flex items-center gap-2 px-3 py-1 bg-surface-container-high border border-primary-container/20">
            <span className={`w-1.5 h-1.5 rounded-full ${isRunning ? "bg-primary-fixed animate-pulse" : "bg-error"}`} />
            <span className="text-on-surface-variant">Bot:</span>
            <span className={isRunning ? "text-primary-fixed" : "text-error"}>
              [{status?.state?.toUpperCase() ?? "OFFLINE"}]
            </span>
          </div>
          <div className="flex items-center gap-2 px-3 py-1 bg-surface-container-high border border-outline-variant/20">
            <span className="text-on-surface-variant">Loop:</span>
            <span className="text-on-surface">30s</span>
          </div>
        </div>
      </div>

      {/* ── Top 3 Cards ── */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-12 gap-4">

        {/* MACRO_INTEL */}
        <div className="lg:col-span-4 bg-surface border-l-2 border-secondary-fixed-dim p-5 flex flex-col justify-between min-h-[220px]">
          <div className="flex justify-between items-start mb-6">
            <span className="text-[10px] text-secondary-fixed-dim font-bold tracking-[0.2em]">
              MACRO_INTEL
            </span>
            <span className="material-symbols-outlined text-secondary-fixed-dim" style={{ fontSize: 20 }}>
              insights
            </span>
          </div>
          <div className="grid grid-cols-2 gap-y-6">
            <div>
              <p className="text-[10px] text-on-surface-variant uppercase mb-1">Crucix Tier</p>
              <p className="text-xl font-bold tracking-tight" style={{ color: tierColor(world?.riskTier) }}>
                [{world?.riskTier ?? "—"}]
              </p>
            </div>
            <div>
              <p className="text-[10px] text-on-surface-variant uppercase mb-1">VIX Index</p>
              <p className="text-xl font-bold text-on-surface">
                {world?.vix != null ? world.vix.toFixed(1) : "—"}
              </p>
            </div>
            <div>
              <p className="text-[10px] text-on-surface-variant uppercase mb-1">Sentiment</p>
              <p className="text-xl font-bold uppercase" style={{ color: sentimentColor(world?.osintSentiment) }}>
                [{world?.osintSentiment?.toUpperCase() ?? "NEUTRAL"}]
              </p>
            </div>
            <div>
              <p className="text-[10px] text-on-surface-variant uppercase mb-1">Lot Scale</p>
              <p className="text-xl font-bold text-on-surface">
                {lotScaleFromTier(world?.riskTier)}
              </p>
            </div>
          </div>
        </div>

        {/* PERFORMANCE_LEDGER */}
        <div className="lg:col-span-4 bg-surface border-l-2 border-secondary p-5 flex flex-col justify-between min-h-[220px]">
          <div className="flex justify-between items-start mb-6">
            <span className="text-[10px] text-secondary font-bold tracking-[0.2em]">
              PERFORMANCE_LEDGER
            </span>
            <span className="material-symbols-outlined text-secondary" style={{ fontSize: 20 }}>
              analytics
            </span>
          </div>
          <div className="space-y-4">
            <div className="flex justify-between items-end">
              <div>
                <p className="text-[10px] text-on-surface-variant uppercase mb-1">Daily PnL</p>
                <p className={`text-3xl font-bold ${dailyPnl >= 0 ? "text-primary-fixed" : "text-error"}`}>
                  {dailyPnl >= 0 ? "+" : ""}${dailyPnl.toFixed(2)}
                </p>
              </div>
              <div className="text-right">
                <p className={`text-xs font-bold px-2 py-0.5 tracking-tighter ${dailyPnl >= 0 ? "text-primary-fixed bg-primary-fixed/10" : "text-error bg-error/10"}`}>
                  {equity && status?.balance
                    ? `${(((equity - Number(status.balance)) / Number(status.balance)) * 100).toFixed(1)}%`
                    : "—"
                  }
                </p>
              </div>
            </div>
            <div className="h-px bg-outline-variant/10 w-full" />
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-[10px] text-on-surface-variant uppercase">Equity</p>
                <p className="text-sm font-bold text-on-surface">
                  ${equity.toLocaleString("en", { maximumFractionDigits: 2 })}
                </p>
              </div>
              <div>
                <p className="text-[10px] text-on-surface-variant uppercase">Open Trades</p>
                <p className="text-sm font-bold text-on-surface">
                  {status?.open_trades ?? 0}
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* STRATEGY_CONFIDENCE */}
        <div className="lg:col-span-4 bg-surface border-l-2 border-primary-container p-5 min-h-[220px]">
          <div className="flex justify-between items-start mb-6">
            <span className="text-[10px] text-primary-container font-bold tracking-[0.2em]">
              STRATEGY_CONFIDENCE
            </span>
            <span className="material-symbols-outlined text-primary-container" style={{ fontSize: 20 }}>
              psychology
            </span>
          </div>
          <div className="space-y-5">
            {STRATS.map(({ key, label, color }) => {
              const conf = confMap[key] ?? 0;
              const pct  = Math.round(conf * 100);
              return (
                <div key={key} className="space-y-2">
                  <div className="flex justify-between items-center text-[10px]">
                    <span className="text-on-surface-variant uppercase">{label}</span>
                    <span className="font-bold" style={{ color: pct >= 50 ? "#00fd87" : "#adaaaa" }}>
                      {conf.toFixed(2)}
                    </span>
                  </div>
                  <div className="w-full h-1 bg-surface-container-highest">
                    <div
                      className="h-full transition-all duration-500"
                      style={{ width: `${pct}%`, background: color }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* NEURAL_PIPELINE */}
        <div className="lg:col-span-12 bg-surface p-5 border border-outline-variant/10">
          <div className="flex items-center gap-3 mb-6">
            <span className="text-[10px] text-on-surface-variant font-bold tracking-[0.2em]">
              NEURAL_PIPELINE
            </span>
            <div className="flex-grow h-px bg-outline-variant/10" />
            {isRunning && (
              <span className="text-[10px] text-primary-fixed font-bold uppercase animate-pulse">
                STREAMING DATA
              </span>
            )}
          </div>
          <div className="grid grid-cols-3 md:grid-cols-5 lg:grid-cols-9 gap-3">
            {PIPELINE_AGENTS.map(({ key, label, color }) => {
              const ev   = agentLatest[key];
              const msg  = ev?.message ?? "NO_EVENTS";
              const { icon, color: iconColor } = statusIcon(msg, ev?.created_at);
              return (
                <div
                  key={key}
                  className="bg-surface-container-low p-3 border border-outline-variant/5 hover:border-primary-container/30 duration-0"
                >
                  <div className="flex justify-between items-start mb-2">
                    <span className="text-[9px] font-bold" style={{ color }}>
                      {label}
                    </span>
                    <span style={{ color: iconColor, fontSize: 11 }}>{icon}</span>
                  </div>
                  <div className="text-[10px] text-on-surface font-medium truncate">
                    {msg.slice(0, 24).toUpperCase()}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* TERMINAL VISUAL — decorative HUD footer */}
        <div className="lg:col-span-12 h-40 bg-surface-container-low border border-outline-variant/10 relative overflow-hidden">
          <div className="absolute inset-0 flex flex-col justify-center px-6 gap-1 opacity-20 select-none pointer-events-none">
            {["01001110 01000101 01010101 01010010 01000001 01001100",
              "01000110 01011000 00100000 01010100 01010010 01000001",
              "01000100 01000101 01010010 00100000 01010110 00110100"].map((line, i) => (
              <p key={i} className="text-[9px] font-mono text-primary-fixed tracking-widest">
                {line}
              </p>
            ))}
          </div>
          <div className="absolute inset-0 bg-gradient-to-r from-surface-container-low via-transparent to-surface-container-low" />
          <div className="absolute bottom-4 left-6">
            <p className="text-[10px] text-primary-fixed font-bold uppercase tracking-[0.3em] mb-1">
              Neural_Vis_Engine_v4
            </p>
            <p className="text-[10px] text-on-surface-variant">
              {events.length} events in buffer · pipeline nominal
            </p>
          </div>
          <div className="absolute top-4 right-6 flex flex-col items-end gap-1">
            <div className="flex items-center gap-2">
              <span className="text-[9px] text-on-surface-variant">LATENCY</span>
              <span className="text-[10px] font-bold text-secondary-fixed-dim">0.04ms</span>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[9px] text-on-surface-variant">AGENTS</span>
              <span className="text-[10px] font-bold text-primary-fixed">{PIPELINE_AGENTS.length} ONLINE</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
