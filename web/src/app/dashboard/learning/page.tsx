"use client";

import { useEffect, useState } from "react";
import { formatShort } from "@/lib/time";
import SymbolFilter from "@/components/SymbolFilter";

interface StrategyConfidence {
  strategy: string; confidence: number;
  total_trades: number; total_score: number; last_updated: string;
}

interface TradeScore {
  id: number; trade_id: string; strategy: string; symbol: string;
  session: string; market_condition: string;
  score: number; pnl: number; created_at: string;
}

function formatStrategy(raw: string): string {
  const model = raw.includes(":") ? raw.split(":").pop()! : raw;
  return model.toLowerCase().replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function confColor(conf: number): string {
  if (conf >= 0.7) return "#00ff88";
  if (conf >= 0.5) return "#f5c518";
  return "#ff4455";
}

function scoreColor(score: number): string {
  if (score >= 3) return "#00ff88";
  if (score > 0)  return "#76ff03";
  if (score >= -2) return "#f5c518";
  return "#ff4455";
}

function ConfidenceBar({ strategy, confidence, totalTrades, totalScore }: {
  strategy: string; confidence: number; totalTrades: number; totalScore: number;
}) {
  const pct   = Math.max(0, Math.min(100, confidence * 100));
  const color = confColor(confidence);
  const label = formatStrategy(strategy);

  return (
    <div style={{
      background: "#0a0a12", border: "1px solid #1c1c28",
      borderRadius: 6, padding: "12px 16px",
      position: "relative", overflow: "hidden",
    }}>
      {/* Background fill */}
      <div style={{
        position: "absolute", inset: 0,
        background: `linear-gradient(90deg, ${color}08 0%, transparent ${pct}%, transparent 100%)`,
        pointerEvents: "none",
      }} />

      <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 14 }}>
        {/* Strategy name */}
        <div style={{ width: 200, flexShrink: 0 }}>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
            fontWeight: 700, color: "#9aa8b8", letterSpacing: "0.04em",
          }} title={strategy}>
            {label}
          </div>
          <div style={{
            fontFamily: "'JetBrains Mono', monospace", fontSize: 8.5,
            color: "#2a3a4a", marginTop: 2, letterSpacing: "0.06em",
          }}>
            {totalTrades} trades · score {totalScore >= 0 ? "+" : ""}{totalScore}
          </div>
        </div>

        {/* Bar */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{
            height: 6, background: "#0e0e10",
            border: "1px solid #1c1c28", borderRadius: 3,
            overflow: "hidden",
          }}>
            <div style={{
              height: "100%", borderRadius: 3,
              width: `${pct}%`,
              background: `linear-gradient(90deg, ${color}88, ${color})`,
              boxShadow: `0 0 8px ${color}55`,
              transition: "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)",
            }} />
          </div>

          {/* Threshold markers */}
          <div style={{ position: "relative", height: 0 }}>
            {[20, 50, 70].map((threshold) => (
              <div key={threshold} style={{
                position: "absolute",
                left: `${threshold}%`,
                top: -12,
                width: 1, height: 8,
                background: "#1c1c28",
              }} />
            ))}
          </div>
        </div>

        {/* Value */}
        <div style={{ width: 64, textAlign: "right", flexShrink: 0 }}>
          <span style={{
            fontFamily: "'JetBrains Mono', monospace",
            fontSize: 16, fontWeight: 700, color,
            textShadow: `0 0 10px ${color}66`,
          }}>
            {pct.toFixed(0)}%
          </span>
        </div>

        {/* Status badge */}
        <div style={{ width: 80, flexShrink: 0, textAlign: "right" }}>
          <span style={{
            display: "inline-block",
            padding: "2px 8px", borderRadius: 3,
            fontSize: 9, fontWeight: 700, letterSpacing: "0.08em",
            fontFamily: "'JetBrains Mono', monospace",
            background: confidence >= 0.2 ? `${color}18` : "rgba(255,68,85,0.12)",
            color: confidence >= 0.2 ? color : "#ff4455",
            border: `1px solid ${confidence >= 0.2 ? `${color}33` : "rgba(255,68,85,0.25)"}`,
          }}>
            {confidence >= 0.7 ? "FULL" : confidence >= 0.5 ? "NORMAL" : confidence >= 0.2 ? "LOW" : "DISABLED"}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function LearningPage() {
  const [confidences, setConfidences] = useState<StrategyConfidence[]>([]);
  const [scores, setScores]           = useState<TradeScore[]>([]);
  const [symbol, setSymbol]           = useState<string | null>(null);

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

  // Aggregate stats
  const totalWins   = filtered.filter((s) => Number(s.score) > 0).length;
  const totalLosses = filtered.filter((s) => Number(s.score) <= 0).length;
  const avgScore    = filtered.length > 0 ? filtered.reduce((s, t) => s + Number(t.score), 0) / filtered.length : 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* Header */}
      <div>
        <div style={{
          fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
          color: "#2a3a4a", letterSpacing: "0.2em", textTransform: "uppercase",
        }}>
          Adaptive System
        </div>
        <h1 style={{
          fontSize: 20, fontFamily: "'JetBrains Mono', monospace",
          fontWeight: 700, color: "#4da6ff",
          textShadow: "0 0 20px rgba(77,166,255,0.3)", marginTop: 2,
        }}>
          Learning System
        </h1>
      </div>

      <SymbolFilter value={symbol} onChange={setSymbol} />

      {/* Stats strip */}
      {filtered.length > 0 && (
        <div style={{
          display: "flex", gap: 24, padding: "10px 16px",
          background: "#0a0a12", border: "1px solid #1c1c28", borderRadius: 6,
          fontFamily: "'JetBrains Mono', monospace",
        }}>
          <div>
            <div style={{ fontSize: 8.5, color: "#2a3a4a", letterSpacing: "0.15em", textTransform: "uppercase" }}>Scored</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#9aa8b8", marginTop: 2 }}>{filtered.length}</div>
          </div>
          <div>
            <div style={{ fontSize: 8.5, color: "#2a3a4a", letterSpacing: "0.15em", textTransform: "uppercase" }}>Wins</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#00ff88", marginTop: 2 }}>{totalWins}</div>
          </div>
          <div>
            <div style={{ fontSize: 8.5, color: "#2a3a4a", letterSpacing: "0.15em", textTransform: "uppercase" }}>Losses</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#ff4455", marginTop: 2 }}>{totalLosses}</div>
          </div>
          <div>
            <div style={{ fontSize: 8.5, color: "#2a3a4a", letterSpacing: "0.15em", textTransform: "uppercase" }}>Avg Score</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: avgScore >= 0 ? "#00ff88" : "#ff4455", marginTop: 2 }}>
              {avgScore >= 0 ? "+" : ""}{avgScore.toFixed(1)}
            </div>
          </div>
        </div>
      )}

      {/* Strategy Confidence */}
      <div>
        <div style={{
          fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
          color: "#2a3a4a", letterSpacing: "0.18em", textTransform: "uppercase",
          marginBottom: 10,
        }}>
          Strategy Confidence
          <span style={{ marginLeft: 10, color: "#1c2c1c" }}>
            20% = disabled · 50% = reduced · 70% = full
          </span>
        </div>
        {confidences.length === 0 ? (
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#1e2e1e", padding: "20px 0" }}>
            No strategies tracked yet.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {confidences.map((c) => (
              <ConfidenceBar
                key={c.strategy}
                strategy={c.strategy}
                confidence={Number(c.confidence)}
                totalTrades={Number(c.total_trades)}
                totalScore={Number(c.total_score)}
              />
            ))}
          </div>
        )}
      </div>

      {/* Recent Scores */}
      <div>
        <div style={{
          fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
          color: "#2a3a4a", letterSpacing: "0.18em", textTransform: "uppercase",
          marginBottom: 10,
        }}>
          Recent Scores
        </div>
        <div style={{
          background: "#0e0e10", border: "1px solid #1c1c28",
          borderRadius: 8, overflow: "auto",
        }}>
          <table style={{
            width: "100%", borderCollapse: "collapse",
            fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5,
          }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #1c1c28" }}>
                {["Trade","Strategy","Symbol","Session","Condition","Score","P&L","Time"].map((h) => (
                  <th key={h} style={{
                    padding: "9px 10px",
                    textAlign: h === "Score" || h === "P&L" ? "right" : "left",
                    fontSize: 8.5, letterSpacing: "0.12em", textTransform: "uppercase",
                    color: "#2a3a4a", fontWeight: 600,
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((s) => (
                <tr
                  key={s.id}
                  style={{ borderBottom: "1px solid rgba(28,28,40,0.5)", transition: "background 0.1s" }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(0,212,255,0.03)"; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = ""; }}
                >
                  <td style={{ padding: "7px 10px", color: "#2a3a4a", fontSize: 9.5 }}>{s.trade_id.slice(0, 8)}</td>
                  <td style={{ padding: "7px 10px", color: "#9aa8b8", fontSize: 9.5 }} title={s.strategy}>
                    {formatStrategy(s.strategy)}
                  </td>
                  <td style={{ padding: "7px 10px", color: "#00d4ff", fontWeight: 700 }}>{s.symbol}</td>
                  <td style={{ padding: "7px 10px", color: "#4a5568", fontSize: 9.5 }}>{s.session || "—"}</td>
                  <td style={{ padding: "7px 10px", color: "#4a5568", fontSize: 9.5 }}>{s.market_condition || "—"}</td>
                  <td style={{ padding: "7px 10px", textAlign: "right", fontWeight: 700, color: scoreColor(Number(s.score)) }}>
                    {Number(s.score) >= 0 ? "+" : ""}{s.score}
                  </td>
                  <td style={{ padding: "7px 10px", textAlign: "right", color: Number(s.pnl) >= 0 ? "#00ff88" : "#ff4455" }}>
                    {Number(s.pnl) >= 0 ? "+" : ""}{Number(s.pnl).toFixed(2)}
                  </td>
                  <td style={{ padding: "7px 10px", color: "#2a3a4a", fontSize: 9.5, whiteSpace: "nowrap" }}>
                    {formatShort(s.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <div style={{ padding: "40px 20px", textAlign: "center", fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#1e2e1e" }}>
              {symbol ? `no scores for ${symbol}` : "no scores recorded yet"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
