"use client";

import { useBotStatus, useOpenTrades, useSignals, useEvents, useIntelligence, useLearning } from "@/lib/swr";
import { confTier, dirChip, verdictHue } from "@/lib/handoff";
import { Chip, Sdot } from "@/components/ui/chip";

function fmtRel(ts: string) {
  const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000);
  if (diff < 60) return `${diff}s`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m`;
  return `${Math.floor(diff / 3600)}h`;
}

function EquityMini({ data }: { data: number[] }) {
  const w = 800;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const r = max - min || 1;
  const pts = data.map((v, i) => [
    (i / (data.length - 1)) * w,
    ((v - min) / r),
  ]);
  const path = "M " + pts.map((p) => p.join(",")).join(" L ");
  return (
    <svg
      className="eq-svg"
      viewBox={`0 0 ${w} 1`}
      preserveAspectRatio="none"
      style={{ width: "100%", display: "block" }}
    >
      <path
        d={path}
        fill="none"
        stroke="var(--accent-warm)"
        strokeWidth="0.005"
      />
    </svg>
  );
}

// Fallback flat equity line when no history is available
function EquityPlaceholder({ equity }: { equity: number }) {
  const w = 800;
  const mid = 0.5;
  const pts = [0, 0.25, 0.5, 0.75, 1].map((t, i) => [
    t * w,
    mid + (i % 2 === 0 ? -0.02 : 0.02),
  ]);
  const path = "M " + pts.map((p) => p.join(",")).join(" L ");
  return (
    <svg
      className="eq-svg"
      viewBox={`0 0 ${w} 1`}
      preserveAspectRatio="none"
      style={{ width: "100%", display: "block" }}
    >
      <path
        d={path}
        fill="none"
        stroke="var(--accent-warm)"
        strokeWidth="0.005"
      />
    </svg>
  );
}

export default function MissionPage() {
  const { data: status } = useBotStatus();
  const { data: trades } = useOpenTrades();
  const { data: signals } = useSignals("EXECUTION", 10);
  const { data: events } = useEvents(50);
  const { data: intel } = useIntelligence();
  const { data: learning } = useLearning();

  const equity     = typeof status?.equity === "number" ? status.equity : 0;
  const balance    = typeof status?.balance === "number" ? status.balance : 0;
  const dailyPnl  = typeof status?.daily_pnl === "number" ? status.daily_pnl : 0;
  const openTrades = status?.open_trades ?? 0;
  const botState   = status?.state ?? "—";
  const loopMs     = (status as unknown as Record<string, unknown>)?.last_scan_latency_ms as number | undefined;

  const denominator = equity - dailyPnl;
  const dayPnlPct = balance > 0 && denominator !== 0 ? (dailyPnl / denominator) * 100 : 0;

  // Top 5 ranked signals (already sorted by confidence desc from DB)
  const topSignals = (signals ?? []).slice(0, 5);

  // Recent events (most recent first)
  const recentEvents = (events ?? []).slice(0, 12);

  // Live positions from open trades
  const positions = (trades ?? []).filter(t => t.status === "OPEN" || t.status === "PARTIAL");

  // Strategy confidences for learning panel
  const confidences = learning?.confidences ?? [];

  // Macro fields from intelligence
  const regime    = intel?.marketRegime ?? "—";
  const vix       = intel?.vix ?? null;
  const session    = intel?.sessionLabel ?? "—";
  const spreadCond = intel?.spreadCondition ?? "—";

  // Exposure: aggregate lots by direction per symbol
  const exposure: Record<string, { long: number; short: number; dir: string }> = {};
  for (const p of positions) {
    if (!exposure[p.symbol]) exposure[p.symbol] = { long: 0, short: 0, dir: "" };
    if (p.direction === "BUY") {
      exposure[p.symbol].long += p.lot_size ?? 0;
      exposure[p.symbol].dir = "BUY";
    } else {
      exposure[p.symbol].short += p.lot_size ?? 0;
      exposure[p.symbol].dir = "SELL";
    }
  }
  const netExposure = Object.values(exposure).reduce((s, e) => {
    const net = e.long - e.short;
    return s + (e.long > 0 ? net : net);
  }, 0);

  return (
    <div className="page">
      {/* page-head */}
      <div className="page-head">
        <div>
          <div className="crumbs">Console · live</div>
          <h1>Mission Control</h1>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span className="hint">
            Last iteration <span className="mono">{loopMs != null ? `${Math.round(loopMs)}ms` : "—"}</span>
          </span>
          <button className="btn ghost">
            <RefreshIcon />
            <span style={{ marginLeft: 4 }}>Force cycle</span>
          </button>
          <button className="btn">
            <PauseIcon />
            <span style={{ marginLeft: 4 }}>Pause</span>
          </button>
          <button className="btn danger">
            <StopIcon />
            <span style={{ marginLeft: 4 }}>Close all</span>
          </button>
        </div>
      </div>

      {/* KPI strip */}
      <div className="kpi-strip">
        <div className="kpi-cell">
          <span className="label">Daily P&amp;L</span>
          <span className="v" style={{ color: dailyPnl >= 0 ? "var(--pos)" : "var(--neg)" }}>
            {dailyPnl >= 0 ? "+" : "−"}${Math.abs(dailyPnl).toFixed(2)}
          </span>
          <span className="sub">
            {dayPnlPct >= 0 ? "+" : ""}{dayPnlPct.toFixed(2)}%
          </span>
        </div>
        <div className="kpi-cell">
          <span className="label">Equity</span>
          <span className="v">
            ${equity.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
          </span>
          <span className="sub">balance ${balance.toLocaleString("en-US")}</span>
        </div>
        <div className="kpi-cell">
          <span className="label">Open / Pending</span>
          <span className="v">
            {openTrades}
            <span className="dim" style={{ fontSize: 14, marginLeft: 6 }}>
              / {(signals ?? []).filter(s => s.signal_intent === "QUEUED" || s.signal_intent === "PENDING").length}
            </span>
          </span>
          <span className="sub">
            {(signals ?? []).filter(s => s.signal_intent === "QUEUED").length} queued
          </span>
        </div>
        <div className="kpi-cell">
          <span className="label">Risk used (day)</span>
          <span className="v">—</span>
          <span className="sub">cap 5.00%</span>
        </div>
        <div className="kpi-cell">
          <span className="label">Macro tier</span>
          <span className="v" style={{ color: "var(--warning)" }}>
            {(intel?.session ?? "—").toUpperCase()}
          </span>
          <span className="sub">spread {spreadCond}</span>
        </div>
      </div>

      {/* 3-column grid */}
      <div className="mc-grid">
        {/* LEFT */}
        <div className="col">
          {/* Live positions */}
          <div className="card">
            <div className="card-head">
              <span className="card-title">
                <span className="dot" />
                Live positions
              </span>
              <a href="/dashboard/trades" className="hint">
                View all →
              </a>
            </div>
            <div className="card-body flush">
              {positions.length === 0 ? (
                <div style={{ padding: "24px 16px", textAlign: "center", color: "var(--fg-3)", fontSize: 13 }}>
                  No open positions
                </div>
              ) : (
                positions.map((p) => (
                  <div
                    key={p.id}
                    style={{
                      padding: "12px 16px",
                      borderBottom: "1px solid var(--border)",
                    }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center",
                        marginBottom: 6,
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span className="mono" style={{ fontSize: 13, fontWeight: 500 }}>
                          {p.symbol}
                        </span>
                        <Chip tone={dirChip(p.direction)}>{p.direction}</Chip>
                      </div>
                      <span
                        className="mono tnum"
                        style={{
                          color: (p.pnl ?? 0) >= 0 ? "var(--pos)" : "var(--neg)",
                          fontSize: 13,
                          fontWeight: 500,
                        }}
                      >
                        {(p.pnl ?? 0) >= 0 ? "+" : "−"}$
                        {Math.abs(p.pnl ?? 0).toFixed(2)}
                      </span>
                    </div>
                    <div
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        fontSize: 11,
                        color: "var(--fg-3)",
                        marginBottom: 6,
                      }}
                    >
                      <span className="mono">
                        {(p.lot_size ?? 0).toFixed(2)} lots
                      </span>
                      <span>{p.open_time ? String(p.open_time).slice(11, 16) : "—"}</span>
                    </div>
                    <div className="tp-prog">
                      <div className="tp-pill" title="TP1" />
                      <div className="tp-pill" title="TP2" />
                      <div className="tp-pill" title="TP3" />
                      <div className="tp-pill" title="TP4" />
                      <span className="dim mono" style={{ marginLeft: 8, fontSize: 10 }}>
                        entry {typeof p.entry_price === "number" ? p.entry_price.toFixed(2) : "—"} · sl {typeof p.stop_loss === "number" ? p.stop_loss.toFixed(2) : "—"}
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Exposure */}
          <div className="card">
            <div className="card-head">
              <span className="card-title">
                <span className="dot" />
                Exposure
              </span>
              <span className="hint mono">
                net {netExposure.toFixed(2)} lots
              </span>
            </div>
            <div className="card-body">
              {Object.keys(exposure).length === 0 ? (
                <div style={{ padding: "12px 0", textAlign: "center", color: "var(--fg-3)", fontSize: 13 }}>
                  No active exposure
                </div>
              ) : (
                <>
                  <div className="heat">
                    <div className="h">SYM</div>
                    <div className="h">LONG</div>
                    <div className="h">SHORT</div>
                    <div className="h">NET</div>
                    {Object.entries(exposure).map(([sym, exp]) => {
                      const net = exp.long - exp.short;
                      const li = Math.min(exp.long / 0.8, 1);
                      const si = Math.min(exp.short / 0.8, 1);
                      return (
                        <div key={sym} style={{ display: "contents" }}>
                          <div className="c mono" style={{ fontWeight: 500 }}>
                            {sym}
                          </div>
                          <div
                            className="c long"
                            style={{ "--i": li } as React.CSSProperties}
                          >
                            {exp.long > 0 ? exp.long.toFixed(2) : "—"}
                          </div>
                          <div
                            className="c short"
                            style={{ "--i": si } as React.CSSProperties}
                          >
                            {exp.short > 0 ? exp.short.toFixed(2) : "—"}
                          </div>
                          <div
                            className="c mono"
                            style={{ color: net > 0 ? "var(--pos)" : net < 0 ? "var(--neg)" : undefined }}
                          >
                            {net > 0 ? "+" : ""}{net.toFixed(2)}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  <div
                    style={{
                      marginTop: 14,
                      display: "flex",
                      justifyContent: "space-between",
                      fontSize: 11,
                    }}
                  >
                    <span className="dim">Concentration</span>
                    <span className="dim">
                      Notional <span className="mono">—</span>
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>

        {/* CENTER */}
        <div className="col">
          {/* Top signals */}
          <div className="card">
            <div className="card-head">
              <span className="card-title">
                <span className="dot" />
                Top signals · ranked
              </span>
              <a href="/dashboard/signals" className="hint">
                All signals →
              </a>
            </div>
            <div className="card-body flush">
              {topSignals.length === 0 ? (
                <div style={{ padding: "24px 16px", textAlign: "center", color: "var(--fg-3)", fontSize: 13 }}>
                  No signals available
                </div>
              ) : (
                topSignals.map((s, i) => (
                  <div key={s.id} className="sig-card">
                    <div className="sig-rank">#{i + 1}</div>
                    <div>
                      <div className="sig-row1">
                        <span className="sig-sym">{s.symbol}</span>
                        <Chip tone={dirChip(s.direction)}>{s.direction}</Chip>
                        <Chip tone="">{s.strategy}</Chip>
                        <Chip tone={verdictHue(s.signal_intent)}>{s.signal_intent}</Chip>
                      </div>
                      <div className="sig-row2">
                        <div style={{ flex: 1, maxWidth: 260 }}>
                          <div
                            style={{
                              display: "flex",
                              justifyContent: "space-between",
                              fontSize: 10.5,
                              marginBottom: 3,
                            }}
                          >
                            <span className="dim">CONFIDENCE</span>
                            <span className="mono">{Math.round(s.confidence * 100)}%</span>
                          </div>
                          <div className={`conf-bar ${confTier(s.confidence * 100)}`}>
                            <span style={{ width: `${s.confidence * 100}%` }} />
                          </div>
                        </div>
                        <span className="dim mono" style={{ whiteSpace: "nowrap" }}>
                          {fmtRel(s.created_at)}
                        </span>
                      </div>
                    </div>
                    <div className="sig-meta">
                      <span className="mono dim" style={{ fontSize: 11 }}>
                        entry{" "}
                        <span style={{ color: "var(--fg)" }}>
                          {(() => { const pos = positions.find(p => p.symbol === s.symbol); return typeof pos?.entry_price === "number" ? pos.entry_price.toFixed(2) : "—"; })()}
                        </span>
                      </span>
                      <span className="mono dim" style={{ fontSize: 11 }}>
                        sl{" "}
                        <span style={{ color: "var(--fg)" }}>
                          {typeof s.stop_loss === "number" ? s.stop_loss.toFixed(2) : "—"}
                        </span>
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Equity chart */}
          <div className="card">
            <div className="card-head">
              <span className="card-title">
                <span className="dot" />
                Equity · live
              </span>
              <span className="mono dim">
                ${equity.toLocaleString("en-US", { minimumFractionDigits: 0 })}
              </span>
            </div>
            <div className="card-body">
              <EquityPlaceholder equity={equity} />
            </div>
          </div>
        </div>

        {/* RIGHT */}
        <div className="col">
          {/* Agent feed */}
          <div className="card">
            <div className="card-head">
              <span className="card-title">
                <span className="dot" />
                Agent feed
              </span>
              <a href="/dashboard/health" className="hint">
                Open ›
              </a>
            </div>
            <div className="card-body flush" style={{ overflowY: "auto" }}>
              {recentEvents.length === 0 ? (
                <div style={{ padding: "24px 16px", textAlign: "center", color: "var(--fg-3)", fontSize: 13 }}>
                  No recent events
                </div>
              ) : (
                recentEvents.map((e, i) => (
                  <div
                    key={e.id ?? i}
                    className={`feed-item severity-${
                      e.level === "error" || e.level === "critical" ? "ERROR" :
                      e.level === "warn" ? "WARN" : "SUCCESS"
                    }`}
                  >
                    <span className="feed-agent">{e.agent}</span>
                    <span className="feed-msg">{e.message ?? e.msg ?? ""}</span>
                    <span className="feed-time">
                      {e.created_at ? fmtRel(String(e.created_at)) : "—"}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Macro snapshot */}
          <div className="card">
            <div className="card-head">
              <span className="card-title">
                <span className="dot" style={{ background: "var(--warning)" }} />
                Macro snapshot
              </span>
              <a href="/dashboard/macro" className="hint">
                Detail ›
              </a>
            </div>
            <div
              className="card-body"
              style={{ display: "flex", flexDirection: "column", gap: 12 }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <Chip tone="warn">
                  <Sdot tone="warn" /> {regime}
                </Chip>
                <span className="mono dim" style={{ fontSize: 11 }}>
                  lot ×1.00 · regime {regime}
                </span>
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr",
                  gap: 6,
                  fontSize: 11.5,
                }}
              >
                {[
                  { label: "VIX",     value: vix != null ? vix.toFixed(1) : "—", unit: "" },
                  { label: "Session",  value: session, unit: "" },
                  { label: "Spread",   value: spreadCond, unit: "" },
                  { label: "Bot",      value: botState, unit: "" },
                ].map((ind) => (
                  <div
                    key={ind.label}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      padding: "5px 0",
                      borderBottom: "1px solid var(--border)",
                    }}
                  >
                    <span className="dim">{ind.label}</span>
                    <span className="mono">
                      {ind.value}
                      {ind.unit}
                    </span>
                  </div>
                ))}
              </div>
              <div
                className="alert-banner warn"
                style={{ margin: 0, padding: "8px 10px", fontSize: 11.5 }}
              >
                <Sdot tone="warn" /> {intel?.intelligence ?? "All systems nominal"}
              </div>
            </div>
          </div>

          {/* Learning drift */}
          <div className="card">
            <div className="card-head">
              <span className="card-title">
                <span className="dot" style={{ background: "var(--violet)" }} />
                Learning · drift
              </span>
              <a href="/dashboard/learn" className="hint">
                Detail ›
              </a>
            </div>
            <div className="card-body">
              {confidences.length === 0 ? (
                <div style={{ padding: "12px 0", textAlign: "center", color: "var(--fg-3)", fontSize: 13 }}>
                  No strategy scores yet
                </div>
              ) : (
                <>
                  {confidences.slice(0, 3).map((c) => (
                    <div key={c.strategy} style={{ marginBottom: 10 }}>
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          marginBottom: 4,
                        }}
                      >
                        <span className="dim" style={{ fontSize: 11 }}>
                          {c.strategy}
                        </span>
                        <span className="mono" style={{ fontSize: 11 }}>
                          {Math.round(c.confidence * 100)}%
                        </span>
                      </div>
                      <div className="progress-lg">
                        <span
                          style={{
                            width: `${c.confidence * 100}%`,
                            background: "var(--violet)",
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function RefreshIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <path d="M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <rect x="6" y="4" width="4" height="16" />
      <rect x="14" y="4" width="4" height="16" />
    </svg>
  );
}

function StopIcon() {
  return (
    <svg
      width="12"
      height="12"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <rect x="3" y="3" width="18" height="18" rx="2" />
    </svg>
  );
}
