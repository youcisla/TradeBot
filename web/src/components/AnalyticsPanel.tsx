"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

interface Trade {
  id: string;
  symbol: string;
  direction: string;
  entry_price: number;
  lot_size: number;
  stop_loss: number;
  take_profit_1: number;
  pnl: number;
  status: string;
  open_time: string;
  close_time?: string;
}

interface StrategyConfidence {
  strategy: string;
  confidence: number;
  trades: number;
  pnl: number;
}

interface AgentEvent {
  id?: number;
  agent: string;
  level: string;
  msg?: string;
  message?: string;
  ts?: string;
  created_at?: string;
}

function fmtUsd(v: number | undefined | string): string {
  const n = typeof v === "string" ? parseFloat(v) : (v as number) ?? 0;
  if (isNaN(n)) return "—";
  const abs = Math.abs(n);
  const f = abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (n < 0 ? "-$" : "$") + f;
}

function pnlNum(v: number | string | undefined): number {
  if (v === undefined || v === null) return 0;
  return typeof v === "string" ? parseFloat(v) : v;
}

function fmtTime(ts: string | undefined | null): string {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleTimeString("en-US", {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
      hour12: false, timeZone: "Europe/Paris",
    });
  } catch { return "—"; }
}

const AGENT_COLORS: Record<string, string> = {
  crucix: "#64D2FF", market: "#32ADE6", analysis: "#636366",
  strategy: "#16A34A", neural: "#9333EA", council: "#D97706",
  risk: "#DC2626", execution: "#6B7280", trade_manager: "#0EA5E9",
  learning: "#8B5CF6", logging: "#9CA3AF", model_manager: "#6366F1",
  debate: "#F59E0B", exposure: "#10B981", memory: "#14B8A6",
};

function agentColor(key: string): string {
  return AGENT_COLORS[key.toLowerCase()] ?? "#9CA3AF";
}

