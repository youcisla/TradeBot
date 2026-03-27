"use client";

import { useEffect, useMemo, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgentEvent {
  id: string; agent: string; event_type: string;
  message: string; created_at: string;
  metadata?: {
    symbol?: string; direction?: string; confidence?: number;
    entry?: number; sl?: number; tp1?: number; tp2?: number; tp3?: number;
    reason?: string; setup?: string; session?: string;
    ict_score?: number; danial_score?: number; traditional_score?: number;
    approved?: boolean; avg_score?: number;
  };
}

interface Confidence {
  strategy: string; confidence: number; wins: number; losses: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n?: number, dec = 5): string {
  if (n == null) return "—";
  return n.toFixed(dec);
}

function confColor(conf?: number): string {
  if (!conf) return "#adaaaa";
  if (conf >= 0.80) return "#00fd87";
  if (conf >= 0.65) return "#e966ff";
  return "#ff716c";
}

function dirColor(dir?: string): string {
  return dir === "BUY" ? "#00fd87" : dir === "SELL" ? "#ff716c" : "#adaaaa";
}

function latestSignal(events: AgentEvent[], agent: string): AgentEvent | null {
  return events.find((e) => e.agent === agent && e.metadata?.direction) ?? null;
}

function latestCouncil(events: AgentEvent[]): AgentEvent | null {
  return events.find((e) => e.agent === "council" && e.metadata?.approved != null) ?? null;
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function StrategyIntelligencePage() {
  const [events, setEvents]           = useState<AgentEvent[]>([]);
  const [confidences, setConfidences] = useState<Confidence[]>([]);

  useEffect(() => {
    let active = true;
    const load = () => {
      Promise.allSettled([
        fetch("/api/events?limit=300").then((r) => r.json()),
        fetch("/api/learning").then((r) => r.json()),
      ]).then(([e, l]) => {
        if (!active) return;
        if (e.status === "fulfilled") setEvents(Array.isArray(e.value) ? e.value : []);
        if (l.status === "fulfilled") setConfidences(l.value?.confidences ?? []);
      });
    };
    load();
    const id = setInterval(load, 8_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  const dsSignal       = useMemo(() => latestSignal(events, "deepseek"), [events]);
  const ictSignal      = useMemo(() => latestSignal(events, "ict"),      [events]);
  const councilVerdict = useMemo(() => latestCouncil(events),            [events]);

  const confMap = useMemo(() => {
    const m: Record<string, Confidence> = {};
    for (const c of confidences) m[c.strategy] = c;
    return m;
  }, [confidences]);

  const history = useMemo(
    () => events.filter((e) => e.metadata?.direction).slice(0, 12),
    [events]
  );

  const ds = dsSignal?.metadata;
  const ict = ictSignal?.metadata;
  const cv  = councilVerdict?.metadata;

  return (
    <div className="flex flex-col gap-6 mt-6">

      {/* ── Page Header ── */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <span className="text-secondary font-bold tracking-widest text-xs mb-1 block">STRATEGY</span>
          <h1 className="text-3xl md:text-5xl font-extrabold uppercase tracking-tighter">
            DeepSeek + ICT Engine
          </h1>
        </div>
        <div className="flex items-center gap-4 bg-surface-container-high p-4 border-l-2 border-primary-container">
          <div>
            <span className="text-on-surface-variant text-[10px] block">STATUS</span>
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
              <span className="font-bold text-sm">
                {[dsSignal, ictSignal].filter(Boolean).length} Active Signal
                {[dsSignal, ictSignal].filter(Boolean).length !== 1 ? "s" : ""}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Strategy Grid ── */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-1 bg-outline-variant/10">

        {/* DeepSeek Signal — 8/12 */}
        <div className="md:col-span-8 bg-surface p-6 flex flex-col gap-6">
          <div className="flex justify-between items-start">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-tertiary" style={{ fontSize: 18 }}>
                  psychology
                </span>
                <span className="text-tertiary font-bold tracking-wider text-sm uppercase">
                  DeepSeek Signal
                </span>
              </div>
              {ds ? (
                <h2 className="text-4xl font-black text-on-surface">
                  {ds.symbol ?? "—"}{" "}
                  <span style={{ color: dirColor(ds.direction) }}>{ds.direction ?? "—"}</span>
                </h2>
              ) : (
                <h2 className="text-3xl font-black text-on-surface-variant uppercase">
                  No_Signal
                </h2>
              )}
            </div>
            <div className="text-right">
              <span className="text-[10px] text-on-surface-variant block uppercase">Confidence</span>
              <span className="text-2xl font-bold" style={{ color: confColor(ds?.confidence) }}>
                {ds?.confidence != null ? `${Math.round(ds.confidence * 100)}%` : "—"}
              </span>
            </div>
          </div>

          {/* Entry / SL / TP / RR */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 py-4 border-y border-outline-variant/15">
            {[
              { label: "ENTRY", value: fmt(ds?.entry),  color: "#ffffff" },
              { label: "SL",    value: fmt(ds?.sl),     color: "#ff716c" },
              { label: "TP1",   value: fmt(ds?.tp1),    color: "#a4ffb9" },
              {
                label: "RR RATIO",
                value: ds?.entry && ds?.sl && ds?.tp1
                  ? `1:${(Math.abs(ds.tp1 - ds.entry) / Math.abs(ds.entry - ds.sl)).toFixed(2)}`
                  : "—",
                color: "#ffffff",
              },
            ].map(({ label, value, color }) => (
              <div key={label}>
                <span className="text-[10px] text-on-surface-variant block">{label}</span>
                <span className="text-lg font-bold" style={{ color }}>{value}</span>
              </div>
            ))}
          </div>

          {/* Neural reasoning */}
          <div className="bg-surface-container-low p-4 border-l-4 border-tertiary">
            <span className="text-[10px] text-tertiary font-bold block mb-2 uppercase tracking-widest">
              Neural Logic Output
            </span>
            <p className="text-sm leading-relaxed text-on-surface-variant">
              {ds?.reason ?? dsSignal?.message ?? "Awaiting next DeepSeek inference cycle..."}
            </p>
          </div>

          {/* Strategy confidence bars */}
          <div className="grid grid-cols-3 gap-3">
            {[
              { key: "deepseek", label: "DeepSeek", color: "#e966ff" },
              { key: "ict",      label: "ICT",      color: "#00d2fd" },
              { key: "sma",      label: "SMA",      color: "#494847" },
            ].map(({ key, label, color }) => {
              const c   = confMap[key];
              const pct = c ? Math.round(c.confidence * 100) : 0;
              return (
                <div key={key} className="bg-surface-container-low p-3">
                  <div className="flex justify-between text-[10px] mb-2">
                    <span className="text-on-surface-variant uppercase">{label}</span>
                    <span className="font-bold" style={{ color }}>{pct}%</span>
                  </div>
                  <div className="w-full h-px bg-surface-container-highest">
                    <div className="h-full" style={{ width: `${pct}%`, background: color }} />
                  </div>
                  {c && (
                    <div className="flex gap-3 mt-2 text-[9px] text-on-surface-variant">
                      <span className="text-primary-container">{c.wins}W</span>
                      <span className="text-error">{c.losses}L</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Council Review — 4/12 */}
        <div className="md:col-span-4 bg-surface-container-high p-6 flex flex-col justify-between border-l border-outline-variant/10">
          <div>
            <div className="flex items-center gap-2 mb-6">
              <span className="material-symbols-outlined" style={{ color: "#ffb86c", fontSize: 18 }}>
                verified
              </span>
              <span className="font-bold tracking-wider text-sm uppercase" style={{ color: "#ffb86c" }}>
                Council Review
              </span>
            </div>

            <div className="space-y-6">
              {[
                { label: "ICT Expert",  score: cv?.ict_score },
                { label: "Traditional", score: cv?.traditional_score },
                { label: "DanialFX",    score: cv?.danial_score },
              ].map(({ label, score }) => {
                const pct   = score != null ? Math.round(score * 100) : 0;
                const color = pct >= 80 ? "#00fd87" : pct >= 65 ? "#00d2fd" : "#ff716c";
                return (
                  <div key={label} className="flex items-center justify-between">
                    <span className="text-xs text-on-surface">{label}</span>
                    <div className="flex items-center gap-3">
                      <div className="w-28 h-1 bg-surface-container-lowest">
                        <div className="h-full" style={{ width: `${pct}%`, background: color }} />
                      </div>
                      <span className="text-sm font-bold w-8 text-right" style={{ color }}>
                        {score != null ? score.toFixed(2) : "—"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div
            className="mt-12 p-4 border text-center"
            style={{
              borderColor: cv?.approved ? "rgba(255,184,108,0.3)" : "rgba(255,113,108,0.3)",
              background:  cv?.approved ? "rgba(255,184,108,0.08)" : "rgba(255,113,108,0.08)",
            }}
          >
            {cv != null ? (
              <>
                <span className="font-black text-xl tracking-tighter block" style={{ color: "#ffb86c" }}>
                  SIGNAL {cv.approved ? "APPROVED ✅" : "REJECTED ❌"}
                </span>
                {cv.avg_score != null && (
                  <span className="text-[10px] text-on-surface-variant mt-1 block">
                    avg score: {cv.avg_score.toFixed(2)}
                  </span>
                )}
              </>
            ) : (
              <span className="text-on-surface-variant text-[11px] uppercase tracking-widest">
                AWAITING REVIEW
              </span>
            )}
          </div>
        </div>

        {/* ICT Signal — full width */}
        {ict && (
          <div className="md:col-span-12 bg-surface p-6 border-t border-outline-variant/10">
            <div className="flex flex-col md:flex-row gap-8">
              <div className="flex-1 space-y-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="material-symbols-outlined text-secondary" style={{ fontSize: 18 }}>
                      swap_horiz
                    </span>
                    <span className="text-secondary font-bold tracking-wider text-sm uppercase">
                      ICT Signal
                    </span>
                  </div>
                  <span className="text-2xl font-bold text-secondary">
                    {ict.confidence != null ? `${Math.round(ict.confidence * 100)}%` : "—"}
                    <span className="text-[10px] text-on-surface-variant font-normal uppercase ml-1">CONF</span>
                  </span>
                </div>
                <h2 className="text-4xl font-black text-on-surface uppercase">
                  {ict.symbol ?? "—"}{" "}
                  <span style={{ color: dirColor(ict.direction) }}>{ict.direction ?? "—"}</span>
                </h2>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6 py-4">
                  {[
                    { label: "Entry",   value: fmt(ict.entry),    color: "#ffffff" },
                    { label: "Stop",    value: fmt(ict.sl),       color: "#ff716c" },
                    { label: "Session", value: ict.session ?? "—", color: "#ffffff" },
                    { label: "Setup",   value: ict.setup ?? "—",   color: "#ffffff" },
                  ].map(({ label, value, color }) => (
                    <div key={label} className="border-l border-outline-variant/30 pl-3">
                      <span className="text-[10px] text-on-surface-variant block uppercase">{label}</span>
                      <span className="text-xl font-bold" style={{ color }}>{value}</span>
                    </div>
                  ))}
                </div>
              </div>
              <div className="md:w-1/3">
                <div className="h-full bg-surface-container-low p-4 relative min-h-[100px]">
                  <span className="text-[10px] text-secondary font-bold block mb-2 uppercase">
                    Market Context
                  </span>
                  <p className="text-xs text-on-surface-variant italic leading-relaxed">
                    {ictSignal?.message ?? "Awaiting ICT analysis..."}
                  </p>
                  <div className="absolute bottom-2 right-2 flex gap-1 items-end">
                    <div className="w-1 h-4 bg-secondary-container/50" />
                    <div className="w-1 h-6 bg-secondary" />
                    <div className="w-1 h-3 bg-secondary-container/50" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* ── Neural History Log ── */}
      <div>
        <h3 className="text-xs font-bold text-on-surface-variant mb-4 tracking-[0.3em] uppercase">
          Neural History Log
        </h3>
        <div className="space-y-1">
          {history.length === 0 ? (
            <div className="p-4 bg-surface-container-low text-[11px] text-on-surface-variant text-center uppercase tracking-widest">
              NO SIGNAL HISTORY
            </div>
          ) : (
            history.map((ev) => {
              const dir = ev.metadata?.direction;
              const conf = ev.metadata?.confidence;
              return (
                <div
                  key={ev.id}
                  className="flex items-center justify-between p-3 bg-surface-container-low hover:bg-surface-bright duration-0"
                >
                  <div className="flex items-center gap-4">
                    <span className="text-[10px] text-outline font-mono">
                      {ev.created_at
                        ? new Date(ev.created_at).toTimeString().slice(0, 8)
                        : "—"}
                    </span>
                    <span className="text-xs font-bold">
                      {ev.metadata?.symbol ?? ev.agent.toUpperCase()}
                    </span>
                    <span
                      className="text-[9px] font-bold uppercase"
                      style={{ color: dirColor(dir) }}
                    >
                      {dir ?? "—"}
                    </span>
                    <span className="text-[10px] bg-primary/10 text-primary px-2 py-0.5 uppercase">
                      {ev.agent}
                    </span>
                  </div>
                  <span className="text-xs font-bold text-on-surface-variant">
                    {conf != null ? `${Math.round(conf * 100)}%` : "—"}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>

    </div>
  );
}
