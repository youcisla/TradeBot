"use client";

import { useEffect, useMemo, useState } from "react";
import { useAppShell } from "@/components/AppShell";

//  Types

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

//  Helpers 

function fmtUsd(v: number): string {
  const abs = Math.abs(v);
  const f = abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (v < 0 ? "-$" : "$") + f;
}

function pnlColor(v: number): string {
  return v > 0 ? "#34C759" : v < 0 ? "#FF3B30" : "rgba(232,234,237,0.40)";
}

// SVG sparkline helpers
function sparkline(values: number[], w: number, h: number): string {
  if (values.length < 2) return "";
  const mn = Math.min(...values);
  const mx = Math.max(...values);
  const range = mx - mn || 1;
  const pts = values.map((v, i) => {
    const x = (i / (values.length - 1)) * w;
    const y = h - ((v - mn) / range) * h;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  return `M${pts.join("L")}`;
}

//  Page 

export default function PerformancePage() {
  const { status: shellStatus } = useAppShell();
  const [trades,  setTrades]  = useState<Trade[]>([]);
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
  const open_  = useMemo(() => trades.filter(t => t.status?.toUpperCase() !== "CLOSED"), [trades]);

  const wins    = closed.filter(t => (t.pnl ?? 0) > 0).length;
  const losses  = closed.filter(t => (t.pnl ?? 0) < 0).length;
  const winRate = closed.length > 0 ? (wins / closed.length) * 100 : 0;
  const totalPnl = closed.reduce((s, t) => s + (t.pnl ?? 0), 0);
  const avgWin   = wins > 0 ? closed.filter(t => (t.pnl ?? 0) > 0).reduce((s, t) => s + (t.pnl ?? 0), 0) / wins : 0;
  const avgLoss  = losses > 0 ? Math.abs(closed.filter(t => (t.pnl ?? 0) < 0).reduce((s, t) => s + (t.pnl ?? 0), 0) / losses) : 0;
  const rr       = avgLoss > 0 ? avgWin / avgLoss : 0;
  const profitFactor = avgLoss > 0 ? (avgWin * wins) / (avgLoss * losses) : 0;

  // Equity curve from cumulative PnL
  const equityCurve = useMemo(() => {
    const sorted = [...closed]
      .sort((a, b) => (a.close_time ?? "").localeCompare(b.close_time ?? ""))
      .map(t => t.pnl ?? 0);
    let cum = 0;
    return sorted.map(p => { cum += p; return cum; });
  }, [closed]);

  // PnL by symbol
  const bySymbol = useMemo(() => {
    const map = new Map<string, { pnl: number; count: number }>();
    for (const t of closed) {
      const e = map.get(t.symbol) ?? { pnl: 0, count: 0 };
      e.pnl += t.pnl ?? 0;
      e.count++;
      map.set(t.symbol, e);
    }
    return Array.from(map.entries())
      .map(([sym, v]) => ({ sym, ...v }))
      .sort((a, b) => Math.abs(b.pnl) - Math.abs(a.pnl))
      .slice(0, 10);
  }, [closed]);

  // PnL by strategy
  const byStrategy = useMemo(() => {
    const map = new Map<string, { pnl: number; wins: number; total: number }>();
    for (const t of closed) {
      const key = t.strategy ?? "Unknown";
      const e   = map.get(key) ?? { pnl: 0, wins: 0, total: 0 };
      e.pnl  += t.pnl ?? 0;
      e.total++;
      if ((t.pnl ?? 0) > 0) e.wins++;
      map.set(key, e);
    }
    return Array.from(map.entries())
      .map(([strat, v]) => ({ strat, ...v, wr: v.total > 0 ? (v.wins / v.total) * 100 : 0 }))
      .sort((a, b) => b.total - a.total);
  }, [closed]);

  // Monthly P&L groups
  const byMonth = useMemo(() => {
    const map = new Map<string, number>();
    for (const t of closed) {
      if (!t.close_time) continue;
      const d = new Date(t.close_time);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
      map.set(key, (map.get(key) ?? 0) + (t.pnl ?? 0));
    }
    return Array.from(map.entries()).sort((a, b) => a[0].localeCompare(b[0])).slice(-6);
  }, [closed]);

  const MONO = "var(--font-mono-stack)";
  const card: React.CSSProperties = {
    background: "var(--card-bg)", border: "1px solid var(--card-border)", borderRadius: "var(--card-radius)",
  };
  const sectionLabel: React.CSSProperties = {
    fontSize: 11, fontWeight: 600, color: "var(--section-label)",
    letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 14,
  };

  //  Max bar widths for symbol chart
  const maxAbsPnl = bySymbol.reduce((m, x) => Math.max(m, Math.abs(x.pnl)), 1);
  const maxMonthPnl = byMonth.reduce((m, x) => Math.max(m, Math.abs(x[1])), 1);

  return (
    <>
      {/*  Top KPI strip  */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 20 }}>
        {loading
          ? [0,1,2,3].map(i => (
              <div key={i} className="skel-row" style={{ ...card, padding: "18px 20px" }}>
                <div className="ios-skeleton" style={{ height: 11, width: "55%", borderRadius: 4, marginBottom: 10 }} />
                <div className="ios-skeleton" style={{ height: 28, width: "75%", borderRadius: 6 }} />
              </div>
            ))
          : [
              { label: "Net P&L",        value: fmtUsd(totalPnl),          color: pnlColor(totalPnl) },
              { label: "Win Rate",       value: winRate.toFixed(1) + "%",   color: winRate >= 50 ? "#34C759" : "#FF9F0A" },
              { label: "Risk / Reward",  value: rr.toFixed(2) + "×",       color: rr >= 1.5 ? "#34C759" : rr >= 1 ? "#FF9F0A" : "#FF3B30" },
              { label: "Profit Factor",  value: profitFactor.toFixed(2),   color: profitFactor >= 1.5 ? "#34C759" : profitFactor >= 1 ? "#FF9F0A" : "#FF3B30" },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ ...card, padding: "18px 20px" }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(232,234,237,0.60)", letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 6 }}>{label}</div>
                <div style={{ fontSize: 24, fontWeight: 700, color, fontFamily: MONO, letterSpacing: -0.5 }}>{value}</div>
              </div>
            ))
        }
      </div>

      {/*  Second row: totals  */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))", gap: 12, marginBottom: 20 }}>
        {loading
          ? [0,1,2,3,4].map(i => (
              <div key={i} className="skel-row" style={{ ...card, padding: "14px 18px" }}>
                <div className="ios-skeleton" style={{ height: 11, width: "60%", borderRadius: 4, marginBottom: 8 }} />
                <div className="ios-skeleton" style={{ height: 22, width: "50%", borderRadius: 5 }} />
              </div>
            ))
          : [
              { label: "Total Trades",  value: String(trades.length) },
              { label: "Closed",        value: String(closed.length) },
              { label: "Open",          value: String(open_.length),  color: "#0A84FF" },
              { label: "Avg Win",       value: fmtUsd(avgWin),        color: "#34C759" },
              { label: "Avg Loss",      value: fmtUsd(-avgLoss),      color: "#FF3B30" },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ ...card, padding: "14px 18px" }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(232,234,237,0.60)", letterSpacing: 0.4, textTransform: "uppercase", marginBottom: 4 }}>{label}</div>
                <div style={{ fontSize: 18, fontWeight: 700, color: color ?? "#E8EAED", fontFamily: MONO }}>{value}</div>
              </div>
            ))
        }
      </div>

      {/*  Equity curve  */}
      <div style={{ ...card, padding: "20px", marginBottom: 20 }}>
        <div style={sectionLabel}>Equity Curve · Closed Trades P&L</div>
        {loading ? (
          <div className="ios-skeleton" style={{ height: 120, borderRadius: 6 }} />
        ) : equityCurve.length < 2 ? (
          <div style={{ height: 120, display: "flex", alignItems: "center", justifyContent: "center", color: "rgba(232,234,237,0.20)", fontSize: 13 }}>
            Not enough closed trades
          </div>
        ) : (
          <svg width="100%" viewBox={`0 0 800 120`} preserveAspectRatio="none" style={{ display: "block", height: 120 }}>
            {/* Zero line */}
            {(() => {
              const nums = equityCurve.map(Number).filter(n => isFinite(n));
              if (nums.length === 0) return null;
              const mn = Math.min(...nums);
              const mx = Math.max(...nums);
              const range = mx - mn || 1;
              const zeroY = 120 - ((-mn) / range) * 120;
              return <line x1={0} x2={800} y1={zeroY} y2={zeroY} stroke="rgba(255,255,255,0.08)" strokeWidth={1} />;
            })()}
            {/* Fill under curve */}
            {(() => {
              const path = sparkline(equityCurve, 800, 120);
              const last = equityCurve[equityCurve.length - 1];
              const isPositive = last >= 0;
              return (
                <>
                  <defs>
                    <linearGradient id="fillGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor={isPositive ? "#34C759" : "#FF3B30"} stopOpacity={0.15} />
                      <stop offset="100%" stopColor={isPositive ? "#34C759" : "#FF3B30"} stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <path d={path + `L800,120 L0,120 Z`} fill="url(#fillGrad)" />
                  <path d={path} fill="none" stroke={isPositive ? "#34C759" : "#FF3B30"} strokeWidth={1.5} />
                </>
              );
            })()}
          </svg>
        )}
        {equityCurve.length >= 2 && (
          <div style={{ display: "flex", justifyContent: "space-between", marginTop: 6, fontSize: 11, color: "rgba(232,234,237,0.25)", fontFamily: MONO }}>
            <span>Trade 1</span>
            <span style={{ color: pnlColor(equityCurve[equityCurve.length - 1]) }}>{fmtUsd(equityCurve[equityCurve.length - 1])} cumulative</span>
            <span>Trade {equityCurve.length}</span>
          </div>
        )}
      </div>

      {/*  Bottom row  */}
      <div style={{ display: "flex", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>

        {/* By symbol */}
        <div style={{ flex: "1 1 220px", minWidth: 0 }}>
          <div style={{ ...card, padding: "20px" }}>
            <div style={sectionLabel}>P&L by Symbol</div>
            {loading ? (
              [0,1,2,3,4].map(i => (
                <div key={i} className="skel-row" style={{ marginBottom: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                    <div className="ios-skeleton" style={{ height: 12, width: "30%", borderRadius: 4 }} />
                    <div className="ios-skeleton" style={{ height: 12, width: "25%", borderRadius: 4 }} />
                  </div>
                  <div className="ios-skeleton" style={{ height: 4, borderRadius: 2 }} />
                </div>
              ))
            ) : bySymbol.length === 0 ? (
              <div style={{ fontSize: 13, color: "rgba(232,234,237,0.20)", textAlign: "center", padding: "20px 0" }}>No data</div>
            ) : bySymbol.map(({ sym, pnl, count }) => (
              <div key={sym} style={{ marginBottom: 10 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontSize: 12, color: "#E8EAED", fontWeight: 600 }}>{sym}</span>
                  <span style={{ fontSize: 12, fontFamily: MONO, color: pnlColor(pnl) }}>{fmtUsd(pnl)}</span>
                </div>
                <div style={{ height: 4, background: "rgba(255,255,255,0.06)", borderRadius: 2, overflow: "hidden" }}>
                  <div style={{
                    height: "100%", width: `${(Math.abs(pnl) / maxAbsPnl) * 100}%`,
                    background: pnl > 0 ? "#34C759" : "#FF3B30", borderRadius: 2,
                  }} />
                </div>
                <div style={{ fontSize: 10, color: "rgba(232,234,237,0.25)", marginTop: 3, fontFamily: MONO }}>{count} trade{count !== 1 ? "s" : ""}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Monthly P&L */}
        <div style={{ flex: "1 1 220px", minWidth: 0 }}>
          <div style={{ ...card, padding: "20px" }}>
            <div style={sectionLabel}>Monthly P&L · Last 6 Months</div>
            {loading ? (
              [0,1,2,3,4,5].map(i => (
                <div key={i} className="skel-row" style={{ marginBottom: 14 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
                    <div className="ios-skeleton" style={{ height: 12, width: "22%", borderRadius: 4 }} />
                    <div className="ios-skeleton" style={{ height: 13, width: "28%", borderRadius: 4 }} />
                  </div>
                  <div className="ios-skeleton" style={{ height: 6, borderRadius: 3 }} />
                </div>
              ))
            ) : byMonth.length === 0 ? (
              <div style={{ fontSize: 13, color: "rgba(232,234,237,0.20)", textAlign: "center", padding: "20px 0" }}>No closed trades</div>
            ) : byMonth.map(([month, pnl]) => (
              <div key={month} style={{ marginBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
                  <span style={{ fontSize: 12, color: "rgba(232,234,237,0.55)" }}>
                    {new Date(month + "-15").toLocaleDateString("en-US", { month: "short", year: "2-digit" })}
                  </span>
                  <span style={{ fontSize: 13, fontFamily: MONO, fontWeight: 700, color: pnlColor(pnl) }}>{fmtUsd(pnl)}</span>
                </div>
                <div style={{ height: 6, background: "rgba(255,255,255,0.06)", borderRadius: 3, overflow: "hidden" }}>
                  <div style={{
                    height: "100%", width: `${(Math.abs(pnl) / maxMonthPnl) * 100}%`,
                    background: pnl > 0 ? "#34C759" : "#FF3B30", borderRadius: 3,
                  }} />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* By strategy */}
        <div style={{ flex: "1 1 220px", minWidth: 0 }}>
          <div style={{ ...card, padding: "20px" }}>
            <div style={sectionLabel}>P&L by Strategy</div>
            {loading ? (
              [0,1,2,3].map(i => (
                <div key={i} className="skel-row" style={{ padding: "10px 12px", marginBottom: 8, borderRadius: 8, background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                    <div className="ios-skeleton" style={{ height: 12, width: "45%", borderRadius: 4 }} />
                    <div className="ios-skeleton" style={{ height: 13, width: "25%", borderRadius: 4 }} />
                  </div>
                  <div style={{ display: "flex", gap: 16 }}>
                    <div className="ios-skeleton" style={{ height: 11, width: "30%", borderRadius: 3 }} />
                    <div className="ios-skeleton" style={{ height: 11, width: "22%", borderRadius: 3 }} />
                  </div>
                </div>
              ))
            ) : byStrategy.length === 0 ? (
              <div style={{ fontSize: 13, color: "rgba(232,234,237,0.20)", textAlign: "center", padding: "20px 0" }}>No data</div>
            ) : byStrategy.map(({ strat, pnl, total, wr }) => (
              <div key={strat} style={{
                padding: "10px 12px", marginBottom: 8, borderRadius: 8,
                background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.07)",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: "#E8EAED", maxWidth: "60%", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {strat}
                  </span>
                  <span style={{ fontSize: 13, fontFamily: MONO, fontWeight: 700, color: pnlColor(pnl) }}>
                    {fmtUsd(pnl)}
                  </span>
                </div>
                <div style={{ display: "flex", gap: 16 }}>
                  <span style={{ fontSize: 11, color: "rgba(232,234,237,0.35)" }}>{total} trades</span>
                  <span style={{ fontSize: 11, color: wr >= 50 ? "#34C759" : "#FF9F0A" }}>{wr.toFixed(0)}% WR</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}