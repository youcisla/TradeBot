"use client";

import { useEffect, useState } from "react";
import { formatShort } from "@/lib/time";
import SymbolFilter from "@/components/SymbolFilter";

interface StrategyConfidence {
  strategy: string;
  confidence: number;
  total_trades: number;
  total_score: number;
  last_updated: string;
}

interface TradeScore {
  id: number;
  trade_id: string;
  strategy: string;
  symbol: string;
  session: string;
  market_condition: string;
  score: number;
  pnl: number;
  created_at: string;
}

export default function LearningPage() {
  const [confidences, setConfidences] = useState<StrategyConfidence[]>([]);
  const [scores, setScores] = useState<TradeScore[]>([]);
  const [symbol, setSymbol] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/learning")
      .then((r) => r.json())
      .then((data) => {
        setConfidences(data.confidences ?? []);
        setScores(data.scores ?? []);
      })
      .catch(() => {});
  }, []);

  const filtered = symbol ? scores.filter((s) => s.symbol === symbol) : scores;

  return (
    <div className="space-y-6">
      <h1 className="text-matrix text-lg font-bold">Learning System</h1>
      <SymbolFilter value={symbol} onChange={setSymbol} />

      {/* Strategy Confidence */}
      <div className="border border-terminal-border rounded bg-terminal-surface p-4">
        <div className="text-matrix-dim text-xs uppercase tracking-widest mb-3">
          Strategy Confidence
        </div>
        {confidences.length === 0 ? (
          <div className="text-matrix-dim text-sm">No strategies tracked yet.</div>
        ) : (
          <div className="space-y-3">
            {confidences.map((c) => (
              <div key={c.strategy} className="flex items-center gap-4">
                <span className="text-matrix font-bold w-40 text-sm">
                  {c.strategy}
                </span>
                <div className="flex-1 h-3 bg-terminal rounded overflow-hidden border border-terminal-border">
                  <div
                    className="h-full bg-matrix transition-all"
                    style={{ width: `${Math.max(0, Math.min(100, Number(c.confidence) * 100))}%` }}
                  />
                </div>
                <span className="text-matrix text-sm w-16 text-right font-bold">
                  {(Number(c.confidence) * 100).toFixed(0)}%
                </span>
                <span className="text-matrix-dim text-xs w-24 text-right">
                  {c.total_trades} trades
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Scores */}
      <div className="border border-terminal-border rounded bg-terminal-surface overflow-x-auto">
        <div className="px-4 pt-3 text-matrix-dim text-xs uppercase tracking-widest">
          Recent Scores
        </div>
        <table className="w-full text-xs mt-2">
          <thead className="border-b border-terminal-border text-matrix-dim uppercase tracking-wider">
            <tr>
              <th className="text-left p-2">Trade</th>
              <th className="text-left p-2">Strategy</th>
              <th className="text-left p-2">Symbol</th>
              <th className="text-left p-2">Session</th>
              <th className="text-left p-2">Condition</th>
              <th className="text-right p-2">Score</th>
              <th className="text-right p-2">PnL</th>
              <th className="text-left p-2">Time</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((s) => (
              <tr
                key={s.id}
                className="border-b border-terminal-border/50 hover:bg-terminal-border/30"
              >
                <td className="p-2 text-matrix-dim">{s.trade_id.slice(0, 8)}</td>
                <td className="p-2 text-matrix">{s.strategy}</td>
                <td className="p-2">{s.symbol}</td>
                <td className="p-2 text-matrix-dim">{s.session || "—"}</td>
                <td className="p-2 text-matrix-dim">{s.market_condition || "—"}</td>
                <td
                  className={`p-2 text-right font-bold ${Number(s.score) >= 0 ? "text-matrix" : "text-red-500"}`}
                >
                  {Number(s.score) >= 0 ? "+" : ""}
                  {s.score}
                </td>
                <td
                  className={`p-2 text-right ${Number(s.pnl) >= 0 ? "text-matrix" : "text-red-500"}`}
                >
                  {Number(s.pnl) >= 0 ? "+" : ""}
                  {Number(s.pnl).toFixed(2)}
                </td>
                <td className="p-2 text-matrix-dim">
                  {formatShort(s.created_at)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="p-4 text-matrix-dim text-sm">{symbol ? `No scores for ${symbol}.` : "No scores recorded yet."}</div>
        )}
      </div>
    </div>
  );
}
