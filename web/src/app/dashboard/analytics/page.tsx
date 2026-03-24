"use client";

import { useEffect, useState, useCallback } from "react";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import { formatChartDate } from "@/lib/time";
import SymbolFilter from "@/components/SymbolFilter";
import PageHeader from "@/components/PageHeader";

interface Trade {
  id: string; symbol: string; direction: string; pnl: number;
  close_time: string | null; open_time: string; status: string; strategy: string;
}
interface SymbolStat {
  symbol: string; total: number; wins: number; losses: number;
  total_pnl: number; avg_pnl: number; avg_win: number; avg_loss: number;
}
interface DirStat { direction: string; total: number; total_pnl: number; }
interface DayPnl  { day: string; trades: number; pnl: number; }
interface Kpis {
  total_trades: number; wins: number; losses: number; total_pnl: number;
  avg_pnl: number; best_trade: number; worst_trade: number; avg_duration_min: number;
}
type Range = "24h" | "7d" | "30d" | "all";

function sinceDate(r: Range): string | undefined {
  if (r === "all") return undefined;
  const d = new Date();
  if (r === "24h") d.setHours(d.getHours() - 24);
  else if (r === "7d") d.setDate(d.getDate() - 7);
  else d.setDate(d.getDate() - 30);
  return d.toISOString();
}

const SYM_COLORS = ["#00ff88","#00d4ff","#f5c518","#ff9d00","#d500f9","#4da6ff","#ff4455","#76ff03","#bf7fff","#f0f0f0"];

// ── KPI Card ────────────────────────────────────────────────────────────────

function KpiCard({
  label, value, sub, color = "#00ff88", glowColor,
}: {
  label: string; value: string; sub?: string; color?: string; glowColor?: string;
}) {
  const glow = glowColor ?? color;
  return (
    <div style={{
      background: "#0e0e10",
      border: "1px solid #1c1c28",
      borderRadius: 8,
      padding: "14px 16px",
      position: "relative",
      overflow: "hidden",
    }}>
      <div style={{
        position: "absolute", top: 0, left: 0, right: 0, height: 1,
        background: `linear-gradient(90deg, transparent, ${glow}33, transparent)`,
      }} />
      <div style={{
        fontSize: 8.5, fontFamily: "'JetBrains Mono', monospace",
        color: "#607888", letterSpacing: "0.18em", textTransform: "uppercase",
        marginBottom: 6,
      }}>
        {label}
      </div>
      <div style={{
        fontSize: 20, fontFamily: "'JetBrains Mono', monospace",
        fontWeight: 700, color,
        textShadow: `0 0 12px ${glow}55`,
        lineHeight: 1.1,
      }}>
        {value}
      </div>
      {sub && (
        <div style={{
          fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
          color: "#607888", marginTop: 4,
        }}>
          {sub}
        </div>
      )}
    </div>
  );
}

// ── Chart card ──────────────────────────────────────────────────────────────

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{
      background: "#0e0e10", border: "1px solid #1c1c28",
      borderRadius: 8, padding: "16px",
    }}>
      <div style={{
        fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
        color: "#607888", letterSpacing: "0.2em", textTransform: "uppercase",
        marginBottom: 14,
      }}>
        {title}
      </div>
      {children}
    </div>
  );
}

function NoData() {
  return (
    <div style={{
      height: 180, display: "flex", alignItems: "center", justifyContent: "center",
      color: "#3a5a3a", fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
    }}>
      no data yet
    </div>
  );
}

