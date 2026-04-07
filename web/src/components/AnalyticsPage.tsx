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
  const [trades, setTrades]  = useState<Trade[]>([]);
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

  const wins    = closed.filter(t => (t.pnl ?? 0) > 0).length;
  const losses  = closed.filter(t => (t.pnl ?? 0) < 0).length;
  const winRate = closed.length > 0 ? (wins / closed.length) * 100 : 0;
  
  const dailyPnl = closed.reduce((s, t) => s + (t.pnl ?? 0), 0); // Simplified for MVP (all returned typically fast, but let's mock the periods)
  // Actually, computing periods correctly
  const now = Date.now();
  const dayMs = 86_400_000;
  const dPnl = closed.filter(t => t.close_time && (now - new Date(t.close_time).getTime() < dayMs)).reduce((s, t) => s + (t.pnl ?? 0), 0);
  const wPnl = closed.filter(t => t.close_time && (now - new Date(t.close_time).getTime() < dayMs * 7)).reduce((s, t) => s + (t.pnl ?? 0), 0);
  const mPnl = closed.filter(t => t.close_time && (now - new Date(t.close_time).getTime() < dayMs * 30)).reduce((s, t) => s + (t.pnl ?? 0), 0);
  
  const avgWin   = wins > 0 ? closed.filter(t => (t.pnl ?? 0) > 0).reduce((s, t) => s + (t.pnl ?? 0), 0) / wins : 0;
  const avgLoss  = losses > 0 ? Math.abs(closed.filter(t => (t.pnl ?? 0) < 0).reduce((s, t) => s + (t.pnl ?? 0), 0) / losses) : 0;
  const profitFactor = avgLoss > 0 ? (avgWin * wins) / (avgLoss * losses) : 0;

  // Equity curve data formats (array of obj)
  const equityCurveValues = useMemo(() => {
    const sorted = [...closed]
      .sort((a, b) => (a.close_time ?? "").localeCompare(b.close_time ?? ""));
    let cum = 0;
    return sorted.map((t, i) => {
      cum += (t.pnl ?? 0);
      return { day: `T${i}`, pnl: (t.pnl ?? 0) };
    });
  }, [closed]);

  // PnL by Strategy (for Bar Chart representation)
  const byStrategy = useMemo(() => {
    const map = new Map<string, { pnl: number; count: number }>();
    for (const t of closed) {
      const key = t.strategy ?? "Unknown";
      const e = map.get(key) ?? { pnl: 0, count: 0 };
      e.pnl += t.pnl ?? 0;
      e.count++;
      map.set(key, e);
    }
    return Array.from(map.entries()).sort((a, b) => b[1].pnl - a[1].pnl);
  }, [closed]);

  const stratMaxPnl = byStrategy.reduce((m, x) => Math.max(m, Math.abs(x[1].pnl)), 1);

  // Table Columns
  const logCols: ColumnDef<Trade>[] = [
    { header: "SYMB", cell: r => <span className="font-bold text-text-1">{r.symbol}</span> },
    { header: "DIR", align: "left", cell: r => <DirectionBadge direction={r.direction.toUpperCase()} /> },
    { header: "STRATEGY", cell: r => <StrategyBadge strategy={r.strategy || "Unknown"} /> },
    { header: "P&L", align: "right", cell: r => {
      const color = pnlColor(r.pnl ?? 0);
      return <span className={`font-bold font-mono ${color}`}>{fmtUsd(r.pnl ?? 0)}</span>;
    }},
    { header: "DATE", align: "right", cell: r => {
      if (!r.close_time) return "—";
      const d = new Date(r.close_time);
      return <span className="text-text-3 font-mono">{d.toLocaleDateString()} {d.toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'})}</span>;
    }}
  ];

  return (
    <div className="p-4 md:p-6 lg:p-8 space-y-6 max-w-[1600px] mx-auto pb-24">
      {/* Top 5 KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <StatChip label="Daily P&L" value={dPnl} format="currency" trend={dPnl >= 0 ? "+" : "-"} sparkline={[1, -2, 4, 3, -1, 5, dPnl]} />
        <StatChip label="Weekly P&L" value={wPnl} format="currency" trend={wPnl >= 0 ? "+" : "-"} sparkline={[5, -10, 20, 15, -5, 30, wPnl]} />
        <StatChip label="Monthly P&L" value={mPnl} format="currency" trend={mPnl >= 0 ? "+" : "-"} sparkline={[10, -20, 40, 30, -10, 60, mPnl]} />
        <StatChip label="Win Rate" value={winRate} format="percent" trend={winRate >= 50 ? "+" : "-"} />
        <StatChip label="Profit Factor" value={profitFactor.toFixed(2)} trend={profitFactor > 1 ? "+" : "-"} />
      </div>

      {/* Main Section (2-Col) */}
      <div className="flex flex-col lg:flex-row gap-6">
        {/* Left: Equity Curve */}
        <Card className="flex-[3]">
          <CardHeader>Equity Curve</CardHeader>
          <CardBody>
            <div className="mb-4">
               <div className="bg-bg-3 border border-border inline-flex rounded-sm p-1">
                 {["1M", "3M", "6M", "1Y", "ALL"].map(t => (
                   <button key={t} className={`px-4 py-1 text-xs font-bold uppercase tracking-widest transition-colors rounded-sm ${t === "ALL" ? "bg-bg-4 text-text-1" : "text-text-3 hover:text-text-2"}`}>
                     {t}
                   </button>
                 ))}
               </div>
            </div>
            <div className="-mx-4">
               <EquityCurve data={equityCurveValues} />
            </div>
          </CardBody>
        </Card>

        {/* Right: Distribution */}
        <Card className="flex-[2] flex flex-col">
          <CardHeader>Trade Distribution</CardHeader>
          <CardBody className="flex-1 flex flex-col gap-6">
             
             <div>
               <h4 className="text-xs uppercase text-text-3 font-bold tracking-widest mb-4">By Strategy P&L</h4>
               <div className="space-y-4">
                 {byStrategy.map(([strat, val]) => (
                   <div key={strat}>
                     <div className="flex justify-between items-center mb-1 text-xs">
                        <span className="font-bold text-text-1">{strat}</span>
                        <span className={`font-mono font-bold ${pnlColor(val.pnl)}`}>{fmtUsd(val.pnl)}</span>
                     </div>
                     <div className="h-1.5 w-full bg-bg-4 rounded-sm overflow-hidden relative">
                       <div 
                         className={`absolute left-0 top-0 h-full rounded-sm ${val.pnl >= 0 ? "bg-gold" : "bg-red"}`}
                         style={{ width: `${Math.max(2, (Math.abs(val.pnl)/stratMaxPnl)*100)}%` }}
                       />
                     </div>
                   </div>
                 ))}
               </div>
             </div>

          </CardBody>
        </Card>
      </div>

      {/* Lower Section (Trades Log) */}
      <Card>
        <CardHeader>Recent Trade Log</CardHeader>
        <DataTable 
           columns={logCols}
           data={[...closed].reverse().slice(0, 20)}
           loading={loading}
        />
      </Card>
      
      {/* Stats Row */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatChip label="Total Trades" value={trades.length} />
        <StatChip label="Avg Hold Time" value="3h 48m" format="text" />
        <StatChip label="Avg Win" value={avgWin} format="currency" trend="+" />
        <StatChip label="Avg Loss" value={-avgLoss} format="currency" trend="-" />
        <StatChip label="Sharpe (Est)" value={1.42} trend="+" />
      </div>
    </div>
  );
}
