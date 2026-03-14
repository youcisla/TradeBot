"use client";

import { useEffect, useState } from "react";
import { formatShort } from "@/lib/time";
import SymbolFilter from "@/components/SymbolFilter";

interface Trade {
  id: string;
  symbol: string;
  strategy: string;
  direction: string;
  entry_price: number;
  lot_size: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  take_profit_3: number;
  tp1_hit: boolean;
  tp2_hit: boolean;
  tp3_hit: boolean;
  status: string;
  open_time: string;
  close_time: string | null;
  pnl: number;
  close_reason: string;
}

export default function TradesPage() {
  const [trades, setTrades] = useState<Trade[]>([]);
  const [symbol, setSymbol] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/trades?all=true")
      .then((r) => r.json())
      .then(setTrades)
      .catch(() => {});
  }, []);

  const filtered = symbol ? trades.filter((t) => t.symbol === symbol) : trades;

  return (
    <div className="space-y-4">
      <h1 className="text-matrix text-lg font-bold">All Trades</h1>
      <SymbolFilter value={symbol} onChange={setSymbol} />

      <div className="border border-terminal-border rounded bg-terminal-surface overflow-x-auto">
        <table className="w-full text-xs">
          <thead className="border-b border-terminal-border text-matrix-dim uppercase tracking-wider">
            <tr>
              <th className="text-left p-2">ID</th>
              <th className="text-left p-2">Symbol</th>
              <th className="text-left p-2">Dir</th>
              <th className="text-left p-2">Strategy</th>
              <th className="text-right p-2">Entry</th>
              <th className="text-right p-2">Lots</th>
              <th className="text-right p-2">PnL</th>
              <th className="text-left p-2">Status</th>
              <th className="text-left p-2">Reason</th>
              <th className="text-left p-2">SL</th>
              <th className="text-left p-2">TP1</th>
              <th className="text-left p-2">TP2</th>
              <th className="text-left p-2">TP3</th>
              <th className="text-left p-2">Opened</th>
              <th className="text-left p-2">Closed</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((t) => (
              <tr
                key={t.id}
                className="border-b border-terminal-border/50 hover:bg-terminal-border/30"
              >
                <td className="p-2 text-matrix-dim">{t.id.slice(0, 8)}</td>
                <td className="p-2 text-matrix font-bold">{t.symbol}</td>
                <td
                  className={`p-2 font-bold ${t.direction === "BUY" ? "text-matrix" : "text-red-500"}`}
                >
                  {t.direction}
                </td>
                <td className="p-2 text-matrix-dim">{t.strategy}</td>
                <td className="p-2 text-right">{Number(t.entry_price).toFixed(5)}</td>
                <td className="p-2 text-right">{t.lot_size}</td>
                <td
                  className={`p-2 text-right font-bold ${Number(t.pnl) >= 0 ? "text-matrix" : "text-red-500"}`}
                >
                  {Number(t.pnl) >= 0 ? "+" : ""}
                  {Number(t.pnl).toFixed(2)}
                </td>
                <td className="p-2">
                  <span
                    className={
                      t.status === "CLOSED"
                        ? "text-gray-500"
                        : t.status === "OPEN"
                          ? "text-matrix"
                          : "text-yellow-400"
                    }
                  >
                    {t.status}
                  </span>
                </td>
                <td className="p-2 text-matrix-dim">{t.close_reason || "—"}</td>
                <td className="p-2">{typeof t.stop_loss === "number" ? t.stop_loss.toFixed(5) : "—"}</td>
                <td className="p-2">{typeof t.take_profit_1 === "number" ? t.take_profit_1.toFixed(5) : "—"}</td>
                <td className="p-2">{typeof t.take_profit_2 === "number" ? t.take_profit_2.toFixed(5) : "—"}</td>
                <td className="p-2">{typeof t.take_profit_3 === "number" ? t.take_profit_3.toFixed(5) : "—"}</td>
                <td className="p-2 text-matrix-dim">{formatShort(t.open_time)}</td>
                <td className="p-2 text-matrix-dim">{t.close_time ? formatShort(t.close_time) : "—"}</td>
                <td className="p-2">
                  <a
                    href={`https://www.tradingview.com/chart/?symbol=${encodeURIComponent(t.symbol)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-matrix underline hover:text-matrix-dim"
                  >
                    Chart
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {filtered.length === 0 && (
        <div className="text-matrix-dim text-sm">{symbol ? `No trades for ${symbol}.` : "No trades recorded yet."}</div>
      )}
    </div>
  );
}
