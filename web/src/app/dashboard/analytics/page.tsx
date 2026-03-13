"use client";

import { useEffect, useState, useCallback } from "react";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend,
} from "recharts";
import { formatChartDate } from "@/lib/time";
import SymbolFilter from "@/components/SymbolFilter";

// ── Types ───────────────────────────────────────────────────────────────

interface Trade {
  id: string;
  symbol: string;
  direction: string;
  pnl: number;
  close_time: string | null;
  open_time: string;
  status: string;
  strategy: string;
}

interface SymbolStat {
  symbol: string;
  total: number;
  wins: number;
  losses: number;
  total_pnl: number;
  avg_pnl: number;
  avg_win: number;
  avg_loss: number;
}

interface DirStat { direction: string; total: number; total_pnl: number; }
interface DayPnl { day: string; trades: number; pnl: number; }
interface Kpis {
  total_trades: number;
  wins: number;
  losses: number;
  total_pnl: number;
  avg_pnl: number;
  best_trade: number;
  worst_trade: number;
  avg_duration_min: number;
}

type Range = "24h" | "7d" | "30d" | "all";

function sinceDate(r: Range): string | undefined {
  if (r === "all") return undefined;
  const d = new Date();
  if (r === "24h") d.setHours(d.getHours() - 24);
  else if (r === "7d") d.setDate(d.getDate() - 7);
  else if (r === "30d") d.setDate(d.getDate() - 30);
  return d.toISOString();
}

const COLORS = ["#00ff41", "#06b6d4", "#eab308", "#f97316", "#d946ef", "#3b82f6", "#ef4444", "#22c55e", "#a855f7", "#14b8a6"];

const chipCls = (active: boolean) =>
  `px-3 py-1 rounded text-[10px] font-bold uppercase border transition-colors cursor-pointer ${
    active
      ? "border-matrix bg-matrix/20 text-matrix"
      : "border-terminal-border text-matrix-dim hover:text-matrix"
  }`;

// ── KPI Card ────────────────────────────────────────────────────────────

