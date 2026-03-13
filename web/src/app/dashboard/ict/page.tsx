"use client";

import { useEffect, useState, useCallback } from "react";
import SymbolFilter from "@/components/SymbolFilter";

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="border border-terminal-border rounded bg-terminal-surface p-5">
      <div className="text-matrix text-xs font-bold uppercase tracking-widest mb-3 border-b border-terminal-border pb-2">
        {title}
      </div>
      {children}
    </div>
  );
}

const TAG = "px-2 py-0.5 rounded text-[9px] font-bold uppercase";

interface Setup {
  id: number;
  symbol: string;
  direction: string;
  model: string;
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  take_profit_2: number;
  take_profit_3: number;
  confidence: number;
  htf_bias: string;
  htf_regime: string;
  premium_discount: string;
  entry_zone: string;
  reason: string;
  confluences: Record<string, unknown>;
  missing: string[];
  session: string;
  executed: boolean;
  created_at: string;
}

interface ModelStat {
  model: string;
  total: number;
  executed: number;
  avg_confidence: number;
}

interface SessionStat {
  session: string;
  total: number;
  executed: number;
  avg_confidence: number;
}

interface ConfluenceStats {
  total_setups: number;
  htf_aligned: number;
  swept: number;
  mss: number;
  displacement: number;
  fvg: number;
  ob: number;
  session_valid: number;
  avg_confidence: number;
}

const MODEL_LABELS: Record<string, string> = {
  trend_continuation_long: "Trend Cont. Long",
  trend_continuation_short: "Trend Cont. Short",
  reversal_after_sweep: "Reversal After Sweep",
  range_dealing_long: "Range Dealing Long",
  range_dealing_short: "Range Dealing Short",
  session_sweep_reversal: "Session Sweep Rev.",
};

const CONFLUENCE_LABELS: [string, string][] = [
  ["htf_aligned", "HTF Bias Aligned"],
  ["swept", "Liquidity Swept"],
  ["mss", "MSS Confirmed"],
  ["displacement", "Displacement"],
  ["fvg", "FVG Present"],
  ["ob", "Order Block"],
  ["session_valid", "Killzone Active"],
];

