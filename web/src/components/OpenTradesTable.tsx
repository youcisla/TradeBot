"use client";

import { useEffect, useState } from "react";

interface Trade {
  id: string;
  symbol: string;
  strategy: string;
  direction: string;
  entry_price: number;
  lot_size: number;
  stop_loss: number;
  take_profit_1: number;
  status: string;
  pnl: number;
  open_time: string;
}

export default function OpenTradesTable() {
  const [trades, setTrades] = useState<Trade[]>([]);

  useEffect(() => {
    const load = () =>
      fetch("/api/trades")
        .then((r) => r.json())
        .then(setTrades)
        .catch(() => {});
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  async function closeTrade(tradeId: string) {
    await fetch("/api/commands", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ command: "close_trade", payload: { trade_id: tradeId } }),
    });
  }

  if (trades.length === 0)
    return (
      <div className="border border-terminal-border rounded bg-terminal-surface p-4 text-matrix-dim text-sm">
        No open trades.
      </div>
    );

  return (
    <div className="border border-terminal-border rounded bg-terminal-surface overflow-x-auto">
      <table className="w-full text-xs">
        <thead className="border-b border-terminal-border text-matrix-dim uppercase tracking-wider">
          <tr>
            <th className="text-left p-2">Symbol</th>
            <th className="text-left p-2">Dir</th>
            <th className="text-left p-2">Strategy</th>
            <th className="text-right p-2">Entry</th>
            <th className="text-right p-2">Lots</th>
            <th className="text-right p-2">SL</th>
            <th className="text-right p-2">TP1</th>
            <th className="text-right p-2">PnL</th>
            <th className="text-right p-2">Status</th>
            <th className="p-2"></th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id} className="border-b border-terminal-border/50 hover:bg-terminal-border/30">
              <td className="p-2 text-matrix font-bold">{t.symbol}</td>
              <td className={`p-2 font-bold ${t.direction === "BUY" ? "text-matrix" : "text-red-500"}`}>
                {t.direction}
              </td>
              <td className="p-2 text-matrix-dim">{t.strategy}</td>
              <td className="p-2 text-right">{Number(t.entry_price).toFixed(5)}</td>
              <td className="p-2 text-right">{t.lot_size}</td>
              <td className="p-2 text-right text-red-400">{Number(t.stop_loss).toFixed(5)}</td>
              <td className="p-2 text-right text-matrix-dim">{Number(t.take_profit_1).toFixed(5)}</td>
              <td className={`p-2 text-right font-bold ${Number(t.pnl) >= 0 ? "text-matrix" : "text-red-500"}`}>
                {Number(t.pnl) >= 0 ? "+" : ""}{Number(t.pnl).toFixed(2)}
              </td>
              <td className="p-2 text-right text-yellow-400">{t.status}</td>
              <td className="p-2 text-right">
                <button
                  onClick={() => closeTrade(t.id)}
                  className="px-2 py-0.5 border border-red-500 text-red-500 hover:bg-red-500 hover:text-black rounded text-[10px] uppercase"
                >
                  Close
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
