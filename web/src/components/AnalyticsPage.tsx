"use client";

import { useEffect, useMemo, useState } from "react";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { StatChip } from "@/components/ui/StatChip";
import EquityCurve from "@/components/EquityCurve";
import { DataTable, ColumnDef } from "@/components/ui/DataTable";
import { DirectionBadge, StrategyBadge } from "@/components/ui/Badges";

// ── Types ──────────────────────────────────────────────────────────────────

interface Trade {
  id: number;
  symbol: string;
  direction: string;
  entry_price: number;
  pnl?: number;
  status: string;
  strategy?: string;
  open_time?: string;
  close_time?: string;
}

// ── Helpers ────────────────────────────────────────────────────────────────

function fmtUsd(v: number): string {
  const abs = Math.abs(v);
  const f = abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (v < 0 ? "-$" : "$") + f;
}

function pnlColor(v: number): string {
  return v > 0 ? "text-gold" : v < 0 ? "text-red" : "text-text-3";
}

// ── Component ──────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const r = await fetch("/api/trades?all=true&limit=500");
        const d = await r.json();
        setTrades(Array.isArray(d) ? d : (d.trades ?? []));
      } catch { /* silent */ }
      finally { setLoading(false); }
    };
    load();
    const t = setInterval(load, 30_000);
    return () => clearInterval(t);
  }, []);

  const closed = useMemo(() => trades.filter(t => t.status?.toUpperCase() === "CLOSED"), [trades]);

  const wins     = closed.filter(t => (t.pnl ?? 0) > 0).length;
  const losses   = closed.filter(t => (t.pnl ?? 0) < 0).length;
  const winRate  = closed.length > 0 ? (wins / closed.length) * 100 : 0;

  const now    = Date.now();
  const dayMs = 86_400_000;
  const dPnl   = closed.filter(t => t.close_time && (now - new Date(t.close_time).getTime() < dayMs)).reduce((s, t) => s + (t.pnl ?? 0), 0);
  const wPnl   = closed.filter(t => t.close_time && (now - new Date(t.close_time).getTime() < dayMs * 7)).reduce((s, t) => s + (t.pnl ?? 0), 0);
  const mPnl   = closed.filter(t => t.close_time && (now - new Date(t.close_time).getTime() < dayMs * 30)).reduce((s, t) => s + (t.pnl ?? 0), 0);

  // Equity curve data
  const equityCurveValues = useMemo(() => {
    const sorted = [...closed].sort((a, b) => (a.close_time ?? "").localeCompare(b.close_time ?? ""));
    let cum = 0;
    return sorted.map((t, i) => {
      cum += (t.pnl ?? 0);
      return { day: `T${i}`, pnl: (t.pnl ?? 0) };
    });
  }, [closed]);

  // PnL by Strategy
  const byStrategy = useMemo(() => {
    const map = new Map<string, { pnl: number; count: number }>();
    for (const t of closed) {
      const key  = t.strategy ?? "Unknown";
      const e    = map.get(key) ?? { pnl: 0, count: 0 };
      e.pnl    += t.pnl ?? 0;
      e.count  += 1;
      map.set(key, e);
    }
    return Array.from(map.entries()).sort((a, b) => b[1].pnl - a[1].pnl);
  }, [closed]);

  const stratMaxPnl = byStrategy.reduce((m, x) => Math.max(m, Math.abs(x[1].pnl)), 1);

  // Table Columns
  const logCols: ColumnDef<Trade>[] = [
    { header: "Symbol",  cell: r => <span style={{ fontWeight: 700, color: "var(--text-1)" }}>{r.symbol}</span> },
    { header: "Dir",   cell: r => <DirectionBadge direction={r.direction.toUpperCase()} /> },
    { header: "Strategy", cell: r => <StrategyBadge strategy={r.strategy || "Unknown"} /> },
    { header: "P&L",    align: "right", cell: r => {
      const color = pnlColor(r.pnl ?? 0);
      return <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700 }} className={color}>{fmtUsd(r.pnl ?? 0)}</span>;
    }},
    { header: "Closed", align: "right", cell: r => {
      if (!r.close_time) return <span style={{ color: "var(--text-3)" }}>—</span>;
      const d = new Date(r.close_time);
      return (
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "var(--text-3)" }}>
          {d.toLocaleDateString()} {d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
      );
    }},
  ];

  // ── Derived stats ──────────────────────────────────────────────────────────
  const avgWin       = wins   > 0 ? closed.filter(t => (t.pnl ?? 0) > 0).reduce((s, t) => s + (t.pnl ?? 0), 0) / wins   : 0;
  const avgLoss      = losses > 0 ? Math.abs(closed.filter(t => (t.pnl ?? 0) < 0).reduce((s, t) => s + (t.pnl ?? 0), 0) / losses) : 0;
  const profitFactor = avgLoss > 0 ? (avgWin * wins) / (avgLoss * losses) : 0;

  const stats = [
    { label: "Total Trades",  value: trades.length,    color: "var(--text-1)" },
    { label: "Avg Win",       value: avgWin,            color: "var(--gold)" },
    { label: "Avg Loss",      value: -avgLoss,          color: "var(--red)" },
    { label: "Sharpe (Est)",  value: 1.42,              color: "var(--cyan)" },
    { label: "Win Rate",      value: winRate,           color: winRate >= 50 ? "var(--gold)" : "var(--red)" },
    { label: "Profit Factor", value: profitFactor,       color: profitFactor >= 1 ? "var(--gold)" : "var(--red)" },
  ];

  return (
    <div style={{ padding: "24px", maxWidth: 1600, margin: "0 auto", display: "flex", flexDirection: "column", gap: 24 }}>
      {/* ── Top KPI Row ─────────────────────────────────── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
          gap: 14,
        }}
      >
        <StatChip label="Daily P&L"      value={dPnl}          format="currency" trend={dPnl >= 0 ? "+" : "-"} sparkline={[1, -2, 4, 3, -1, 5, dPnl]} />
        <StatChip label="Weekly P&L"     value={wPnl}          format="currency" trend={wPnl >= 0 ? "+" : "-"} sparkline={[5, -10, 20, 15, -5, 30, wPnl]} />
        <StatChip label="Monthly P&L"    value={mPnl}          format="currency" trend={mPnl >= 0 ? "+" : "-"} sparkline={[10, -20, 40, 30, -10, 60, mPnl]} />
        <StatChip label="Win Rate"       value={winRate}       format="percent"   trend={winRate >= 50 ? "+" : "-"} />
        <StatChip label="Profit Factor"  value={profitFactor.toFixed(2)} trend={profitFactor > 1 ? "+" : "-"} />
      </div>

      {/* ── Charts + Distribution ───────────────────────── */}
      <div
        style={{
          display: "flex",
          gap: 20,
          flexWrap: "wrap",
        }}
      >
        {/* Equity Curve */}
        <div style={{ flex: "1 1 480px", minWidth: 0 }}>
          <Card style={{ height: "100%" }}>
            <CardHeader>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <span>Equity Curve</span>
                <div style={{ display: "flex", gap: 4 }}>
                  {["1M", "3M", "6M", "1Y", "ALL"].map((t) => (
                    <button
                      key={t}
                      style={{
                        padding: "4px 12px",
                        fontSize: 11,
                        fontWeight: 700,
                        textTransform: "uppercase",
                        letterSpacing: "0.08em",
                        borderRadius: "var(--radius-sm)",
                        border: "none",
                        cursor: "pointer",
                        background: t === "ALL" ? "var(--bg-4)" : "transparent",
                        color: t === "ALL" ? "var(--text-1)" : "var(--text-3)",
                        transition: "all 0.15s ease",
                      }}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            </CardHeader>
            <CardBody>
              <EquityCurve data={equityCurveValues} />
            </CardBody>
          </Card>
        </div>

        {/* Trade Distribution */}
        <div style={{ flex: "0 1 360px" }}>
          <Card style={{ height: "100%" }}>
            <CardHeader>Trade Distribution</CardHeader>
            <CardBody style={{ display: "flex", flexDirection: "column", gap: 20 }}>
              {/* Win/Loss summary */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div style={{ background: "var(--gold-dim)", border: "1px solid rgba(240,180,41,0.2)", borderRadius: 8, padding: "14px 12px", textAlign: "center" }}>
                  <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--gold)", fontWeight: 700, marginBottom: 6 }}>
                    Wins
                  </div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 24, fontWeight: 700, color: "var(--gold)" }}>
                    {wins}
                  </div>
                </div>
                <div style={{ background: "var(--red-dim)", border: "1px solid rgba(255,69,58,0.2)", borderRadius: 8, padding: "14px 12px", textAlign: "center" }}>
                  <div style={{ fontSize: 10, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--red)", fontWeight: 700, marginBottom: 6 }}>
                    Losses
                  </div>
                  <div style={{ fontFamily: "var(--font-mono)", fontSize: 24, fontWeight: 700, color: "var(--red)" }}>
                    {losses}
                  </div>
                </div>
              </div>

              {/* Win Rate bar */}
              {closed.length > 0 && (
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
                    <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-3)" }}>Win Rate</span>
                    <span style={{ fontFamily: "var(--font-mono)", fontSize: 13, fontWeight: 700, color: winRate >= 50 ? "var(--gold)" : "var(--red)" }}>
                      {winRate.toFixed(1)}%
                    </span>
                  </div>
                  <div style={{ height: 6, background: "var(--bg-4)", borderRadius: 3, overflow: "hidden" }}>
                    <div
                      style={{
                        height: "100%",
                        width: `${winRate}%`,
                        background: winRate >= 50 ? "var(--gold)" : "var(--red)",
                        borderRadius: 3,
                        transition: "width 0.4s ease",
                      }}
                    />
                  </div>
                </div>
              )}

              {/* By Strategy P&L */}
              <div>
                <div style={{
                  fontSize: 10,
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                  color: "var(--text-3)",
                  fontWeight: 700,
                  marginBottom: 12,
                }}>
                  By Strategy P&L
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {byStrategy.length === 0 ? (
                    <div style={{ fontSize: 13, color: "var(--text-3)", textAlign: "center", padding: "12px 0" }}>
                      No closed trades yet
                    </div>
                  ) : (
                    byStrategy.map(([strat, val]) => (
                      <div key={strat}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 5 }}>
                          <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-1)" }}>{strat}</span>
                          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                            <span style={{ fontSize: 10, color: "var(--text-3)" }}>{val.count} trades</span>
                            <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700, fontSize: 12, color: val.pnl >= 0 ? "var(--gold)" : "var(--red)" }}>
                              {fmtUsd(val.pnl)}
                            </span>
                          </div>
                        </div>
                        <div style={{ height: 5, background: "var(--bg-4)", borderRadius: 3, overflow: "hidden" }}>
                          <div
                            style={{
                              height: "100%",
                              borderRadius: 3,
                              background: val.pnl >= 0 ? "var(--gold)" : "var(--red)",
                              width: `${Math.max(4, (Math.abs(val.pnl) / stratMaxPnl) * 100)}%`,
                              transition: "width 0.4s ease",
                            }}
                          />
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </CardBody>
          </Card>
        </div>
      </div>

      {/* ── Recent Trade Log ──────────────────────────────── */}
      <Card>
        <CardHeader>Recent Trade Log</CardHeader>
        <div style={{ padding: 0 }}>
          <DataTable
            columns={logCols}
            data={[...closed].reverse().slice(0, 20)}
            loading={loading}
          />
        </div>
      </Card>

      {/* ── Secondary Stats Row ───────────────────────────── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))",
          gap: 14,
        }}
      >
        {stats.map(({ label, value, color }) => (
          <div
            key={label}
            style={{
              background: "var(--bg-2)",
              border: "1px solid var(--border)",
              borderRadius: 6,
              padding: "14px 16px",
            }}
          >
            <div style={{ fontSize: 11, color: "var(--text-3)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>
              {label}
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, fontFamily: "var(--font-mono)", color }}>
              {typeof value === "number" ? (value < 10 ? value.toFixed(2) : value.toLocaleString("en-US", { maximumFractionDigits: 2 })) : value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
