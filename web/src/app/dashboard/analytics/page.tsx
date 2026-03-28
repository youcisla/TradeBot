"use client";

import { useEffect, useState, useCallback } from "react";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import { formatChartDate } from "@/lib/time";

// ── Types ─────────────────────────────────────────────────────────────────────

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

const SYM_COLORS = ["#00fd87","#00d2fd","#e966ff","#ffb86c","#ff716c","#79dfff","#a4ffb9","#1cd5ff","#d501f9","#ffffff"];
const TOOLTIP_STYLE = { background: "#0e0e0e", border: "1px solid #494847", fontSize: 11, fontFamily: "'JetBrains Mono', monospace", color: "#ffffff" };

// ── Sub-components ────────────────────────────────────────────────────────────

function KpiCard({ label, value, sub, color = "#00fd87" }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-surface border-l-2 p-4 relative overflow-hidden" style={{ borderLeftColor: color }}>
      <div className="text-[9px] text-on-surface-variant uppercase tracking-[0.18em] mb-2">{label}</div>
      <div className="text-2xl font-bold font-mono" style={{ color }}>{value}</div>
      {sub && <div className="text-[10px] text-on-surface-variant mt-1">{sub}</div>}
    </div>
  );
}

function ChartCard({ title, accent = "#494847", children }: { title: string; accent?: string; children: React.ReactNode }) {
  return (
    <div className="bg-surface p-4 border border-outline-variant/10">
      <div className="text-[9px] font-bold uppercase tracking-[0.2em] mb-4" style={{ color: accent }}>{title}</div>
      {children}
    </div>
  );
}

function NoData() {
  return (
    <div className="h-44 flex items-center justify-center text-on-surface-variant text-[11px] uppercase tracking-widest">
      no data yet
    </div>
  );
}