function Kpi({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="border border-terminal-border rounded bg-terminal-surface p-4">
      <div className="text-matrix-dim text-[10px] uppercase tracking-widest">{label}</div>
      <div className={`text-xl font-bold mt-1 ${color ?? "text-matrix"}`}>{value}</div>
      {sub && <div className="text-matrix-dim text-[10px] mt-1">{sub}</div>}
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const [range, setRange] = useState<Range>("all");
  const [symbol, setSymbol] = useState<string | null>(null);
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [dailyPnl, setDailyPnl] = useState<DayPnl[]>([]);
  const [symbolStats, setSymbolStats] = useState<SymbolStat[]>([]);
  const [dirStats, setDirStats] = useState<DirStat[]>([]);
  const [closedTrades, setClosedTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);

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

  // ── Derived data ──────────────────────────────────────────────────────

  // Apply symbol filter to closed trades
  const filteredTrades = symbol
    ? closedTrades.filter((t) => t.symbol === symbol)
    : closedTrades;

  // Cumulative PnL curve
  const equityCurve = filteredTrades.reduce<{ date: string; cum: number }[]>(
    (acc, t) => {
      const prev = acc.length > 0 ? acc[acc.length - 1].cum : 0;
      acc.push({ date: t.close_time ?? t.open_time, cum: prev + Number(t.pnl) });
      return acc;
    }, []
  );

  // Drawdown curve
  let peak = 0;
  const drawdownCurve = equityCurve.map((p) => {
    if (p.cum > peak) peak = p.cum;
    const dd = peak > 0 ? ((p.cum - peak) / peak) * 100 : 0;
    return { date: p.date, drawdown: Math.min(0, dd) };
  });

  // Win rate
  const fTrades = filteredTrades;
  const fWins = fTrades.filter((t) => Number(t.pnl) > 0).length;
  const fTotal = fTrades.length;
  const fTotalPnl = fTrades.reduce((s, t) => s + Number(t.pnl), 0);
  const fAvgPnl = fTotal > 0 ? fTotalPnl / fTotal : 0;
  const fBest = fTotal > 0 ? Math.max(...fTrades.map((t) => Number(t.pnl))) : 0;
  const fWorst = fTotal > 0 ? Math.min(...fTrades.map((t) => Number(t.pnl))) : 0;
  const winRate = fTotal > 0 ? ((fWins / fTotal) * 100).toFixed(1) : "0";

  // When symbol is selected, override KPIs with filtered values
  const displayKpis: Kpis | null = symbol && kpis
    ? {
        total_trades: fTotal,
        wins: fWins,
        losses: fTotal - fWins,
        total_pnl: fTotalPnl,
        avg_pnl: fAvgPnl,
        best_trade: fBest,
        worst_trade: fWorst,
        avg_duration_min: kpis.avg_duration_min,
      }
    : kpis;

  // Symbol PnL for pie chart
  const filteredSymbolStats = symbol
    ? symbolStats.filter((s) => s.symbol === symbol)
    : symbolStats;
  const symbolPie = filteredSymbolStats.map((s) => ({
    name: s.symbol,
    value: Math.abs(Number(s.total_pnl)),
    pnl: Number(s.total_pnl),
  }));

  // Trades by symbol for bar chart
  const symbolBars = filteredSymbolStats.map((s) => ({
    symbol: s.symbol,
    wins: Number(s.wins),
    losses: Number(s.losses),
    pnl: Number(s.total_pnl),
  }));

  // Direction pie
  const filteredDirStats = symbol
    ? (() => {
        const buys = filteredTrades.filter((t) => t.direction === "BUY");
        const sells = filteredTrades.filter((t) => t.direction === "SELL");
        return [
          ...(buys.length > 0 ? [{ name: "BUY", value: buys.length }] : []),
          ...(sells.length > 0 ? [{ name: "SELL", value: sells.length }] : []),
        ];
      })()
    : dirStats.map((d) => ({
        name: d.direction,
        value: Number(d.total),
      }));

  // Daily PnL (filtered)
  const filteredDailyPnl = symbol
    ? (() => {
        const byDay: Record<string, number> = {};
        for (const t of filteredTrades) {
          const day = (t.close_time ?? t.open_time).slice(0, 10);
          byDay[day] = (byDay[day] ?? 0) + Number(t.pnl);
        }
        return Object.entries(byDay)
          .sort(([a], [b]) => a.localeCompare(b))
          .map(([day, pnl]) => ({ day, pnl, trades: 0 }));
      })()
    : dailyPnl;

  // ── Render ────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4">
        <h1 className="text-matrix text-lg font-bold">Analytics</h1>
        <div className="flex gap-2">
          {(["24h", "7d", "30d", "all"] as Range[]).map((r) => (
            <button key={r} className={chipCls(range === r)} onClick={() => setRange(r)}>
              {r === "all" ? "All Time" : r}
            </button>
          ))}
        </div>
      </div>

      <SymbolFilter value={symbol} onChange={setSymbol} />

      {loading && <div className="text-matrix-dim text-sm">Loading analytics…</div>}

      {/* KPI row */}
      {displayKpis && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3">
          <Kpi label="Total Trades" value={String(displayKpis.total_trades)} />
          <Kpi label="Wins" value={String(displayKpis.wins)} color="text-green-400" />
          <Kpi label="Losses" value={String(displayKpis.losses)} color="text-red-500" />
          <Kpi label="Win Rate" value={`${winRate}%`} color={Number(winRate) >= 50 ? "text-green-400" : "text-red-500"} />
          <Kpi
            label="Total PnL"
            value={`${Number(displayKpis.total_pnl) >= 0 ? "+" : ""}${Number(displayKpis.total_pnl).toFixed(2)}`}
            color={Number(displayKpis.total_pnl) >= 0 ? "text-green-400" : "text-red-500"}
          />
          <Kpi label="Avg PnL" value={Number(displayKpis.avg_pnl).toFixed(2)} />
          <Kpi label="Best Trade" value={`+${Number(displayKpis.best_trade).toFixed(2)}`} color="text-green-400" />
          <Kpi label="Worst Trade" value={Number(displayKpis.worst_trade).toFixed(2)} color="text-red-500" />
        </div>
      )}

      {/* Charts row 1: Equity curve + Drawdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Cumulative PnL / Equity Curve */}
        <div className="border border-terminal-border rounded bg-terminal-surface p-4">
          <div className="text-matrix-dim text-[10px] uppercase tracking-widest mb-3">Cumulative PnL</div>
          {equityCurve.length < 2 ? (
            <div className="text-matrix-dim text-sm h-48 flex items-center justify-center">Not enough data</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={equityCurve}>
                <defs><linearGradient id="gCum" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00ff41" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00ff41" stopOpacity={0} />
                </linearGradient></defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                <XAxis dataKey="date" tickFormatter={formatChartDate} tick={{ fill: "#555", fontSize: 10 }} />
                <YAxis tick={{ fill: "#555", fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ background: "#111", border: "1px solid #1a1a1a", fontSize: 11 }}
                  labelFormatter={(label: any) => formatChartDate(String(label))}
                  formatter={(v: any) => [`${Number(v).toFixed(2)}`, "Cum PnL"]}
                />
                <Area type="monotone" dataKey="cum" stroke="#00ff41" fill="url(#gCum)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Drawdown */}
        <div className="border border-terminal-border rounded bg-terminal-surface p-4">
          <div className="text-matrix-dim text-[10px] uppercase tracking-widest mb-3">Drawdown %</div>
          {drawdownCurve.length < 2 ? (
            <div className="text-matrix-dim text-sm h-48 flex items-center justify-center">Not enough data</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={drawdownCurve}>
                <defs><linearGradient id="gDD" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                </linearGradient></defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                <XAxis dataKey="date" tickFormatter={formatChartDate} tick={{ fill: "#555", fontSize: 10 }} />
                <YAxis tick={{ fill: "#555", fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ background: "#111", border: "1px solid #1a1a1a", fontSize: 11 }}
                  labelFormatter={(label: any) => formatChartDate(String(label))}
                  formatter={(v: any) => [`${Number(v).toFixed(2)}%`, "Drawdown"]}
                />
                <Area type="monotone" dataKey="drawdown" stroke="#ef4444" fill="url(#gDD)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Charts row 2: Daily PnL + Win/Loss by symbol */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily PnL bars */}
        <div className="border border-terminal-border rounded bg-terminal-surface p-4">
          <div className="text-matrix-dim text-[10px] uppercase tracking-widest mb-3">Daily PnL</div>
          {filteredDailyPnl.length === 0 ? (
            <div className="text-matrix-dim text-sm h-48 flex items-center justify-center">No daily data</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={filteredDailyPnl.map((d) => ({ ...d, pnl: Number(d.pnl) }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                <XAxis dataKey="day" tickFormatter={formatChartDate} tick={{ fill: "#555", fontSize: 10 }} />
                <YAxis tick={{ fill: "#555", fontSize: 10 }} />
                <Tooltip
                  contentStyle={{ background: "#111", border: "1px solid #1a1a1a", fontSize: 11 }}
                  formatter={(v: any) => [`${Number(v).toFixed(2)}`, "PnL"]}
                />
                <Bar dataKey="pnl" fill="#00ff41">
                  {filteredDailyPnl.map((d, i) => (
                    <Cell key={i} fill={Number(d.pnl) >= 0 ? "#22c55e" : "#ef4444"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Win/Loss by symbol */}
        <div className="border border-terminal-border rounded bg-terminal-surface p-4">
          <div className="text-matrix-dim text-[10px] uppercase tracking-widest mb-3">Trades by Symbol</div>
          {symbolBars.length === 0 ? (
            <div className="text-matrix-dim text-sm h-48 flex items-center justify-center">No symbol data</div>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={symbolBars} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#1a1a1a" />
                <XAxis type="number" tick={{ fill: "#555", fontSize: 10 }} />
                <YAxis dataKey="symbol" type="category" tick={{ fill: "#aaa", fontSize: 10 }} width={70} />
                <Tooltip contentStyle={{ background: "#111", border: "1px solid #1a1a1a", fontSize: 11 }} />
                <Legend wrapperStyle={{ fontSize: 10 }} />
                <Bar dataKey="wins" stackId="a" fill="#22c55e" name="Wins" />
                <Bar dataKey="losses" stackId="a" fill="#ef4444" name="Losses" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Charts row 3: Symbol PnL pie + Direction pie */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Symbol PnL pie */}
        <div className="border border-terminal-border rounded bg-terminal-surface p-4">
          <div className="text-matrix-dim text-[10px] uppercase tracking-widest mb-3">PnL by Symbol</div>
          {symbolPie.length === 0 ? (
            <div className="text-matrix-dim text-sm h-48 flex items-center justify-center">No data</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={symbolPie} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name }) => name}>
                  {symbolPie.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "#111", border: "1px solid #1a1a1a", fontSize: 11 }}
                  formatter={(v: any, _n: any, entry: any) =>
                    [`${(entry.payload?.pnl ?? 0) >= 0 ? "+" : ""}${Number(entry.payload?.pnl ?? 0).toFixed(2)}`, "PnL"]
                  }
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Direction pie */}
        <div className="border border-terminal-border rounded bg-terminal-surface p-4">
          <div className="text-matrix-dim text-[10px] uppercase tracking-widest mb-3">Buy vs Sell</div>
          {filteredDirStats.length === 0 ? (
            <div className="text-matrix-dim text-sm h-48 flex items-center justify-center">No data</div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie data={filteredDirStats} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, value }) => `${name}: ${value}`}>
                  <Cell fill="#22c55e" />
                  <Cell fill="#ef4444" />
                </Pie>
                <Tooltip contentStyle={{ background: "#111", border: "1px solid #1a1a1a", fontSize: 11 }} />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Symbol ranking table */}
        <div className="border border-terminal-border rounded bg-terminal-surface p-4 overflow-x-auto">
          <div className="text-matrix-dim text-[10px] uppercase tracking-widest mb-3">Symbol Ranking</div>
          {filteredSymbolStats.length === 0 ? (
            <div className="text-matrix-dim text-sm">No data</div>
          ) : (
            <table className="w-full text-[10px]">
              <thead className="text-matrix-dim uppercase border-b border-terminal-border">
                <tr>
                  <th className="text-left p-1">Symbol</th>
                  <th className="text-right p-1">Trades</th>
                  <th className="text-right p-1">Win%</th>
                  <th className="text-right p-1">PnL</th>
                </tr>
              </thead>
              <tbody>
                {filteredSymbolStats.map((s) => {
                  const wr = s.total > 0 ? ((Number(s.wins) / Number(s.total)) * 100).toFixed(0) : "0";
                  const pnl = Number(s.total_pnl);
                  return (
                    <tr key={s.symbol} className="border-b border-terminal-border/30">
                      <td className="p-1 text-matrix font-bold">{s.symbol}</td>
                      <td className="p-1 text-right">{s.total}</td>
                      <td className="p-1 text-right">{wr}%</td>
                      <td className={`p-1 text-right font-bold ${pnl >= 0 ? "text-green-400" : "text-red-500"}`}>
                        {pnl >= 0 ? "+" : ""}{pnl.toFixed(2)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Avg duration KPI */}
      {displayKpis && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <Kpi
            label="Avg Duration"
            value={`${Math.floor(Number(displayKpis.avg_duration_min))}m`}
            sub="minutes per trade"
          />
          <Kpi label="Total Closed" value={String(filteredTrades.length)} />
          <Kpi
            label="Avg Win"
            value={filteredSymbolStats.length > 0 ? `+${(filteredSymbolStats.reduce((s, x) => s + Number(x.avg_win), 0) / filteredSymbolStats.length).toFixed(2)}` : "—"}
            color="text-green-400"
          />
          <Kpi
            label="Avg Loss"
            value={filteredSymbolStats.length > 0 ? (filteredSymbolStats.reduce((s, x) => s + Number(x.avg_loss), 0) / filteredSymbolStats.length).toFixed(2) : "—"}
            color="text-red-500"
          />
        </div>
      )}
    </div>
  );
}