export default function ICTPage() {
  const [symbol, setSymbol] = useState<string | null>(null);
  const [setups, setSetups] = useState<Setup[]>([]);
  const [modelStats, setModelStats] = useState<ModelStat[]>([]);
  const [confluenceStats, setConfluenceStats] = useState<ConfluenceStats | null>(null);
  const [sessionStats, setSessionStats] = useState<SessionStat[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchData = useCallback(async () => {
    try {
      const params = symbol ? `?symbol=${encodeURIComponent(symbol)}` : "";
      const res = await fetch(`/api/ict${params}`);
      if (!res.ok) return;
      const data = await res.json();
      setSetups(data.setups ?? []);
      setModelStats(data.modelStats ?? []);
      setConfluenceStats(data.confluenceStats ?? null);
      setSessionStats(data.sessionStats ?? []);
    } catch {
      /* ignore */
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30_000);
    return () => clearInterval(interval);
  }, [fetchData]);

  const filtered = symbol ? setups.filter((s) => s.symbol === symbol) : setups;

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <span className="text-matrix text-xs animate-pulse">Loading ICT engine data…</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-matrix text-lg font-bold">ICT / SMC Strategy Engine</h1>
          <p className="text-matrix-dim text-xs mt-1">
            Real-time overview of ICT setup detection, confluences, and scoring
          </p>
        </div>
        <SymbolFilter value={symbol} onChange={setSymbol} />
      </div>

      {/* KPI Row */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPI label="Total Setups" value={confluenceStats?.total_setups ?? 0} />
        <KPI label="Avg Confidence" value={`${confluenceStats?.avg_confidence ?? 0}/100`} />
        <KPI label="Models Active" value={modelStats.length} />
        <KPI label="Active Sessions" value={sessionStats.length} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Setup Model Distribution */}
        <Card title="Setup Model Distribution">
          {modelStats.length === 0 ? (
            <p className="text-matrix-dim text-[11px]">No setups detected yet</p>
          ) : (
            <table className="w-full text-[11px]">
              <thead className="text-matrix-dim uppercase border-b border-terminal-border text-[9px]">
                <tr>
                  <th className="text-left py-1">Model</th>
                  <th className="text-right py-1">Total</th>
                  <th className="text-right py-1">Executed</th>
                  <th className="text-right py-1">Avg Score</th>
                </tr>
              </thead>
              <tbody className="text-matrix-dim">
                {modelStats.map((m) => (
                  <tr key={m.model} className="border-b border-terminal-border/20">
                    <td className="py-1.5 text-matrix font-bold">{MODEL_LABELS[m.model] || m.model}</td>
                    <td className="py-1.5 text-right">{m.total}</td>
                    <td className="py-1.5 text-right">{m.executed}</td>
                    <td className="py-1.5 text-right">
                      <ConfBadge value={m.avg_confidence} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        {/* Confluence Frequency */}
        <Card title="Confluence Frequency">
          {!confluenceStats || confluenceStats.total_setups === 0 ? (
            <p className="text-matrix-dim text-[11px]">No data yet</p>
          ) : (
            <div className="space-y-2">
              {CONFLUENCE_LABELS.map(([key, label]) => {
                const count = (confluenceStats as unknown as Record<string, number>)[key] ?? 0;
                const pct = confluenceStats.total_setups > 0
                  ? Math.round((count / confluenceStats.total_setups) * 100)
                  : 0;
                return (
                  <div key={key} className="flex items-center gap-3">
                    <span className="text-matrix-dim text-[10px] w-28 shrink-0">{label}</span>
                    <div className="flex-1 h-3 bg-terminal rounded overflow-hidden border border-terminal-border/30">
                      <div
                        className="h-full bg-matrix/40 rounded"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                    <span className="text-matrix text-[10px] font-bold w-12 text-right">{pct}%</span>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        {/* Session Distribution */}
        <Card title="Session Distribution">
          {sessionStats.length === 0 ? (
            <p className="text-matrix-dim text-[11px]">No session data</p>
          ) : (
            <table className="w-full text-[11px]">
              <thead className="text-matrix-dim uppercase border-b border-terminal-border text-[9px]">
                <tr>
                  <th className="text-left py-1">Session</th>
                  <th className="text-right py-1">Setups</th>
                  <th className="text-right py-1">Executed</th>
                  <th className="text-right py-1">Avg Score</th>
                </tr>
              </thead>
              <tbody className="text-matrix-dim">
                {sessionStats.map((s) => (
                  <tr key={s.session} className="border-b border-terminal-border/20">
                    <td className="py-1.5 text-matrix font-bold capitalize">{s.session}</td>
                    <td className="py-1.5 text-right">{s.total}</td>
                    <td className="py-1.5 text-right">{s.executed}</td>
                    <td className="py-1.5 text-right">
                      <ConfBadge value={s.avg_confidence} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        {/* ICT Strategy Explanation */}
        <Card title="How the ICT Engine Works">
          <div className="space-y-2 text-[11px] text-matrix-dim leading-relaxed">
            <p>
              The ICT engine runs a <span className="text-matrix font-bold">7-layer analysis</span> pipeline on every tick:
            </p>
            <ol className="list-decimal list-inside space-y-1 pl-2">
              <li><span className="text-matrix">HTF Bias</span> — H4/D1 structure for directional filter</li>
              <li><span className="text-matrix">Market Structure</span> — Swing points, BOS, MSS detection</li>
              <li><span className="text-matrix">Liquidity</span> — BSL/SSL mapping + sweep detection</li>
              <li><span className="text-matrix">Displacement</span> — Impulsive candle / intent confirmation</li>
              <li><span className="text-matrix">FVG</span> — Fair Value Gap detection + fill tracking</li>
              <li><span className="text-matrix">Order Blocks</span> — Supply/demand zones + high-probability validation</li>
              <li><span className="text-matrix">Session/Time</span> — Killzone + macro window scoring</li>
            </ol>
            <p className="pt-2 border-t border-terminal-border/30">
              After analysis, <span className="text-matrix font-bold">6 setup models</span> are tested for pattern match. Each produces a{" "}
              <span className="text-matrix font-bold">confidence score (0-100)</span> from 10 weighted components.
              Only setups scoring above the minimum threshold are forwarded to the execution pipeline.
            </p>
          </div>
        </Card>
      </div>

      {/* Recent Setups Table */}
      <Card title="Recent Setups">
        {filtered.length === 0 ? (
          <p className="text-matrix-dim text-[11px]">No setups recorded yet. The bot will log setups when it detects ICT patterns.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-[10px]">
              <thead className="text-matrix-dim uppercase border-b border-terminal-border text-[9px]">
                <tr>
                  <th className="text-left py-1 pr-2">Time</th>
                  <th className="text-left py-1 pr-2">Symbol</th>
                  <th className="text-left py-1 pr-2">Dir</th>
                  <th className="text-left py-1 pr-2">Model</th>
                  <th className="text-right py-1 pr-2">Entry</th>
                  <th className="text-right py-1 pr-2">SL</th>
                  <th className="text-right py-1 pr-2">Score</th>
                  <th className="text-left py-1 pr-2">Zone</th>
                  <th className="text-left py-1 pr-2">Bias</th>
                  <th className="text-left py-1">Exec</th>
                </tr>
              </thead>
              <tbody className="text-matrix-dim">
                {filtered.slice(0, 50).map((s) => (
                  <tr key={s.id} className="border-b border-terminal-border/20 hover:bg-terminal-border/10">
                    <td className="py-1.5 pr-2 font-mono">{new Date(s.created_at).toLocaleString("en-GB", { hour: "2-digit", minute: "2-digit", day: "2-digit", month: "short" })}</td>
                    <td className="py-1.5 pr-2 text-matrix font-bold">{s.symbol}</td>
                    <td className="py-1.5 pr-2">
                      <span className={`${TAG} ${s.direction === "BUY" ? "bg-green-900/40 text-green-400" : "bg-red-900/40 text-red-400"}`}>
                        {s.direction}
                      </span>
                    </td>
                    <td className="py-1.5 pr-2">{MODEL_LABELS[s.model] || s.model}</td>
                    <td className="py-1.5 pr-2 text-right font-mono">{Number(s.entry_price).toFixed(5)}</td>
                    <td className="py-1.5 pr-2 text-right font-mono">{Number(s.stop_loss).toFixed(5)}</td>
                    <td className="py-1.5 pr-2 text-right">
                      <ConfBadge value={Number(s.confidence)} />
                    </td>
                    <td className="py-1.5 pr-2 capitalize">{s.entry_zone || "—"}</td>
                    <td className="py-1.5 pr-2 capitalize">{s.htf_bias || "—"}</td>
                    <td className="py-1.5">
                      {s.executed ? (
                        <span className="text-green-400 font-bold">✓</span>
                      ) : (
                        <span className="text-matrix-dim">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Scoring Breakdown Explanation */}
      <Card title="Confidence Score Breakdown (0-100)">
        <table className="w-full text-[11px]">
          <thead className="text-matrix-dim uppercase border-b border-terminal-border text-[9px]">
            <tr>
              <th className="text-left py-1">Component</th>
              <th className="text-right py-1">Max</th>
              <th className="text-left py-1 pl-3">What It Measures</th>
            </tr>
          </thead>
          <tbody className="text-matrix-dim">
            {[
              ["HTF Bias", "15", "H4/D1 directional alignment"],
              ["Premium/Discount", "12", "Correct price zone for direction"],
              ["Liquidity Sweep", "15", "Recent sweep quality & recency"],
              ["MSS Quality", "15", "Market structure shift confirmation"],
              ["Displacement", "10", "Impulsive candle intent confirmation"],
              ["FVG Quality", "8", "Fair value gap presence & zone"],
              ["OB Quality", "8", "Order block confluence"],
              ["Session/Time", "7", "Killzone & macro window activity"],
              ["Target Clarity", "5", "Clear opposing liquidity for TP"],
              ["R:R Quality", "5", "Risk-reward ratio assessment"],
            ].map(([name, max, desc]) => (
              <tr key={name} className="border-b border-terminal-border/20">
                <td className="py-1.5 text-matrix font-bold">{name}</td>
                <td className="py-1.5 text-right">{max}</td>
                <td className="py-1.5 pl-3">{desc}</td>
              </tr>
            ))}
            <tr className="border-t border-matrix/30">
              <td className="py-1.5 text-matrix font-bold">Total</td>
              <td className="py-1.5 text-right text-matrix font-bold">100</td>
              <td className="py-1.5 pl-3">Minimum threshold: 55</td>
            </tr>
          </tbody>
        </table>
      </Card>
    </div>
  );
}

function KPI({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="border border-terminal-border rounded bg-terminal-surface p-4 text-center">
      <div className="text-matrix text-lg font-bold">{value}</div>
      <div className="text-matrix-dim text-[10px] uppercase tracking-wider mt-1">{label}</div>
    </div>
  );
}

function ConfBadge({ value }: { value: number }) {
  const n = Number(value);
  let color = "text-red-400";
  if (n >= 70) color = "text-green-400";
  else if (n >= 55) color = "text-yellow-400";
  else if (n >= 40) color = "text-orange-400";
  return <span className={`${color} font-bold`}>{n.toFixed(0)}</span>;
}