function SymbolPill({ value, options, onChange }: { value: string | null; options: string[]; onChange: (v: string | null) => void }) {
  return (
    <div className="flex gap-2 flex-wrap">
      <button
        onClick={() => onChange(null)}
        className={`px-3 py-1 text-[10px] font-bold uppercase tracking-wider duration-0 ${!value ? "bg-primary-fixed/10 text-primary-fixed border border-primary-fixed/30" : "text-on-surface-variant border border-outline-variant/20 hover:text-on-surface"}`}
      >
        All
      </button>
      {options.map((s) => (
        <button
          key={s}
          onClick={() => onChange(s === value ? null : s)}
          className={`px-3 py-1 text-[10px] font-bold uppercase tracking-wider duration-0 ${value === s ? "bg-secondary/10 text-secondary border border-secondary/30" : "text-on-surface-variant border border-outline-variant/20 hover:text-on-surface"}`}
        >
          {s}
        </button>
      ))}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [range, setRange]             = useState<Range>("all");
  const [symbol, setSymbol]           = useState<string | null>(null);
  const [kpis, setKpis]               = useState<Kpis | null>(null);
  const [dailyPnl, setDailyPnl]       = useState<DayPnl[]>([]);
  const [symbolStats, setSymbolStats] = useState<SymbolStat[]>([]);
  const [dirStats, setDirStats]       = useState<DirStat[]>([]);
  const [closedTrades, setClosedTrades] = useState<Trade[]>([]);
  const [loading, setLoading]           = useState(true);

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
  const filteredTrades = symbol ? closedTrades.filter((t) => t.symbol === symbol) : closedTrades;
  const fWins    = filteredTrades.filter((t) => Number(t.pnl) > 0).length;
  const fTotal   = filteredTrades.length;
  const fTotalPnl = filteredTrades.reduce((s, t) => s + Number(t.pnl), 0);
  const fAvgPnl  = fTotal > 0 ? fTotalPnl / fTotal : 0;
  const fBest    = fTotal > 0 ? Math.max(...filteredTrades.map((t) => Number(t.pnl))) : 0;
  const fWorst   = fTotal > 0 ? Math.min(...filteredTrades.map((t) => Number(t.pnl))) : 0;
  const winRate  = fTotal > 0 ? (fWins / fTotal) * 100 : 0;
  const winRateColor = winRate >= 55 ? "#00fd87" : winRate >= 45 ? "#ffb86c" : "#ff716c";

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
    return { date: p.date, drawdown: Math.min(0, peak > 0 ? ((p.cum - peak) / peak) * 100 : 0) };
  });

  const filteredSymbolStats = symbol ? symbolStats.filter((s) => s.symbol === symbol) : symbolStats;
  const symbolPie  = filteredSymbolStats.map((s) => ({ name: s.symbol, value: Math.abs(Number(s.total_pnl)), pnl: Number(s.total_pnl) }));
  const symbolBars = filteredSymbolStats.map((s) => ({ symbol: s.symbol, wins: Number(s.wins), losses: Number(s.losses) }));
  const filteredDirStats = symbol
    ? (() => {
        const buys  = filteredTrades.filter((t) => t.direction === "BUY");
        const sells = filteredTrades.filter((t) => t.direction === "SELL");
        return [...(buys.length ? [{ name: "BUY", value: buys.length }] : []),
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

  const allSymbols = [...new Set(closedTrades.map((t) => t.symbol))].sort();

  return (
    <div className="flex flex-col gap-5">

      {/* ── Page Header ── */}
      <div className="flex items-end justify-between gap-4 flex-wrap">
        <div>
          <span className="text-[10px] font-bold tracking-widest text-on-surface-variant uppercase block mb-1">PERFORMANCE</span>
          <h1 className="text-3xl font-extrabold uppercase tracking-tighter">Analytics</h1>
        </div>
        <div className="flex items-center gap-4 flex-wrap">
          {/* Range selector */}
          <div className="flex gap-1">
            {(["24h","7d","30d","all"] as Range[]).map((r) => (
              <button
                key={r}
                onClick={() => setRange(r)}
                className={`px-3 py-1 text-[10px] font-bold uppercase tracking-wider duration-0 ${range === r ? "bg-secondary/10 text-secondary border border-secondary/30" : "text-on-surface-variant border border-outline-variant/20 hover:text-on-surface"}`}
              >
                {r === "all" ? "All Time" : r}
              </button>
            ))}
          </div>
          {loading && (
            <div className="flex items-center gap-2 text-[10px] text-on-surface-variant">
              <div className="w-3 h-3 border border-outline-variant border-t-primary-fixed rounded-full animate-spin" />
              Loading…
            </div>
          )}
        </div>
      </div>

      {/* Symbol filter */}
      <SymbolPill value={symbol} options={allSymbols} onChange={setSymbol} />

      {/* KPI rows */}
      {displayKpis && (
        <>
          <div className="grid grid-cols-4 xl:grid-cols-8 gap-3">
            <KpiCard label="Total Trades" value={String(displayKpis.total_trades)} color="#adaaaa" />
            <KpiCard label="Win Rate"     value={`${winRate.toFixed(1)}%`} color={winRateColor} />
            <KpiCard
              label="Total P&L"
              value={`${Number(displayKpis.total_pnl) >= 0 ? "+" : ""}$${Number(displayKpis.total_pnl).toFixed(2)}`}
              color={Number(displayKpis.total_pnl) >= 0 ? "#00fd87" : "#ff716c"}
              sub={`${displayKpis.wins}W / ${displayKpis.losses}L`}
            />
            <KpiCard label="Avg P&L"     value={`${Number(displayKpis.avg_pnl) >= 0 ? "+" : ""}$${Number(displayKpis.avg_pnl).toFixed(2)}`} color={Number(displayKpis.avg_pnl) >= 0 ? "#00fd87" : "#ff716c"} />
            <KpiCard label="Best Trade"  value={`+$${Number(displayKpis.best_trade).toFixed(2)}`}  color="#00fd87" />
            <KpiCard label="Worst Trade" value={`$${Number(displayKpis.worst_trade).toFixed(2)}`} color="#ff716c" />
            <KpiCard label="Avg Duration" value={`${Math.floor(Number(displayKpis.avg_duration_min))}m`} color="#adaaaa" sub="per trade" />
            <KpiCard label="Total Closed" value={String(filteredTrades.length)} color="#00d2fd" />
          </div>
        </>
      )}

      {/* Charts row 1 */}
      <div className="grid grid-cols-2 gap-4">
        <ChartCard title="Cumulative P&L" accent="#00fd87">
          {equityCurve.length < 2 ? <NoData /> : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={equityCurve}>
                <defs>
                  <linearGradient id="gCum" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#00fd87" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#00fd87" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#494847" strokeOpacity={0.2} />
                <XAxis dataKey="date" tickFormatter={formatChartDate} tick={{ fill: "#777575", fontSize: 9, fontFamily: "JetBrains Mono" }} />
                <YAxis tick={{ fill: "#777575", fontSize: 9, fontFamily: "JetBrains Mono" }} />
                <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(l) => formatChartDate(String(l))} formatter={(v) => [`$${Number(v).toFixed(2)}`, "Cum PnL"]} />
                <Area type="monotone" dataKey="cum" stroke="#00fd87" fill="url(#gCum)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Drawdown %" accent="#ff716c">
          {drawdownCurve.length < 2 ? <NoData /> : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={drawdownCurve}>
                <defs>
                  <linearGradient id="gDD" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#ff716c" stopOpacity={0.2} />
                    <stop offset="95%" stopColor="#ff716c" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#494847" strokeOpacity={0.2} />
                <XAxis dataKey="date" tickFormatter={formatChartDate} tick={{ fill: "#777575", fontSize: 9, fontFamily: "JetBrains Mono" }} />
                <YAxis tick={{ fill: "#777575", fontSize: 9, fontFamily: "JetBrains Mono" }} />
                <Tooltip contentStyle={TOOLTIP_STYLE} labelFormatter={(l) => formatChartDate(String(l))} formatter={(v) => [`${Number(v).toFixed(2)}%`, "Drawdown"]} />
                <Area type="monotone" dataKey="drawdown" stroke="#ff716c" fill="url(#gDD)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>

      {/* Charts row 2 */}
      <div className="grid grid-cols-3 gap-4">
        <ChartCard title="Daily P&L" accent="#00d2fd">
          {filteredDailyPnl.length === 0 ? <NoData /> : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={filteredDailyPnl.map((d) => ({ ...d, pnl: Number(d.pnl) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#494847" strokeOpacity={0.2} />
                <XAxis dataKey="day" tickFormatter={formatChartDate} tick={{ fill: "#777575", fontSize: 9, fontFamily: "JetBrains Mono" }} />
                <YAxis tick={{ fill: "#777575", fontSize: 9, fontFamily: "JetBrains Mono" }} />
                <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(v) => [`$${Number(v).toFixed(2)}`, "PnL"]} />
                <Bar dataKey="pnl">
                  {filteredDailyPnl.map((d, i) => <Cell key={i} fill={Number(d.pnl) >= 0 ? "#00fd87" : "#ff716c"} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Trades by Symbol" accent="#e966ff">
          {symbolBars.length === 0 ? <NoData /> : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={symbolBars} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#494847" strokeOpacity={0.2} />
                <XAxis type="number" tick={{ fill: "#777575", fontSize: 9, fontFamily: "JetBrains Mono" }} />
                <YAxis dataKey="symbol" type="category" tick={{ fill: "#adaaaa", fontSize: 9, fontFamily: "JetBrains Mono" }} width={64} />
                <Tooltip contentStyle={TOOLTIP_STYLE} />
                <Legend wrapperStyle={{ fontSize: 9, fontFamily: "JetBrains Mono", color: "#adaaaa" }} />
                <Bar dataKey="wins"   stackId="a" fill="#00fd87" name="Wins" />
                <Bar dataKey="losses" stackId="a" fill="#ff716c" name="Losses" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        {/* Symbol ranking */}
        <ChartCard title="Symbol Ranking" accent="#ffb86c">
          {filteredSymbolStats.length === 0 ? <NoData /> : (
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-outline-variant/20">
                  {["Symbol","Trades","Win%","PnL"].map((h) => (
                    <th key={h} className="pb-2 text-[9px] uppercase tracking-widest text-outline font-normal text-left last:text-right">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filteredSymbolStats.map((s) => {
                  const wr  = s.total > 0 ? ((Number(s.wins) / Number(s.total)) * 100).toFixed(0) : "0";
                  const pnl = Number(s.total_pnl);
                  return (
                    <tr key={s.symbol} className="border-b border-outline-variant/10 hover:bg-surface-bright duration-0">
                      <td className="py-2 text-secondary font-bold">{s.symbol}</td>
                      <td className="py-2 text-on-surface-variant">{s.total}</td>
                      <td className="py-2" style={{ color: Number(wr) >= 50 ? "#00fd87" : "#ff716c" }}>{wr}%</td>
                      <td className="py-2 text-right font-bold" style={{ color: pnl >= 0 ? "#00fd87" : "#ff716c" }}>
                        {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </ChartCard>
      </div>

      {/* Pie row */}
      <div className="grid grid-cols-2 gap-4">
        <ChartCard title="P&L by Symbol">
          {symbolPie.length === 0 ? <NoData /> : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={symbolPie} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name }) => name} labelLine={{ stroke: "#777575" }}>
                  {symbolPie.map((_, i) => <Cell key={i} fill={SYM_COLORS[i % SYM_COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={TOOLTIP_STYLE} formatter={(_v, _n, e) => [`${(e.payload?.pnl ?? 0) >= 0 ? "+" : ""}$${Number(e.payload?.pnl ?? 0).toFixed(2)}`, "PnL"]} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard title="Buy vs Sell">
          {filteredDirStats.length === 0 ? <NoData /> : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={filteredDirStats} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, value }) => `${name}: ${value}`} labelLine={{ stroke: "#777575" }}>
                  <Cell fill="#00fd87" />
                  <Cell fill="#ff716c" />
                </Pie>
                <Tooltip contentStyle={TOOLTIP_STYLE} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </ChartCard>
      </div>
    </div>
  );
}
