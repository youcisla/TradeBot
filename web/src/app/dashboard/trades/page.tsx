"use client";

import { useEffect, useState, useMemo } from "react";
import { formatShort } from "@/lib/time";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Trade {
  id: string; symbol: string; strategy: string; direction: string;
  entry_price: number; lot_size: number; stop_loss: number;
  take_profit_1: number; take_profit_2: number; take_profit_3: number;
  tp1_hit: boolean; tp2_hit: boolean; tp3_hit: boolean;
  status: string; open_time: string; close_time: string | null;
  pnl: number; close_reason: string;
}

interface BotStatus {
  daily_pnl: number; balance: number; equity: number;
}

// ── Emergency Close ────────────────────────────────────────────────────────────

async function emergencyCloseAll() {
  await fetch("/api/commands", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ command: "kill" }),
  });
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function LiveMonitoringPage() {
  const [trades, setTrades]   = useState<Trade[]>([]);
  const [status, setStatus]   = useState<BotStatus | null>(null);
  const [closing, setClosing] = useState(false);

  useEffect(() => {
    let active = true;
    const load = () => {
      Promise.allSettled([
        fetch("/api/trades?all=true").then((r) => r.json()),
        fetch("/api/status").then((r) => r.json()),
      ]).then(([t, s]) => {
        if (!active) return;
        if (t.status === "fulfilled") setTrades(Array.isArray(t.value) ? t.value : []);
        if (s.status === "fulfilled") setStatus(s.value);
      });
    };
    load();
    const id = setInterval(load, 5_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  const openTrades   = useMemo(() => trades.filter((t) => t.status === "OPEN"),   [trades]);
  const closedTrades = useMemo(() => trades.filter((t) => t.status === "CLOSED"), [trades]);
  const wins         = useMemo(() => closedTrades.filter((t) => Number(t.pnl) > 0), [closedTrades]);
  const winRate      = closedTrades.length > 0 ? Math.round((wins.length / closedTrades.length) * 100) : 0;

  const dailyPnl     = Number(status?.daily_pnl ?? 0);
  const balance      = Number(status?.balance ?? 0);
  const drawdownPct  = balance > 0 ? Math.abs(Math.min(0, dailyPnl) / balance) * 100 : 0;
  const circuitBreak = drawdownPct >= 5;

  return (
    <div className="flex flex-col gap-6 mt-6">

      {/* ── Page Header ── */}
      <div className="border-l-2 border-primary-container pl-4 py-2">
        <span className="text-on-surface-variant text-[10px] tracking-widest uppercase font-bold">TRADES</span>
        <div className="flex flex-col md:flex-row md:items-baseline md:justify-between gap-2">
          <h1 className="text-3xl font-extrabold uppercase tracking-tighter text-on-surface">
            Live Monitoring
          </h1>
          <div className="flex items-center gap-2 text-secondary-fixed">
            <span className="material-symbols-outlined text-sm" style={{ fontSize: 16, fontVariationSettings: "'FILL' 1" }}>
              analytics
            </span>
            <span className="text-xl font-bold">
              {openTrades.length} OPEN · {trades.length} TOTAL
            </span>
          </div>
        </div>
      </div>

      {/* ── Asymmetric Bento Grid ── */}
      <div className="grid grid-cols-1 md:grid-cols-12 gap-1 auto-rows-min">

        {/* Chart placeholder ─ 8/12 col */}
        <div className="md:col-span-8 md:row-span-2 bg-surface p-4 relative overflow-hidden min-h-[360px]">
          <div className="flex justify-between items-center mb-4">
            <div className="flex gap-4 items-center">
              <span className="text-xs text-primary-fixed border border-primary-fixed/20 px-2 py-0.5">H1</span>
              <span className="text-xs text-on-surface-variant">CANDLESTICK</span>
            </div>
            <div className="text-[10px] text-outline uppercase tracking-widest">Neural Link: ACTIVE</div>
          </div>
          {/* Decorative chart grid */}
          <div className="w-full h-[280px] relative border border-outline-variant/10">
            <div className="absolute inset-0 flex flex-col justify-between py-3 px-2 pointer-events-none">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-px w-full bg-outline-variant/10" />
              ))}
            </div>
            <div className="absolute inset-0 flex items-end gap-1 px-3 pb-3">
              {[40,60,45,70,55,80,65,75,50,85,60,90,70,65,80].map((h, i) => (
                <div key={i} className="flex-1 flex flex-col justify-end">
                  <div
                    className="w-full"
                    style={{
                      height: `${h}%`,
                      background: i % 3 === 0 ? "rgba(255,113,108,0.4)" : "rgba(0,253,135,0.4)",
                      borderTop: `1px solid ${i % 3 === 0 ? "#ff716c" : "#00fd87"}`,
                    }}
                  />
                </div>
              ))}
            </div>
            <div className="absolute inset-0 bg-gradient-to-t from-surface to-transparent pointer-events-none" />
            <div className="absolute bottom-4 left-4">
              <span className="text-[10px] text-on-surface-variant">CHART · Open chart page for full detail</span>
            </div>
          </div>
        </div>

        {/* Live Positions ─ 4/12 col */}
        <div className="md:col-span-4 bg-surface-container-high p-4 border-l border-primary-container">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-sm font-bold uppercase tracking-widest text-on-surface">Live Positions</h3>
            <span className="bg-primary-container/10 text-primary-container px-2 py-0.5 text-[10px] animate-pulse">
              LIVE
            </span>
          </div>

          <div className="space-y-3 max-h-[240px] overflow-y-auto">
            {openTrades.length === 0 ? (
              <div className="text-[11px] text-on-surface-variant py-4 text-center">
                NO OPEN POSITIONS
              </div>
            ) : (
              openTrades.map((t) => {
                const pnl = Number(t.pnl);
                return (
                  <div key={t.id} className={`bg-surface p-3 border-l-2 ${t.direction === "BUY" ? "border-primary-container" : "border-error"}`}>
                    <div className="flex justify-between mb-1">
                      <span className="font-bold text-on-surface text-sm">{t.symbol}</span>
                      <span className={`font-bold text-sm uppercase ${t.direction === "BUY" ? "text-primary-container" : "text-error"}`}>
                        {t.direction}
                      </span>
                    </div>
                    <div className="flex justify-between text-[10px] text-on-surface-variant mb-2">
                      <span>Lots: {t.lot_size}</span>
                      <span className={`font-mono ${pnl >= 0 ? "text-primary-container" : "text-error"}`}>
                        PnL: {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
                      </span>
                    </div>
                    {t.tp1_hit && (
                      <div className="flex items-center gap-2 bg-surface-container-lowest p-1.5">
                        <span className="material-symbols-outlined text-secondary" style={{ fontSize: 12 }}>lock</span>
                        <span className="text-[10px] uppercase text-secondary font-bold">SL @ Breakeven</span>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>

          <div className="mt-4">
            <button
              onClick={async () => { setClosing(true); await emergencyCloseAll(); setClosing(false); }}
              disabled={closing || openTrades.length === 0}
              className="w-full py-2.5 bg-error-container text-on-error-container font-bold uppercase text-[10px] tracking-widest hover:bg-error-dim duration-0 disabled:opacity-40"
            >
              {closing ? "Closing..." : "Emergency Close All"}
            </button>
          </div>
        </div>

        {/* Risk Protocol ─ 4/12 col */}
        <div className="md:col-span-4 bg-surface p-4">
          <h3 className="text-sm font-bold uppercase tracking-widest text-on-surface mb-5">Risk Protocol</h3>
          <div className="space-y-5">
            <div>
              <div className="flex justify-between text-[10px] mb-2 uppercase tracking-tight">
                <span className="text-on-surface-variant">Daily Drawdown</span>
                <span className="text-on-surface">
                  {drawdownPct.toFixed(1)}% <span className="text-outline">/ 5.0%</span>
                </span>
              </div>
              <div className="h-1 bg-surface-container-highest w-full overflow-hidden">
                <div
                  className="h-full transition-all duration-500"
                  style={{
                    width: `${Math.min(100, drawdownPct * 20)}%`,
                    background: drawdownPct > 3.5 ? "#ff716c" : "#1cd5ff",
                  }}
                />
              </div>
            </div>
            <div className="flex items-center justify-between p-3 bg-surface-container-low border border-outline-variant/15">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-primary-container" style={{ fontSize: 18 }}>
                  verified_user
                </span>
                <span className="text-[11px] uppercase font-bold text-on-surface">Circuit Breaker</span>
              </div>
              <span className={`text-[10px] font-bold uppercase ${circuitBreak ? "text-error" : "text-primary-container"}`}>
                {circuitBreak ? "🚨 ACTIVE" : "Idle ✅"}
              </span>
            </div>
          </div>
        </div>

        {/* Session Ledger ─ full width */}
        <div className="md:col-span-12 bg-surface p-4">
          <div className="flex justify-between items-center mb-5">
            <h3 className="text-sm font-bold uppercase tracking-widest text-on-surface">Session Ledger</h3>
            <div className="text-right">
              <span className="text-[10px] text-outline uppercase block">Win Rate</span>
              <span className="text-xl font-bold text-primary-fixed">{winRate}%</span>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-[10px] text-outline uppercase tracking-widest">
                  {["ID", "Asset", "Dir", "Strategy", "Lots", "Result", "PnL", "Close", "Reason"].map((h) => (
                    <th key={h} className="pb-3 font-normal whitespace-nowrap pr-4">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="text-xs">
                {trades.slice(0, 30).map((t, i) => {
                  const pnl = Number(t.pnl);
                  const win = pnl > 0;
                  return (
                    <tr
                      key={t.id}
                      className={`hover:bg-surface-bright border-b border-outline-variant/5 duration-0 ${i % 2 === 1 ? "bg-surface-container-low" : ""}`}
                    >
                      <td className="py-3 pr-4 text-on-surface-variant font-mono text-[10px]">
                        #{t.id.slice(0, 6)}
                      </td>
                      <td className="py-3 pr-4 font-bold text-on-surface">{t.symbol}</td>
                      <td className="py-3 pr-4">
                        <span className={`font-bold ${t.direction === "BUY" ? "text-primary-container" : "text-error"}`}>
                          {t.direction}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-on-surface-variant text-[10px]">{t.strategy}</td>
                      <td className="py-3 pr-4 text-on-surface-variant">{t.lot_size}</td>
                      <td className="py-3 pr-4">
                        {t.status === "OPEN" ? (
                          <span className="bg-secondary/10 text-secondary px-2 py-0.5 text-[10px] animate-pulse">OPEN</span>
                        ) : win ? (
                          <span className="bg-primary-container/10 text-primary-container px-2 py-0.5 text-[10px]">W</span>
                        ) : (
                          <span className="bg-error-container/10 text-error-container px-2 py-0.5 text-[10px]">L</span>
                        )}
                      </td>
                      <td className={`py-3 pr-4 font-bold ${pnl >= 0 ? "text-primary-container" : "text-error"}`}>
                        {pnl >= 0 ? "+" : ""}${pnl.toFixed(2)}
                      </td>
                      <td className="py-3 pr-4 text-on-surface-variant text-[10px] whitespace-nowrap">
                        {t.close_time ? formatShort(t.close_time) : "—"}
                      </td>
                      <td className="py-3 text-on-surface-variant text-[10px]">
                        {t.close_reason || "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {trades.length === 0 && (
              <div className="text-center py-12 text-on-surface-variant text-[11px] uppercase tracking-widest">
                NO TRADES RECORDED
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
