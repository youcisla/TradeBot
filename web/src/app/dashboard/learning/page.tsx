"use client";

import { useEffect, useState } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface StrategyConfidence {
  strategy: string; confidence: number;
  total_trades: number; total_score: number; last_updated: string;
}

interface TradeScore {
  id: number; trade_id: string; strategy: string; symbol: string;
  session: string; market_condition: string;
  score: number; pnl: number; created_at: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatStrategy(raw: string): string {
  const model = raw.includes(":") ? raw.split(":").pop()! : raw;
  return model.toLowerCase().replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function confColor(conf: number): string {
  if (conf >= 0.7) return "#00fd87";
  if (conf >= 0.5) return "#ffb86c";
  return "#ff716c";
}

function confLabel(conf: number): string {
  if (conf >= 0.7) return "FULL";
  if (conf >= 0.5) return "NORMAL";
  if (conf >= 0.2) return "LOW";
  return "DISABLED";
}

function scoreColor(score: number): string {
  if (score >= 3) return "#00fd87";
  if (score > 0)  return "#a4ffb9";
  if (score >= -2) return "#ffb86c";
  return "#ff716c";
}

function fmtTime(iso: string): string {
  try { return new Date(iso).toLocaleString(); } catch { return "—"; }
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function LearningPage() {
  const [confidences, setConfidences] = useState<StrategyConfidence[]>([]);
  const [scores, setScores]           = useState<TradeScore[]>([]);
  const [symbol, setSymbol]           = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = () =>
      fetch("/api/learning")
        .then((r) => r.json())
        .then((data) => {
          if (!active) return;
          setConfidences(data.confidences ?? []);
          setScores(data.scores ?? []);
        })
        .catch(() => {});
    load();
    const id = setInterval(load, 15_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  const symbols = Array.from(new Set(scores.map((s) => s.symbol))).filter(Boolean);
  const filtered = symbol ? scores.filter((s) => s.symbol === symbol) : scores;

  const totalWins   = filtered.filter((s) => Number(s.score) > 0).length;
  const totalLosses = filtered.filter((s) => Number(s.score) <= 0).length;
  const avgScore    = filtered.length > 0
    ? filtered.reduce((a, t) => a + Number(t.score), 0) / filtered.length
    : 0;

  return (
    <div className="flex flex-col gap-6 mt-6">

      {/* ── Page Header ── */}
      <div className="border-l-4 border-secondary pl-6 py-2 bg-surface-container-low">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-secondary text-[10px] font-bold tracking-[0.2em] uppercase">FEEDBACK LOOP</span>
          <span className="w-2 h-2 rounded-full bg-secondary animate-pulse" />
        </div>
        <h1 className="text-3xl md:text-5xl font-extrabold tracking-tighter uppercase mb-2">
          Learning System
        </h1>
        <p className="text-on-surface-variant text-sm font-mono">
          Reinforcement loop — strategy confidence adjusts on every scored trade
        </p>
      </div>

      {/* ── Symbol Filter ── */}
      {symbols.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSymbol(null)}
            className={[
              "text-[10px] font-bold tracking-widest uppercase px-3 py-1 border duration-0",
              !symbol
                ? "border-secondary text-secondary bg-secondary/10"
                : "border-outline-variant/30 text-on-surface-variant hover:border-outline",
            ].join(" ")}
          >
            ALL
          </button>
          {symbols.map((s) => (
            <button
              key={s}
              onClick={() => setSymbol(s === symbol ? null : s)}
              className={[
                "text-[10px] font-bold tracking-widest uppercase px-3 py-1 border duration-0",
                symbol === s
                  ? "border-secondary text-secondary bg-secondary/10"
                  : "border-outline-variant/30 text-on-surface-variant hover:border-outline",
              ].join(" ")}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* ── Stats Strip ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-1 bg-outline-variant/10">
        {[
          { label: "SCORED",    value: filtered.length,                      color: "text-on-surface" },
          { label: "WINS",      value: totalWins,                             color: "text-primary-fixed" },
          { label: "LOSSES",    value: totalLosses,                          color: "text-error" },
          { label: "AVG SCORE", value: `${avgScore >= 0 ? "+" : ""}${avgScore.toFixed(1)}`, color: avgScore >= 0 ? "text-primary-fixed" : "text-error" },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-surface p-4">
            <div className="text-[9px] text-on-surface-variant tracking-[0.2em] uppercase mb-1">{label}</div>
            <div className={`text-2xl font-extrabold ${color}`}>{value}</div>
          </div>
        ))}
      </div>

      {/* ── Strategy Confidence ── */}
      <div>
        <div className="flex items-center gap-4 mb-4">
          <h3 className="text-[9px] font-bold tracking-[0.3em] text-on-surface-variant uppercase">
            Strategy Confidence
          </h3>
          <span className="text-[9px] text-outline">
            20% = disabled · 50% = reduced · 70% = full
          </span>
        </div>

        {confidences.length === 0 ? (
          <div className="p-8 bg-surface-container text-center text-[11px] text-on-surface-variant uppercase tracking-widest">
            No strategies tracked yet
          </div>
        ) : (
          <div className="flex flex-col gap-2">
            {confidences.map((c) => {
              const pct   = Math.max(0, Math.min(100, Number(c.confidence) * 100));
              const color = confColor(Number(c.confidence));
              const label = confLabel(Number(c.confidence));
              return (
                <div
                  key={c.strategy}
                  className="relative bg-surface-container-low border border-outline-variant/10 p-4 overflow-hidden"
                >
                  {/* Background fill track */}
                  <div
                    className="absolute inset-0 pointer-events-none"
                    style={{ background: `linear-gradient(90deg, ${color}08 0%, transparent ${pct}%, transparent 100%)` }}
                  />
                  <div className="relative flex items-center gap-4">
                    {/* Name + meta */}
                    <div className="w-44 shrink-0">
                      <div className="text-[11px] font-bold text-on-surface-variant truncate" title={c.strategy}>
                        {formatStrategy(c.strategy)}
                      </div>
                      <div className="text-[9px] text-outline mt-0.5">
                        {Number(c.total_trades)} trades · score {Number(c.total_score) >= 0 ? "+" : ""}{Number(c.total_score)}
                      </div>
                    </div>

                    {/* Bar */}
                    <div className="flex-1">
                      <div className="w-full h-1.5 bg-surface-container-high overflow-hidden">
                        <div
                          className="h-full"
                          style={{ width: `${pct}%`, background: color }}
                        />
                      </div>
                    </div>

                    {/* Pct */}
                    <div className="w-12 text-right shrink-0">
                      <span className="text-base font-extrabold" style={{ color }}>{pct.toFixed(0)}%</span>
                    </div>

                    {/* Badge */}
                    <div className="w-20 shrink-0 text-right">
                      <span
                        className="text-[9px] font-bold px-2 py-0.5 border"
                        style={{
                          color,
                          background: `${color}18`,
                          borderColor: `${color}33`,
                        }}
                      >
                        {label}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Recent Scores ── */}
      <div>
        <h3 className="text-[9px] font-bold tracking-[0.3em] text-on-surface-variant uppercase mb-4">
          Recent Scores
        </h3>

        <div className="overflow-x-auto bg-surface-container border border-outline-variant/10">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-outline-variant/15">
                {["Trade", "Strategy", "Symbol", "Session", "Condition", "Score", "P&L", "Time"].map((h) => (
                  <th
                    key={h}
                    className={[
                      "px-3 py-2.5 text-[9px] font-bold tracking-[0.15em] uppercase text-outline",
                      h === "Score" || h === "P&L" ? "text-right" : "text-left",
                    ].join(" ")}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((s, i) => (
                <tr
                  key={s.id}
                  className={`border-b border-outline-variant/5 hover:bg-surface-bright duration-0 ${i % 2 === 0 ? "bg-surface-container-low" : ""}`}
                >
                  <td className="px-3 py-2 text-outline font-mono">{s.trade_id.slice(0, 8)}</td>
                  <td className="px-3 py-2 text-on-surface-variant" title={s.strategy}>
                    {formatStrategy(s.strategy)}
                  </td>
                  <td className="px-3 py-2 text-secondary font-bold">{s.symbol}</td>
                  <td className="px-3 py-2 text-outline">{s.session || "—"}</td>
                  <td className="px-3 py-2 text-outline">{s.market_condition || "—"}</td>
                  <td className="px-3 py-2 text-right font-bold" style={{ color: scoreColor(Number(s.score)) }}>
                    {Number(s.score) >= 0 ? "+" : ""}{s.score}
                  </td>
                  <td className="px-3 py-2 text-right font-bold" style={{ color: Number(s.pnl) >= 0 ? "#00fd87" : "#ff716c" }}>
                    {Number(s.pnl) >= 0 ? "+" : ""}{Number(s.pnl).toFixed(2)}
                  </td>
                  <td className="px-3 py-2 text-outline whitespace-nowrap">{fmtTime(s.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {filtered.length === 0 && (
            <div className="py-10 text-center text-[11px] text-outline uppercase tracking-widest">
              {symbol ? `No scores for ${symbol}` : "No scores recorded yet"}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
