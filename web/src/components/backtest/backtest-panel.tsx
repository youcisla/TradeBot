"use client";

import { useState } from "react";
import { useBacktestStatus, type BacktestJob, type StrategyStats } from "@/lib/swr";
import { Panel } from "@/components/ui/panel";
import { SectionHeader } from "@/components/ui/section-header";

const SYMBOLS = ["GBPUSD", "EURUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD", "XAUUSD"];
const STRATEGIES = [
  { value: "ict_smc", label: "ICT SMC" },
  { value: "session_range", label: "Session Range" },
  { value: "pairs_spread", label: "Pairs Spread" },
];

function fmtPct(v: number) {
  return v ? `${(v * 100).toFixed(1)}%` : "—";
}
function fmtScore(v: number) {
  return v ? v.toFixed(4) : "—";
}

function fmtElapsed(startedAt: string) {
  const ms = Date.now() - new Date(startedAt).getTime();
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  return `${Math.floor(s / 60)}m ${s % 60}s`;
}

function StatusBadge({ job }: { job: BacktestJob }) {
  const color =
    job.status === "done"
      ? "var(--positive)"
      : job.status === "error"
        ? "var(--negative)"
        : "var(--accent)";
  return (
    <span
      className="text-xs font-mono px-2 py-0.5 rounded"
      style={{
        background: color + "22",
        color,
        border: `1px solid ${color}44`,
      }}
    >
      {job.status.toUpperCase()}
      {job.status === "running" && job.started_at ? ` — ${fmtElapsed(job.started_at)}` : ""}
    </span>
  );
}

function ResultsTable({ stats }: { stats: StrategyStats[] }) {
  if (!stats.length) return <p style={{ color: "var(--text-3)" }}>No results returned.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs font-mono">
        <thead>
          <tr
            className="border-b"
            style={{ borderColor: "var(--border)", color: "var(--text-3)" }}
          >
            {["Symbol", "Strategy", "Signals", "Win%", "PF", "Score", "TP1", "TP2", "TP3", "SL"].map((h) => (
              <th key={h} className="px-2 py-2 text-left font-bold uppercase tracking-widest" style={{ fontSize: 8 }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {stats.map((s, i) => {
            const rowColor = s.win_rate >= 0.5 ? "var(--positive)" : s.win_rate >= 0.4 ? "var(--warning)" : "var(--text-2)";
            return (
              <tr
                key={i}
                className="border-b"
                style={{ borderColor: "var(--border)", color: rowColor }}
              >
                <td className="px-2 py-2">{s.symbol}</td>
                <td className="px-2 py-2">{s.strategy}</td>
                <td className="px-2 py-2 text-center">{s.signals}</td>
                <td className="px-2 py-2 text-center">{fmtPct(s.win_rate)}</td>
                <td className="px-2 py-2 text-center">{fmtScore(s.profit_factor)}</td>
                <td className="px-2 py-2 text-center">{fmtScore(s.score)}</td>
                <td className="px-2 py-2 text-center">{s.tp1_hits}</td>
                <td className="px-2 py-2 text-center">{s.tp2_hits}</td>
                <td className="px-2 py-2 text-center">{s.tp3_hits}</td>
                <td className="px-2 py-2 text-center">{s.sl_hits}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function BacktestPanel() {
  const [symbol, setSymbol] = useState("GBPUSD");
  const [strategy, setStrategy] = useState("ict_smc");
  const [jobId, setJobId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const { data: job } = useBacktestStatus(jobId);

  async function runBacktest() {
    setRunning(true);
    setJobId(null);
    try {
      const res = await fetch("/api/backtest/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, strategy }),
      });
      const data = await res.json();
      if (data.jobId) setJobId(data.jobId);
    } catch {
      setRunning(false);
    }
  }

  const isRunning = job?.status === "running";

  return (
    <Panel
      title={
        <SectionHeader
          title="Strategy Backtest"
          action={
            job ? <StatusBadge job={job} /> : null
          }
        />
      }
    >
      <div className="flex flex-col gap-4">
        {/* ── Controls ─────────────────────────────────────── */}
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex flex-col gap-1">
            <label
              className="text-xs uppercase tracking-widest"
              style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 8 }}
            >
              Symbol
            </label>
            <select
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="px-3 py-2 rounded text-sm font-mono"
              style={{
                background: "var(--bg-3)",
                border: "1px solid var(--border)",
                color: "var(--text-1)",
              }}
            >
              {SYMBOLS.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label
              className="text-xs uppercase tracking-widest"
              style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 8 }}
            >
              Strategy
            </label>
            <select
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
              className="px-3 py-2 rounded text-sm font-mono"
              style={{
                background: "var(--bg-3)",
                border: "1px solid var(--border)",
                color: "var(--text-1)",
              }}
            >
              {STRATEGIES.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          <button
            onClick={runBacktest}
            disabled={running}
            className="px-4 py-2 rounded text-sm font-bold transition-colors"
            style={{
              background: running ? "var(--bg-3)" : "var(--accent)",
              color: running ? "var(--text-3)" : "var(--bg)",
              border: running ? "1px solid var(--border)" : "none",
              cursor: running ? "not-allowed" : "pointer",
            }}
          >
            {running ? "Running..." : "Run Backtest"}
          </button>
        </div>

        {/* ── Error ──────────────────────────────────────────── */}
        {job?.status === "error" && (
          <div
            className="px-4 py-3 rounded text-sm"
            style={{ background: "var(--negative)#18", color: "var(--negative)", border: "1px solid var(--negative)#44" }}
          >
            {job.error ?? "Backtest failed."}
          </div>
        )}

        {/* ── Results ─────────────────────────────────────────── */}
        {job?.status === "done" && job.result && (
          <ResultsTable stats={job.result} />
        )}

        {/* ── Idle state ─────────────────────────────────────── */}
        {!job && !running && (
          <p className="text-sm" style={{ color: "var(--text-3)" }}>
            Select a symbol and strategy, then click <strong style={{ color: "var(--accent)" }}>Run Backtest</strong> to simulate 2 years of H1 history.
          </p>
        )}
      </div>
    </Panel>
  );
}