export default function AnalyticsPanel() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [confidences, setConfidences] = useState<StrategyConfidence[]>([]);
  const [events, setEvents] = useState<AgentEvent[]>([]);

  const fetch_ = useCallback(async () => {
    try {
      const [tradesRes, learnRes, eventsRes] = await Promise.all([
        fetch("/api/broker/trades?days=30"),
        fetch("/api/learning"),
        fetch("/api/events?limit=30"),
      ]);
      if (tradesRes.ok) {
        const data = await tradesRes.json();
        if (Array.isArray(data)) setTrades(data);
      }
      if (learnRes.ok) {
        const ld = await learnRes.json();
        if (Array.isArray(ld.confidences)) setConfidences(ld.confidences);
      }
      if (eventsRes.ok) {
        const ed = await eventsRes.json();
        if (Array.isArray(ed)) setEvents(ed.slice(0, 20));
      }
    } catch { /* keep last */ }
  }, []);

  useEffect(() => {
    fetch_();
    const id = setInterval(fetch_, 10_000);
    return () => clearInterval(id);
  }, [fetch_]);

  // ── KPIs from closed broker trades ─────────────────────────────────────────
  const closed = useMemo(
    () => trades.filter((t) => t.status === "CLOSED"),
    [trades]
  );
  const wins = closed.filter((t) => pnlNum(t.pnl) > 0);
  const losses = closed.filter((t) => pnlNum(t.pnl) < 0);
  const totalPn = closed.reduce((s, t) => s + pnlNum(t.pnl), 0);
  const winRate = closed.length > 0 ? (wins.length / closed.length) * 100 : 0;
  const avgWin = wins.length > 0
    ? wins.reduce((s, t) => s + pnlNum(t.pnl), 0) / wins.length : 0;
  const avgLoss = losses.length > 0
    ? Math.abs(losses.reduce((s, t) => s + pnlNum(t.pnl), 0) / losses.length) : 0;

  // ── Equity curve from closed trades grouped by day ──────────────────────
  const equityCurve = useMemo(() => {
    const byDay: Record<string, number> = {};
    for (const t of closed) {
      if (!t.close_time) continue;
      const day = t.close_time.slice(0, 10); // YYYY-MM-DD
      byDay[day] = (byDay[day] ?? 0) + pnlNum(t.pnl);
    }
    const sorted = Object.entries(byDay).sort(([a], [b]) => a.localeCompare(b));
    let cum = 0;
    return sorted.map(([day, pnl]) => {
      cum += pnl;
      return { day, cum: parseFloat(cum.toFixed(2)) };
    });
  }, [closed]);

  const lastCum = equityCurve.length > 0 ? equityCurve[equityCurve.length - 1].cum : 0;
  const eqColor = lastCum >= 0 ? "#16A34A" : "#DC2626";
  const maxConf = Math.max(...confidences.map((c) => c.confidence), 0.01);

  return (
    <aside style={styles.panel}>
      {/* ── KPIs ───────────────────────────────── */}
      <div style={styles.section}>
        <div style={styles.sectionLabel}>Performance</div>
        <div style={styles.kpiGrid}>
          <KpiItem label="Trades" value={String(closed.length)} />
          <KpiItem label="Win%" value={`${winRate.toFixed(0)}%`}
            color={winRate >= 50 ? "#16A34A" : "#DC2626"} />
          <KpiItem label="Avg Win" value={avgWin > 0 ? fmtUsd(avgWin) : "—"} color="#16A34A" />
          <KpiItem label="Avg Loss" value={avgLoss > 0 ? fmtUsd(avgLoss) : "—"} color="#DC2626" />
        </div>
      </div>

      {/* ── Equity Curve ────────────────────────── */}
      <div style={styles.section}>
        <div style={styles.sectionLabel}>Equity Curve</div>
        {equityCurve.length < 2 ? (
          <div style={styles.empty}>Not enough data</div>
        ) : (
          <div style={styles.chartWrap}>
            <EquitySparkline data={equityCurve} color={eqColor} />
            <div style={{ ...styles.eqLabel, color: eqColor }}>
              {lastCum >= 0 ? "+" : ""}{fmtUsd(lastCum)}
            </div>
          </div>
        )}
      </div>

      {/* ── Strategy Confidence ─────────────────── */}
      <div style={styles.section}>
        <div style={styles.sectionLabel}>Strategy Confidence</div>
        <div style={styles.confList}>
          {confidences.length === 0 ? (
            <div style={styles.empty}>No strategies active</div>
          ) : (
            confidences.map((c) => (
              <ConfBar key={c.strategy} strategy={c.strategy} confidence={c.confidence} max={maxConf} />
            ))
          )}
        </div>
      </div>

      {/* ── Agent Feed ──────────────────────────── */}
      <div style={{ ...styles.section, flex: 1, minHeight: 0 }}>
        <div style={styles.sectionLabel}>Agent Feed</div>
        <div style={styles.feedWrap}>
          {events.length === 0 ? (
            <div style={styles.empty}>No events</div>
          ) : (
            events.slice(0, 15).map((ev, i) => (
              <div key={ev.id ?? `${ev.ts}-${i}`} style={styles.feedRow}>
                <span style={{ ...styles.feedDot, background: agentColor(ev.agent) }} />
                <span style={styles.feedAgent}>{ev.agent}</span>
                <span style={{
                  ...styles.feedMsg,
                  color: ev.level === "error" || ev.level === "critical" ? "#DC2626"
                    : ev.level === "warn" ? "#D97706" : "#374151",
                }}>
                  {String(ev.msg ?? ev.message ?? "").slice(0, 48)}
                </span>
                <span style={styles.feedTime}>{fmtTime(ev.ts ?? ev.created_at)}</span>
              </div>
            ))
          )}
        </div>
      </div>
    </aside>
  );
}

function KpiItem({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={styles.kpiItem}>
      <span style={styles.kpiLabel}>{label}</span>
      <span style={{ ...styles.kpiValue, color: color ?? "#111111" }}>{value}</span>
    </div>
  );
}

