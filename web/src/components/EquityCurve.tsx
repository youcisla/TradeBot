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
          cum += Number(t.pnl);
          return { date: formatChartDate(t.close_time!), cumPnl: cum };
        });
        setPoints(pts);
      })
      .catch(() => {});
  }, []);

  if (points.length < 2) {
    return (
      <div style={{
        background: "#0a0a12", border: "1px solid #1c1c28",
        borderRadius: 8, padding: "20px 16px",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11, color: "#3a5248",
        textAlign: "center",
      }}>
        Not enough closed trades for equity curve.
      </div>
    );
  }

  const maxPnl = Math.max(...points.map((p) => p.cumPnl));
  const minPnl = Math.min(...points.map((p) => p.cumPnl));
  const range  = (maxPnl - minPnl) || 1;
  const W = 600, H = 160, P = 20;
  const lastPnl = points[points.length - 1].cumPnl;
  const lineColor = lastPnl >= 0 ? "#00ff88" : "#ff4455";

  const pts = points.map((p, i) => ({
    x: P + (i / (points.length - 1)) * (W - 2 * P),
    y: P + (1 - (p.cumPnl - minPnl) / range) * (H - 2 * P),
  }));

  const polyline = pts.map((p) => `${p.x},${p.y}`).join(" ");

  // Build area path: line down to bottom, back left, close
  const firstX = pts[0].x;
  const lastX  = pts[pts.length - 1].x;
  const bottomY = P + (H - 2 * P);
  const areaPath = `M${firstX},${bottomY} L${polyline.replace(/,/g, " L").split(" L").map((pt, i) => i === 0 ? pt : ` L${pt}`).join("")} L${lastX},${bottomY} Z`;

  // Zero line Y
  const zeroY = minPnl <= 0 && maxPnl >= 0
    ? P + (1 - (0 - minPnl) / range) * (H - 2 * P)
    : null;

  return (
    <div style={{
      background: "#0a0a12", border: "1px solid #1c1c28",
      borderTop: `2px solid ${lineColor}`,
      borderRadius: 8, padding: "14px 16px",
    }}>
      <div style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        marginBottom: 10,
      }}>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9, fontWeight: 700, letterSpacing: "0.18em",
          textTransform: "uppercase", color: "#607888",
        }}>
          Equity Curve
        </span>
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 13, fontWeight: 700,
          color: lineColor,
          textShadow: `0 0 10px ${lineColor}55`,
        }}>
          {lastPnl >= 0 ? "+" : ""}{lastPnl.toFixed(2)}
        </span>
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", display: "block" }} preserveAspectRatio="none">
        <defs>
          <linearGradient id="equityFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={lineColor} stopOpacity="0.18" />
            <stop offset="100%" stopColor={lineColor} stopOpacity="0.01" />
          </linearGradient>
        </defs>

        {/* Area fill */}
        <path
          d={`M${firstX},${bottomY} ${pts.map((p) => `L${p.x},${p.y}`).join(" ")} L${lastX},${bottomY} Z`}
          fill="url(#equityFill)"
        />

        {/* Zero line */}
        {zeroY !== null && (
          <line
            x1={P} y1={zeroY} x2={W - P} y2={zeroY}
            stroke="#1c1c28" strokeDasharray="4 4" strokeWidth="1"
          />
        )}

        {/* Equity line */}
        <polyline
          points={polyline}
          fill="none"
          stroke={lineColor}
          strokeWidth="1.5"
          strokeLinejoin="round"
          style={{ filter: `drop-shadow(0 0 3px ${lineColor}66)` }}
        />

        {/* Last point dot */}
        <circle
          cx={pts[pts.length - 1].x}
          cy={pts[pts.length - 1].y}
          r="3"
          fill={lineColor}
          style={{ filter: `drop-shadow(0 0 4px ${lineColor})` }}
        />
      </svg>

      <div style={{
        display: "flex", justifyContent: "space-between",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 9, color: "#1a2a1a", marginTop: 6,
      }}>
        <span>{points[0].date}</span>
        <span>{points[points.length - 1].date}</span>
      </div>
    </div>
  );
}
