"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { DataTable, ColumnDef } from "@/components/ui/DataTable";
import { StatChip } from "@/components/ui/StatChip";
import { Card, CardBody } from "@/components/ui/Card";
import { DirectionBadge, StrategyBadge } from "@/components/ui/Badges";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Trade {
  id: number;
  symbol: string;
  strategy?: string;
  direction: string;
  entry_price: number;
  lot_size?: number;
  stop_loss?: number;
  take_profit_1?: number;
  take_profit_2?: number;
  take_profit_3?: number;
  take_profit_4?: number;
  tp1_lots?: number;
  tp2_lots?: number;
  tp3_lots?: number;
  tp4_lots?: number;
  tp1_hit?: boolean;
  tp2_hit?: boolean;
  tp3_hit?: boolean;
  tp4_hit?: boolean;
  status: string;
  open_time?: string;
  close_time?: string;
  pnl?: number;
  close_reason?: string;
  commission?: number;
  current_price?: number;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtUsd(v: number | undefined): string {
  const n = Number(v ?? 0);
  const f = Math.abs(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (n < 0 ? "-$" : "$") + f;
}

function fmtPrice(v: number | undefined): string {
  const n = Number(v ?? 0);
  if (!n && n !== 0) return "—";
  return n >= 100 ? n.toFixed(2) : n >= 1 ? n.toFixed(4) : n.toFixed(5);
}

function fmtDate(ts: string | undefined): string {
  if (!ts) return "—";
  const d = new Date(ts);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
    + " " + d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}

function relAge(ts: string | undefined, closed_ts?: string): string {
  if (!ts) return "—";
  const ms = (closed_ts ? new Date(closed_ts).getTime() : Date.now()) - new Date(ts).getTime();
  if (ms < 3_600_000)  return Math.floor(ms / 60_000)    + "m";
  if (ms < 86_400_000) return Math.floor(ms / 3_600_000) + "h";
  return                      Math.floor(ms / 86_400_000) + "d";
}

// ── Drawer Component ────────────────────────────────────────────────────────

function TradeDrawer({ trade, onClose }: { trade: Trade; onClose: () => void }) {
  const isLong = /buy|long/i.test(trade.direction);

  return (
    <div 
      className="fixed inset-0 z-[200] flex justify-end bg-black/60 animate-in fade-in"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="w-[520px] max-w-[95vw] h-full bg-bg-2 border-l border-border overflow-y-auto animate-in slide-in-from-right flex flex-col font-ui">
        {/* Header */}
        <div className="p-6 border-b border-border shrink-0 space-y-4">
          <div className="flex justify-between items-start">
            <div className="flex items-center gap-3">
              <span className="text-2xl font-bold text-text-1 font-mono">{trade.symbol}</span>
              <DirectionBadge direction={isLong ? "LONG" : "SHORT"} />
              <div className={`px-2 py-1 rounded-sm text-xs font-bold uppercase tracking-wider ${trade.status === 'OPEN' ? 'bg-cyan-dim text-cyan' : 'bg-bg-3 text-text-3'}`}>
                {trade.status}
              </div>
            </div>
            <button onClick={onClose} className="w-8 h-8 rounded-sm bg-bg-3 border border-border text-text-2 hover:text-text-1 flex items-center justify-center text-xl transition-colors">
              &times;
            </button>
          </div>

          <div className="flex gap-6">
            <div className="flex flex-col">
              <span className="text-[10px] text-text-3 uppercase tracking-wider mb-1">Unrealized P&L</span>
              <span className={`text-xl font-mono font-bold ${trade.pnl && trade.pnl > 0 ? "text-gold" : trade.pnl && trade.pnl < 0 ? "text-red" : "text-text-3"}`}>
                 {trade.pnl ? fmtUsd(trade.pnl) : "—"}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-text-3 uppercase tracking-wider mb-1">Entry</span>
              <span className="text-xl font-mono text-text-1">{fmtPrice(trade.entry_price)}</span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] text-text-3 uppercase tracking-wider mb-1">Current</span>
              <span className="text-xl font-mono text-text-1">{trade.current_price ? fmtPrice(trade.current_price) : "—"}</span>
            </div>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 flex-1 flex flex-col gap-8">
          
          {/* Section: Entry Levels */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-text-3 uppercase tracking-widest">Pricing Levels</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {[
                { label: "Entry",   value: trade.entry_price,    color: "text-text-1" },
                { label: "SL",       value: trade.stop_loss,     color: "text-red" },
                { label: "TP1",      value: trade.take_profit_1,  color: "text-gold" },
                { label: "TP2",      value: trade.take_profit_2,  color: "text-gold" },
              ].map(({ label, value, color }) => (
                <div key={label} className="bg-bg-3 rounded-sm p-3 text-center border border-border/50">
                  <div className="text-[10px] text-text-3 tracking-widest uppercase mb-1">{label}</div>
                  <div className={`text-sm font-mono font-bold ${value ? color : 'text-text-3'}`}>
                    {value ? fmtPrice(value) : "—"}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Timing & Metadata */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-text-3 uppercase tracking-widest">Timing & Metadata</h4>
            <div className="flex gap-8 flex-wrap">
              <div className="space-y-1">
                <div className="text-[10px] text-text-3 uppercase tracking-widest">Opened</div>
                <div className="text-xs font-mono text-text-1">{fmtDate(trade.open_time)}</div>
              </div>
              <div className="space-y-1">
                <div className="text-[10px] text-text-3 uppercase tracking-widest">Closed</div>
                <div className="text-xs font-mono text-text-1">{fmtDate(trade.close_time) || "—"}</div>
              </div>
              <div className="space-y-1">
                <div className="text-[10px] text-text-3 uppercase tracking-widest">Duration</div>
                <div className="text-xs font-mono text-text-2">{relAge(trade.open_time, trade.close_time)}</div>
              </div>
              <div className="space-y-1">
                <div className="text-[10px] text-text-3 uppercase tracking-widest">Lots</div>
                <div className="text-xs font-mono text-text-2">{trade.lot_size ?? "—"}</div>
              </div>
              <div className="space-y-1">
                <div className="text-[10px] text-text-3 uppercase tracking-widest">Close Reason</div>
                <div className="text-xs font-mono text-text-2">{trade.close_reason || "—"}</div>
              </div>
            </div>
          </div>

          {/* Outcome */}
          {(trade.status === "CLOSED" || trade.close_reason) && (
            <div className="space-y-3 mt-auto">
              <h4 className="text-xs font-bold text-text-3 uppercase tracking-widest">Outcome</h4>
              <div className={`rounded-sm p-4 border ${trade.pnl && trade.pnl > 0 ? "bg-gold-dim border-gold text-gold" : "bg-red-dim border-red text-red"}`}>
                 <div className="text-[10px] uppercase tracking-widest font-bold mb-1 opacity-80">
                   {trade.close_reason || "Closed"}
                 </div>
                 <div className="text-3xl font-mono font-bold tracking-tight">
                   {fmtUsd(trade.pnl)}
                 </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [search, setSearch] = useState("");
  const [statusFlt, setStatusFlt] = useState<"ALL" | "OPEN" | "CLOSED">("OPEN");
  
  const [page, setPage] = useState(0);
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const PAGE_SIZE = 25;

  const loadTrades = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch("/api/trades?all=true&limit=500");
      const d = await r.json();
      setTrades(Array.isArray(d) ? d : (d.trades ?? []));
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { loadTrades(); }, [loadTrades]);
  useEffect(() => { setPage(0); }, [statusFlt, search]); // reset page on filter change

  // Derived visible set
  const filtered = useMemo(() => {
    return [...trades]
      .filter(t => statusFlt === "ALL" || (statusFlt === "OPEN" ? t.status !== "CLOSED" : t.status === "CLOSED"))
      .filter(t => !search || t.symbol?.toLowerCase().includes(search.toLowerCase()))
      .sort((a, b) => {
        const ta = b.close_time ?? b.open_time ?? "";
        const tb = a.close_time ?? a.open_time ?? "";
        return tb.localeCompare(ta);
      });
  }, [trades, statusFlt, search]);

  const pageCount = Math.ceil(filtered.length / PAGE_SIZE);
  const pageSlice = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  // Stats computation based on visible "CLOSED" trades
  const closedFiltered = filtered.filter(t => t.status === "CLOSED");
  const wins = closedFiltered.filter(t => (t.pnl ?? 0) > 0);
  const losses = closedFiltered.filter(t => (t.pnl ?? 0) <= 0);
  
  const winRate = closedFiltered.length > 0 ? (wins.length / closedFiltered.length) * 100 : 0;
  const avgWin = wins.length > 0 ? wins.reduce((s, t) => s + (t.pnl ?? 0), 0) / wins.length : 0;
  const avgLoss = losses.length > 0 ? losses.reduce((s, t) => s + (t.pnl ?? 0), 0) / losses.length : 0;

  // Columns definition
  const columns: ColumnDef<Trade>[] = [
    { header: "SYMB", align: "left", cell: row => <span className="font-bold text-text-1">{row.symbol}</span> },
    { header: "DIR", align: "left", cell: row => <DirectionBadge direction={row.direction.toUpperCase()} /> },
    { header: "ENTRY", align: "right", cell: row => fmtPrice(row.entry_price) },
    { header: "P&L", align: "right", cell: row => {
       if (row.status !== "CLOSED") return <span className="text-text-3">—</span>;
       const pnl = Number(row.pnl ?? 0);
       const color = pnl > 0 ? "text-gold" : pnl < 0 ? "text-red" : "text-text-3";
       return <span className={`font-bold ${color}`}>{pnl > 0 ? "+" : ""}{fmtUsd(pnl)}</span>
    }},
    { header: "DURATION", align: "right", cell: row => relAge(row.open_time, row.close_time) },
    { header: "STRATEGY", align: "center", cell: row => row.strategy ? <StrategyBadge strategy={row.strategy} /> : <span className="text-text-3">—</span> },
    { header: "STATUS", align: "left", cell: row => {
       if (row.status !== "CLOSED") return <span className="text-cyan text-xs font-bold uppercase">OPEN</span>;
       return <span className="text-text-3 text-xs uppercase">{row.close_reason || "CLOSED"}</span>
    }}
  ];

  return (
    <div className="p-4 md:p-6 lg:p-8 space-y-6 max-w-[1400px] mx-auto pb-24">
      
      {/* Top Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatChip label="Total Visible" value={filtered.length} format="number" />
        <StatChip label="Win Rate" value={winRate} format="percent" trend={winRate >= 50 ? "+" : "-"} />
        <StatChip label="Avg Win" value={avgWin} format="currency" trend="+" />
        <StatChip label="Avg Loss" value={avgLoss} format="currency" trend="-" />
      </div>

      {/* Toolbar */}
      <Card className="flex flex-col md:flex-row gap-4 justify-between items-center bg-bg-2 p-3">
        <div className="flex items-center gap-4 w-full md:w-auto">
          {/* Status Toggle */}
          <div className="flex bg-bg-3 rounded-sm p-1 border border-border">
            {(["OPEN", "CLOSED", "ALL"] as const).map(t => (
              <button 
                key={t}
                onClick={() => setStatusFlt(t)}
                className={`px-4 py-1.5 text-xs font-ui font-bold uppercase tracking-wider rounded-sm transition-colors ${statusFlt === t ? 'bg-bg-4 text-text-1' : 'text-text-3 hover:text-text-2'}`}
              >
                {t}
              </button>
            ))}
          </div>

          <div className="relative flex-1 md:w-48">
            <input 
              type="text" 
              placeholder="Search symbol..." 
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-bg-3 border border-border rounded-sm py-1.5 px-3 text-sm font-ui text-text-1 outline-none focus:border-text-3 transition-colors"
            />
          </div>
        </div>

        <button 
          onClick={loadTrades}
          className="flex items-center gap-2 px-3 py-1.5 text-text-3 hover:text-text-1 hover:bg-bg-3 rounded-sm transition-colors uppercase font-ui text-xs tracking-wider"
        >
          <span className="material-symbols-outlined text-[16px]">refresh</span>
          Refresh
        </button>
      </Card>

      {/* Main Table View */}
      <Card>
        <DataTable 
          data={pageSlice} 
          columns={columns} 
          loading={loading} 
          onRowClick={(row) => setSelectedTrade(row)}
        />
        
        {/* Pagination Strip */}
        {pageCount > 1 && (
          <div className="flex items-center justify-between p-4 bg-bg-2 border-t border-border">
            <span className="text-xs text-text-3 font-mono">
               Showing {page * PAGE_SIZE + 1} to {Math.min((page + 1) * PAGE_SIZE, filtered.length)} of {filtered.length}
            </span>
            <div className="flex gap-2">
              <button 
                disabled={page === 0} 
                onClick={() => setPage(p => Math.max(0, p - 1))}
                className="px-3 py-1 bg-bg-3 border border-border rounded-sm text-sm disabled:opacity-50 hover:bg-bg-4 transition-colors"
              >
                Prev
              </button>
              <button 
                disabled={page >= pageCount - 1} 
                onClick={() => setPage(p => Math.min(pageCount - 1, p + 1))}
                className="px-3 py-1 bg-bg-3 border border-border rounded-sm text-sm disabled:opacity-50 hover:bg-bg-4 transition-colors"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </Card>

      {/* Drawer */}
      {selectedTrade && (
        <TradeDrawer trade={selectedTrade} onClose={() => setSelectedTrade(null)} />
      )}
    </div>
  );
}