function ConfBar({ strategy, confidence, max }: { strategy: string; confidence: number; max: number }) {
  const pct = (confidence / max) * 100;
  const color = pct > 70 ? "#16A34A" : pct > 40 ? "#D97706" : "#9CA3AF";
  return (
    <div style={styles.confRow}>
      <div style={styles.confHeader}>
        <span style={styles.confName}>{strategy}</span>
        <span style={{ ...styles.confPct, color }}>{(confidence * 100).toFixed(0)}%</span>
      </div>
      <div style={styles.confTrack}>
        <div style={{ ...styles.confFill, width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

function EquitySparkline({ data, color }: { data: { day: string; cum: number }[]; color: string }) {
  if (data.length < 2) return null;
  const min = Math.min(...data.map((d) => d.cum));
  const max = Math.max(...data.map((d) => d.cum));
  const range = max - min || 1;
  const W = 200;
  const H = 48;
  const pts = data.map((d, i) => {
    const x = (i / (data.length - 1)) * W;
    const y = H - ((d.cum - min) / range) * H;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} style={{ overflow: "visible" }}>
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

const styles: Record<string, React.CSSProperties> = {
  panel: {
    position: "fixed",
    top: 48,
    right: 0,
    bottom: 32,
    width: 264,
    background: "#FFFFFF",
    borderLeft: "1px solid #F0F0F0",
    display: "flex",
    flexDirection: "column",
    overflowY: "auto",
    zIndex: 90,
    flexShrink: 0,
  },
  section: {
    padding: "12px 14px",
    borderBottom: "1px solid #F8F8F8",
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  sectionLabel: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 9,
    fontWeight: 700,
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: "0.08em",
  },
  empty: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    color: "#9CA3AF",
    textAlign: "center",
    padding: "8px 0",
    fontStyle: "italic",
  },
  kpiGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: 8,
  },
  kpiItem: {
    background: "#FAFAFA",
    borderRadius: 4,
    padding: "6px 8px",
    display: "flex",
    flexDirection: "column",
    gap: 2,
  },
  kpiLabel: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 9,
    color: "#9CA3AF",
    textTransform: "uppercase",
  },
  kpiValue: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 13,
    fontWeight: 700,
  },
  chartWrap: {
    display: "flex",
    flexDirection: "column",
    gap: 4,
  },
  eqLabel: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    fontWeight: 700,
    textAlign: "right",
  },
  confList: {
    display: "flex",
    flexDirection: "column",
    gap: 8,
  },
  confRow: {
    display: "flex",
    flexDirection: "column",
    gap: 3,
  },
  confHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
  },
  confName: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    fontWeight: 600,
    color: "#374151",
  },
  confPct: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    fontWeight: 700,
  },
  confTrack: {
    height: 4,
    background: "#F0F0F0",
    borderRadius: 2,
    overflow: "hidden",
  },
  confFill: {
    height: "100%",
    borderRadius: 2,
    transition: "width 0.3s ease",
  },
  feedWrap: {
    display: "flex",
    flexDirection: "column",
    gap: 1,
    overflowY: "auto",
    minHeight: 0,
    flex: 1,
  },
  feedRow: {
    display: "flex",
    alignItems: "center",
    gap: 5,
    padding: "3px 0",
    borderBottom: "1px solid #FAFAFA",
  },
  feedDot: {
    width: 5,
    height: 5,
    borderRadius: "50%",
    flexShrink: 0,
  },
  feedAgent: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 9,
    fontWeight: 700,
    color: "#6B7280",
    flexShrink: 0,
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    maxWidth: 52,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  feedMsg: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 9,
    flex: 1,
    overflow: "hidden",
    textOverflow: "ellipsis",
    whiteSpace: "nowrap",
  },
  feedTime: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 8,
    color: "#9CA3AF",
    flexShrink: 0,
  },
};
