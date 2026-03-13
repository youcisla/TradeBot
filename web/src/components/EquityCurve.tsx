"use client";

import { useEffect, useState } from "react";
import { formatChartDate } from "@/lib/time";

interface Trade {
  id: string;
  pnl: number;
  close_time: string | null;
}

export default function EquityCurve() {
  const [points, setPoints] = useState<{ date: string; cumPnl: number }[]>([]);

  useEffect(() => {
    fetch("/api/trades?all=true")
      .then((r) => r.json())
      .then((trades: Trade[]) => {
        const closed = trades
          .filter((t) => t.close_time)
          .sort((a, b) => (a.close_time! > b.close_time! ? 1 : -1));

        let cum = 0;
        const pts = closed.map((t) => {
          cum += t.pnl;
          return {
            date: formatChartDate(t.close_time!),
            cumPnl: cum,
          };
        });
        setPoints(pts);
      })
      .catch(() => {});
  }, []);

  if (points.length < 2)
    return (
      <div className="border border-terminal-border rounded bg-terminal-surface p-4 text-matrix-dim text-sm">
        Not enough closed trades for equity curve.
      </div>
    );

  const maxPnl = Math.max(...points.map((p) => p.cumPnl));
  const minPnl = Math.min(...points.map((p) => p.cumPnl));
  const range = (maxPnl - minPnl) || 1;
  const w = 600;
  const h = 160;
  const pad = 20;

  const polyPoints = points
    .map((p, i) => {
      const x = pad + (i / (points.length - 1)) * (w - 2 * pad);
      const y = pad + (1 - (p.cumPnl - minPnl) / range) * (h - 2 * pad);
      return `${x},${y}`;
    })
    .join(" ");

  return (
    <div className="border border-terminal-border rounded bg-terminal-surface p-4">
      <div className="text-matrix-dim text-xs uppercase tracking-widest mb-3">
        Equity Curve
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full" preserveAspectRatio="none">
        {/* zero line */}
        {minPnl <= 0 && maxPnl >= 0 && (
          <line
            x1={pad}
            y1={pad + (1 - (0 - minPnl) / range) * (h - 2 * pad)}
            x2={w - pad}
            y2={pad + (1 - (0 - minPnl) / range) * (h - 2 * pad)}
            stroke="#1a1a1a"
            strokeDasharray="4"
          />
        )}
        <polyline
          points={polyPoints}
          fill="none"
          stroke="#00ff41"
          strokeWidth="2"
          strokeLinejoin="round"
        />
      </svg>
      <div className="flex justify-between text-[10px] text-matrix-dim mt-1 px-2">
        <span>{points[0].date}</span>
        <span>{points[points.length - 1].date}</span>
      </div>
    </div>
  );
}