const TOOLTIP_STYLE = { background: "#0e0e10", border: "1px solid #1c1c28", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" };

// ── Range chip ──────────────────────────────────────────────────────────────

function RangeChip({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button onClick={onClick} style={{
      padding: "4px 12px", borderRadius: 4, fontSize: 10,
      fontFamily: "'JetBrains Mono', monospace", fontWeight: 700,
      letterSpacing: "0.08em", textTransform: "uppercase", cursor: "pointer",
      border: active ? "1px solid rgba(0,212,255,0.5)" : "1px solid #1c1c28",
      background: active ? "rgba(0,212,255,0.12)" : "transparent",
      color: active ? "#00d4ff" : "#607888",
      transition: "all 0.15s",
    }}>
      {label === "all" ? "All Time" : label}
    </button>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [range, setRange]             = useState<Range>("all");
  const [symbol, setSymbol]           = useState<string | null>(null);
  const [kpis, setKpis]               = useState<Kpis | null>(null);
  const [dailyPnl, setDailyPnl]       = useState<DayPnl[]>([]);
  const [symbolStats, setSymbolStats] = useState<SymbolStat[]>([]);
  const [dirStats, setDirStats]       = useState<DirStat[]>([]);
  const [closedTrades, setClosedTrades] = useState<Trade[]>([]);
  const [loading, setLoading]         = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    const since = sinceDate(range);
    const qs = since ? `?since=${encodeURIComponent(since)}` : "";
    fetch(`/api/analytics${qs}`)
      .then((r) => { if (!r.ok) throw new Error(); return r.json(); })
      .then((d) => {
        setKpis(d.kpis ?? null);
        setDailyPnl(d.dailyPnl ?? []);
        setSymbolStats(d.symbolStats ?? []);
        setDirStats(d.directionStats ?? []);
        setClosedTrades(d.closedTrades ?? []);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [range]);

  useEffect(() => { load(); }, [load]);

  // Derived
  const filteredTrades  = symbol ? closedTrades.filter((t) => t.symbol === symbol) : closedTrades;
  const fWins           = filteredTrades.filter((t) => Number(t.pnl) > 0).length;
  const fTotal          = filteredTrades.length;
  const fTotalPnl       = filteredTrades.reduce((s, t) => s + Number(t.pnl), 0);
  const fAvgPnl         = fTotal > 0 ? fTotalPnl / fTotal : 0;
  const fBest           = fTotal > 0 ? Math.max(...filteredTrades.map((t) => Number(t.pnl))) : 0;
  const fWorst          = fTotal > 0 ? Math.min(...filteredTrades.map((t) => Number(t.pnl))) : 0;
  const winRate         = fTotal > 0 ? (fWins / fTotal) * 100 : 0;
  const winRateColor    = winRate >= 55 ? "#00ff88" : winRate >= 45 ? "#f5c518" : "#ff4455";

  const displayKpis: Kpis | null = symbol && kpis
    ? { total_trades: fTotal, wins: fWins, losses: fTotal - fWins, total_pnl: fTotalPnl, avg_pnl: fAvgPnl, best_trade: fBest, worst_trade: fWorst, avg_duration_min: kpis.avg_duration_min }
    : kpis;

  const equityCurve = filteredTrades.reduce<{ date: string; cum: number }[]>((acc, t) => {
    const prev = acc.length > 0 ? acc[acc.length - 1].cum : 0;
    acc.push({ date: t.close_time ?? t.open_time, cum: prev + Number(t.pnl) });
    return acc;
  }, []);

  let peak = 0;
  const drawdownCurve = equityCurve.map((p) => {
    if (p.cum > peak) peak = p.cum;
    const dd = peak > 0 ? ((p.cum - peak) / peak) * 100 : 0;
    return { date: p.date, drawdown: Math.min(0, dd) };
  });

  const filteredSymbolStats = symbol ? symbolStats.filter((s) => s.symbol === symbol) : symbolStats;
  const symbolPie  = filteredSymbolStats.map((s) => ({ name: s.symbol, value: Math.abs(Number(s.total_pnl)), pnl: Number(s.total_pnl) }));
  const symbolBars = filteredSymbolStats.map((s) => ({ symbol: s.symbol, wins: Number(s.wins), losses: Number(s.losses) }));

  const filteredDirStats = symbol
    ? (() => {
        const buys  = filteredTrades.filter((t) => t.direction === "BUY");
        const sells = filteredTrades.filter((t) => t.direction === "SELL");
        return [...(buys.length  ? [{ name: "BUY",  value: buys.length }]  : []),
                ...(sells.length ? [{ name: "SELL", value: sells.length }] : [])];
      })()
    : dirStats.map((d) => ({ name: d.direction, value: Number(d.total) }));

  const filteredDailyPnl = symbol
    ? (() => {
        const byDay: Record<string, number> = {};
        for (const t of filteredTrades) {
          const day = (t.close_time ?? t.open_time).slice(0, 10);
          byDay[day] = (byDay[day] ?? 0) + Number(t.pnl);
        }
        return Object.entries(byDay).sort(([a],[b]) => a.localeCompare(b)).map(([day, pnl]) => ({ day, pnl, trades: 0 }));
      })()
    : dailyPnl;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <PageHeader subsystem="Performance" title="Analytics" accent="#00d4ff" />
        <div style={{ display: "flex", gap: 6 }}>
          {(["24h","7d","30d","all"] as Range[]).map((r) => (
            <RangeChip key={r} label={r} active={range === r} onClick={() => setRange(r)} />
          ))}
        </div>
      </div>

      <SymbolFilter value={symbol} onChange={setSymbol} />

      {loading && (
        <div style={{
          padding: "48px 20px", textAlign: "center",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9, letterSpacing: "0.2em", textTransform: "uppercase",
          color: "#607888",
        }}>
          <div style={{
            width: 20, height: 20, border: "1.5px solid #1c1c28",
            borderTop: "1.5px solid #00ff88", borderRadius: "50%",
            animation: "spin 0.8s linear infinite",
            margin: "0 auto 12px",
          }} />
          loading…
          <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
        </div>
      )}

      {/* KPI row */}
      {displayKpis && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          <KpiCard label="Total Trades" value={String(displayKpis.total_trades)} color="#9aa8b8" />
          <KpiCard label="Win Rate"  value={`${winRate.toFixed(1)}%`} color={winRateColor} glowColor={winRateColor} />
          <KpiCard
            label="Total P&L"
            value={`${Number(displayKpis.total_pnl) >= 0 ? "+" : ""}${Number(displayKpis.total_pnl).toFixed(2)}`}
            color={Number(displayKpis.total_pnl) >= 0 ? "#00ff88" : "#ff4455"}
            sub={`${displayKpis.wins}W / ${displayKpis.losses}L`}
          />
          <KpiCard label="Avg P&L" value={Number(displayKpis.avg_pnl).toFixed(2)} color={Number(displayKpis.avg_pnl) >= 0 ? "#00ff88" : "#ff4455"} />
        </div>
      )}

      {/* Second KPI row */}
      {displayKpis && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
          <KpiCard label="Best Trade"  value={`+${Number(displayKpis.best_trade).toFixed(2)}`}  color="#00ff88" />
          <KpiCard label="Worst Trade" value={Number(displayKpis.worst_trade).toFixed(2)} color="#ff4455" />
          <KpiCard label="Avg Duration" value={`${Math.floor(Number(displayKpis.avg_duration_min))}m`} color="#7a8a9a" sub="per trade" />
          <KpiCard label="Total Closed" value={String(filteredTrades.length)} color="#4da6ff" />
        </div>
      )}

      {/* Charts row 1: Equity + Drawdown */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <ChartCard title="Cumulative P&L">
          {equityCurve.length < 2 ? <NoData /> : (
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={equityCurve}>
                <defs>
                  <linearGradient id="gCum" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#00ff88" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#00ff88" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1c1c28" />
                <XAxis dataKey="date" tickFormatter={formatChartDate} tick={{ fill: "#607888", fontSize: 9, fontFamily: "JetBrains Mono" }} />
                <YAxis tick={{ fill: "#607888", fontSize: 9, fontFamily: "JetBrains Mono" }} />
                <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(l) => formatChartDate(String(l))} formatter={(v) => [`${Number(v).toFixed(2)}`, "Cum PnL"]} />
                <Area type="monotone" dataKey="cum" stroke="#00ff88" fill="url(#gCum)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Drawdown %">
          {drawdownCurve.length < 2 ? <NoData /> : (
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={drawdownCurve}>
                <defs>
                  <linearGradient id="gDD" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#ff4455" stopOpacity={0.25} />
                    <stop offset="95%" stopColor="#ff4455" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1c1c28" />
                <XAxis dataKey="date" tickFormatter={formatChartDate} tick={{ fill: "#607888", fontSize: 9, fontFamily: "JetBrains Mono" }} />
                <YAxis tick={{ fill: "#607888", fontSize: 9, fontFamily: "JetBrains Mono" }} />
                <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(l) => formatChartDate(String(l))} formatter={(v) => [`${Number(v).toFixed(2)}%`, "Drawdown"]} />
                <Area type="monotone" dataKey="drawdown" stroke="#ff4455" fill="url(#gDD)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      {/* Charts row 2: Daily PnL + Symbol bars */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
        <ChartCard title="Daily P&L">
          {filteredDailyPnl.length === 0 ? <NoData /> : (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={filteredDailyPnl.map((d) => ({ ...d, pnl: Number(d.pnl) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1c1c28" />
                <XAxis dataKey="day" tickFormatter={formatChartDate} tick={{ fill: "#607888", fontSize: 9, fontFamily: "JetBrains Mono" }} />
                <YAxis tick={{ fill: "#607888", fontSize: 9, fontFamily: "JetBrains Mono" }} />
                <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [`${Number(v).toFixed(2)}`, "PnL"]} />
                <Bar dataKey="pnl">
                  {filteredDailyPnl.map((d, i) => (
                    <Cell key={i} fill={Number(d.pnl) >= 0 ? "#00ff88" : "#ff4455"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Trades by Symbol">
          {symbolBars.length === 0 ? <NoData /> : (
            <ResponsiveContainer width="100%" height={180}>
              <BarChart data={symbolBars} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1c1c28" />
                <XAxis type="number" tick={{ fill: "#607888", fontSize: 9, fontFamily: "JetBrains Mono" }} />
                <YAxis dataKey="symbol" type="category" tick={{ fill: "#9aa8b8", fontSize: 9, fontFamily: "JetBrains Mono" }} width={70} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Legend wrapperStyle={{ fontSize: 9, fontFamily: "JetBrains Mono", color: "#7a8a9a" }} />
                <Bar dataKey="wins"   stackId="a" fill="#00ff88" name="Wins" />
                <Bar dataKey="losses" stackId="a" fill="#ff4455" name="Losses" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      {/* Charts row 3: Pie charts + Symbol ranking */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>

        <ChartCard title="P&L by Symbol">
          {symbolPie.length === 0 ? <NoData /> : (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={symbolPie} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={72} label={({ name }) => name} labelLine={{ stroke: "#607888" }}>
                  {symbolPie.map((_, i) => <Cell key={i} fill={SYM_COLORS[i % SYM_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(_v, _n, entry) => [`${(entry.payload?.pnl ?? 0) >= 0 ? "+" : ""}${Number(entry.payload?.pnl ?? 0).toFixed(2)}`, "PnL"]} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Buy vs Sell">
          {filteredDirStats.length === 0 ? <NoData /> : (
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie data={filteredDirStats} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={72} label={({ name, value }) => `${name}: ${value}`} labelLine={{ stroke: "#607888" }}>
                  <Cell fill="#00ff88" />
                  <Cell fill="#ff4455" />
                </Pie>
                <Tooltip contentStyle={TOOLTIP_STYLE} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* Symbol ranking table */}
        <ChartCard title="Symbol Ranking">
          {filteredSymbolStats.length === 0 ? (
            <div style={{ color: "#3a5a3a", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, padding: "20px 0" }}>no data</div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 10, fontFamily: "'JetBrains Mono', monospace" }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #1c1c28" }}>
                  {["Symbol","Trades","Win%","PnL"].map((h) => (
                    <th key={h} style={{
                      padding: "4px 6px", textAlign: h === "Symbol" ? "left" : "right",
                      fontSize: 8.5, letterSpacing: "0.12em", textTransform: "uppercase", color: "#607888",
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredSymbolStats.map((s) => {
                  const wr  = s.total > 0 ? ((Number(s.wins) / Number(s.total)) * 100).toFixed(0) : "0";
                  const pnl = Number(s.total_pnl);
                  return (
                    <tr key={s.symbol} style={{ borderBottom: "1px solid rgba(28,28,40,0.4)" }}>
                      <td style={{ padding: "5px 6px", color: "#00d4ff", fontWeight: 700 }}>{s.symbol}</td>
                      <td style={{ padding: "5px 6px", textAlign: "right", color: "#7a8a9a" }}>{s.total}</td>
                      <td style={{ padding: "5px 6px", textAlign: "right", color: Number(wr) >= 50 ? "#00ff88" : "#ff4455" }}>{wr}%</td>
                      <td style={{ padding: "5px 6px", textAlign: "right", fontWeight: 700, color: pnl >= 0 ? "#00ff88" : "#ff4455" }}>
                        {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </ChartCard>
      </div>

    </div>
  );
}
