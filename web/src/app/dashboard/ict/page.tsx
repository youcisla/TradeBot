"use client";

import { useEffect, useState, useCallback } from "react";
import { formatShort } from "@/lib/time";
import SymbolFilter from "@/components/SymbolFilter";
import PageHeader from "@/components/PageHeader";

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
  trend_continuation_long:  "Trend Cont. Long",
  trend_continuation_short: "Trend Cont. Short",
  reversal_after_sweep:     "Reversal After Sweep",
  range_dealing_long:       "Range Dealing Long",
  range_dealing_short:      "Range Dealing Short",
  session_sweep_reversal:   "Session Sweep Rev.",
};

const CONFLUENCE_LABELS: [string, string][] = [
  ["htf_aligned",   "HTF Bias Aligned"],
  ["swept",         "Liquidity Swept"],
  ["mss",           "MSS Confirmed"],
  ["displacement",  "Displacement"],
  ["fvg",           "FVG Present"],
  ["ob",            "Order Block"],
  ["session_valid", "Killzone Active"],
];

const SCORE_ROWS: [string, string, string][] = [
  ["HTF Bias",        "15", "H4/D1 directional alignment"],
  ["Premium/Discount","12", "Correct price zone for direction"],
  ["Liquidity Sweep", "15", "Recent sweep quality & recency"],
  ["MSS Quality",     "15", "Market structure shift confirmation"],
  ["Displacement",    "10", "Impulsive candle intent confirmation"],
  ["FVG Quality",     "8",  "Fair value gap presence & zone"],
  ["OB Quality",      "8",  "Order block confluence"],
  ["Session/Time",    "7",  "Killzone & macro window activity"],
  ["Target Clarity",  "5",  "Clear opposing liquidity for TP"],
  ["R:R Quality",     "5",  "Risk-reward ratio assessment"],
];

function confColor(v: number): string {
  if (v >= 70) return "#00ff88";
  if (v >= 55) return "#f5c518";
  if (v >= 40) return "#ff9d00";
  return "#ff4455";
}

function KpiCard({ label, value, color = "#00d4ff" }: { label: string; value: string | number; color?: string }) {
  return (
    <div style={{
      background: "#0a0a12",
      border: "1px solid #1c1c28",
      borderTop: `2px solid ${color}`,
      borderRadius: 8,
      padding: "16px 20px",
      textAlign: "center",
    }}>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 20, fontWeight: 700,
        color,
        textShadow: `0 0 14px ${color}55`,
      }}>
        {value}
      </div>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 8.5, letterSpacing: "0.14em",
        textTransform: "uppercase", color: "#607888", marginTop: 4,
      }}>
        {label}
      </div>
    </div>
  );
}

function Card({ title, accent = "#1c1c28", children }: {
  title: string;
  accent?: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{
      background: "#0a0a12",
      border: "1px solid #1c1c28",
      borderTop: `2px solid ${accent}`,
      borderRadius: 8,
      padding: "18px 20px",
    }}>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 9, fontWeight: 700, letterSpacing: "0.16em",
        textTransform: "uppercase", color: "#607888",
        marginBottom: 14,
        paddingBottom: 10,
        borderBottom: "1px solid #1c1c28",
      }}>
        {title}
      </div>
      {children}
    </div>
  );
}

export default function ICTPage() {
  const [symbol, setSymbol]                 = useState<string | null>(null);
  const [setups, setSetups]                 = useState<Setup[]>([]);
  const [modelStats, setModelStats]         = useState<ModelStat[]>([]);
  const [confluenceStats, setConfluenceStats] = useState<ConfluenceStats | null>(null);
  const [sessionStats, setSessionStats]     = useState<SessionStat[]>([]);
  const [loading, setLoading]               = useState(true);

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
    } catch { /* ignore */ }
    finally { setLoading(false); }
  }, [symbol]);

  useEffect(() => {
    fetchData();
    const iv = setInterval(fetchData, 30_000);
    return () => clearInterval(iv);
  }, [fetchData]);

  const filtered = symbol ? setups.filter((s) => s.symbol === symbol) : setups;

  if (loading) {
    return (
      <div style={{
        padding: "48px 20px", textAlign: "center",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 9, letterSpacing: "0.2em", textTransform: "uppercase",
        color: "#607888",
      }}>
        <div style={{
          width: 20, height: 20, border: "1.5px solid #1c1c28",
          borderTop: "1.5px solid #00ff88", borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
          margin: "0 auto 12px",
        }} />
        loading…
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>

      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <PageHeader subsystem="Smart Money" title="ICT Engine" accent="#ff9d00" />
        <SymbolFilter value={symbol} onChange={setSymbol} />
      </div>

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12 }}>
        <KpiCard label="Total Setups"     value={confluenceStats?.total_setups ?? 0}                                       color="#f5c518" />
        <KpiCard label="Avg Confidence"   value={`${Number(confluenceStats?.avg_confidence ?? 0).toFixed(0)}/100`}         color="#00ff88" />
        <KpiCard label="Models Active"    value={modelStats.length}                                                        color="#00d4ff" />
        <KpiCard label="Active Sessions"  value={sessionStats.length}                                                      color="#ff9d00" />
      </div>

      {/* 2-col grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", gap: 16 }}>

        {/* Model distribution */}
        <Card title="Setup Model Distribution" accent="#f5c518">
          {modelStats.length === 0 ? (
            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#3a5248", padding: "10px 0" }}>
              No setups detected yet.
            </div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #1c1c28" }}>
                  {["Model", "Total", "Exec'd", "Score"].map((h) => (
                    <th key={h} style={{
                      padding: "6px 8px",
                      textAlign: h === "Total" || h === "Exec'd" || h === "Score" ? "right" : "left",
                      fontSize: 8.5, letterSpacing: "0.12em", textTransform: "uppercase",
                      color: "#607888", fontWeight: 600,
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {modelStats.map((m) => (
                  <tr key={m.model} style={{ borderBottom: "1px solid rgba(28,28,40,0.5)" }}>
                    <td style={{ padding: "7px 8px", color: "#9aa8b8", fontWeight: 700, fontSize: 10 }}>
                      {MODEL_LABELS[m.model] || m.model}
                    </td>
                    <td style={{ padding: "7px 8px", textAlign: "right", color: "#7a8a9a" }}>{m.total}</td>
                    <td style={{ padding: "7px 8px", textAlign: "right", color: "#7a8a9a" }}>{m.executed}</td>
                    <td style={{ padding: "7px 8px", textAlign: "right", fontWeight: 700, color: confColor(m.avg_confidence) }}>
                      {Number(m.avg_confidence).toFixed(0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        {/* Confluence frequency */}
        <Card title="Confluence Frequency" accent="#00d4ff">
          {!confluenceStats || confluenceStats.total_setups === 0 ? (
            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#3a5248", padding: "10px 0" }}>
              No data yet.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {CONFLUENCE_LABELS.map(([key, label]) => {
                const count = (confluenceStats as unknown as Record<string, number>)[key] ?? 0;
                const pct = confluenceStats.total_setups > 0
                  ? Math.round((count / confluenceStats.total_setups) * 100)
                  : 0;
                const color = pct >= 70 ? "#00ff88" : pct >= 50 ? "#f5c518" : "#ff9d00";
                return (
                  <div key={key} style={{ display: "flex", alignItems: "center", gap: 10 }}>
                    <span style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10, color: "#607888",
                      width: 120, flexShrink: 0,
                    }}>
                      {label}
                    </span>
                    <div style={{
                      flex: 1, height: 5, background: "#0e0e10",
                      border: "1px solid #1c1c28", borderRadius: 3,
                      overflow: "hidden",
                    }}>
                      <div style={{
                        height: "100%", borderRadius: 3,
                        width: `${pct}%`,
                        background: `linear-gradient(90deg, ${color}88, ${color})`,
                        boxShadow: `0 0 6px ${color}44`,
                        transition: "width 0.8s cubic-bezier(0.4, 0, 0.2, 1)",
                      }} />
                    </div>
                    <span style={{
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 10.5, fontWeight: 700, color,
                      width: 36, textAlign: "right", flexShrink: 0,
                    }}>
                      {pct}%
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </Card>

        {/* Session distribution */}
        <Card title="Session Distribution" accent="#ff9d00">
          {sessionStats.length === 0 ? (
            <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#3a5248", padding: "10px 0" }}>
              No session data.
            </div>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #1c1c28" }}>
                  {["Session", "Setups", "Exec'd", "Score"].map((h) => (
                    <th key={h} style={{
                      padding: "6px 8px",
                      textAlign: h !== "Session" ? "right" : "left",
                      fontSize: 8.5, letterSpacing: "0.12em", textTransform: "uppercase",
                      color: "#607888", fontWeight: 600,
                    }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sessionStats.map((s) => (
                  <tr key={s.session} style={{ borderBottom: "1px solid rgba(28,28,40,0.5)" }}>
                    <td style={{ padding: "7px 8px", color: "#9aa8b8", fontWeight: 700, textTransform: "capitalize" }}>{s.session}</td>
                    <td style={{ padding: "7px 8px", textAlign: "right", color: "#7a8a9a" }}>{s.total}</td>
                    <td style={{ padding: "7px 8px", textAlign: "right", color: "#7a8a9a" }}>{s.executed}</td>
                    <td style={{ padding: "7px 8px", textAlign: "right", fontWeight: 700, color: confColor(s.avg_confidence) }}>
                      {Number(s.avg_confidence).toFixed(0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        {/* How it works */}
        <Card title="How the ICT Engine Works" accent="#4da6ff">
          <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5, color: "#607888", lineHeight: 1.7 }}>
            <p style={{ marginBottom: 10 }}>
              Runs a <span style={{ color: "#00d4ff", fontWeight: 700 }}>7-layer analysis</span> pipeline on every tick:
            </p>
            {[
              ["HTF Bias",        "H4/D1 structure for directional filter"],
              ["Market Structure","Swing points, BOS, MSS detection"],
              ["Liquidity",       "BSL/SSL mapping + sweep detection"],
              ["Displacement",    "Impulsive candle / intent confirmation"],
              ["FVG",             "Fair Value Gap detection + fill tracking"],
              ["Order Blocks",    "Supply/demand zones + high-probability validation"],
              ["Session/Time",    "Killzone + macro window scoring"],
            ].map(([name, desc], i) => (
              <div key={name} style={{ display: "flex", gap: 10, marginBottom: 4 }}>
                <span style={{ color: "#506070", minWidth: 16, flexShrink: 0 }}>{i + 1}.</span>
                <span><span style={{ color: "#f5c518", fontWeight: 700 }}>{name}</span> — {desc}</span>
              </div>
            ))}
            <p style={{ marginTop: 12, paddingTop: 10, borderTop: "1px solid #1c1c28", color: "#3a5248" }}>
              After analysis, <span style={{ color: "#ff9d00", fontWeight: 700 }}>6 setup models</span> are tested.
              Each scores <span style={{ color: "#00ff88", fontWeight: 700 }}>0-100</span> from 10 weighted components.
              Only setups above the threshold are forwarded to execution.
            </p>
          </div>
        </Card>
      </div>

      {/* Recent setups table */}
      <div>
        <div style={{
          fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
          color: "#607888", letterSpacing: "0.18em", textTransform: "uppercase",
          marginBottom: 10,
        }}>
          Recent Setups
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
                {["Time","Symbol","Dir","Model","Entry","SL","Score","Zone","Bias","Exec"].map((h) => (
                  <th key={h} style={{
                    padding: "9px 10px",
                    textAlign: h === "Entry" || h === "SL" || h === "Score" ? "right" : "left",
                    fontSize: 8.5, letterSpacing: "0.12em", textTransform: "uppercase",
                    color: "#607888", fontWeight: 600, whiteSpace: "nowrap",
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.slice(0, 50).map((s) => (
                <tr
                  key={s.id}
                  style={{ borderBottom: "1px solid rgba(28,28,40,0.5)", transition: "background 0.1s" }}
                  onMouseEnter={(e) => { (e.currentTarget as HTMLElement).style.background = "rgba(0,212,255,0.03)"; }}
                  onMouseLeave={(e) => { (e.currentTarget as HTMLElement).style.background = ""; }}
                >
                  <td style={{ padding: "7px 10px", color: "#607888", fontSize: 9.5, whiteSpace: "nowrap" }}>
                    {formatShort(s.created_at)}
                  </td>
                  <td style={{ padding: "7px 10px", color: "#00d4ff", fontWeight: 700 }}>{s.symbol}</td>
                  <td style={{ padding: "7px 10px" }}>
                    <span style={{
                      display: "inline-block", padding: "1px 7px", borderRadius: 3,
                      fontSize: 9, fontWeight: 700, letterSpacing: "0.06em",
                      background: s.direction === "BUY" ? "rgba(0,255,136,0.12)" : "rgba(255,68,85,0.12)",
                      color: s.direction === "BUY" ? "#00ff88" : "#ff4455",
                      border: `1px solid ${s.direction === "BUY" ? "rgba(0,255,136,0.3)" : "rgba(255,68,85,0.3)"}`,
                    }}>
                      {s.direction}
                    </span>
                  </td>
                  <td style={{ padding: "7px 10px", color: "#7a8a9a", fontSize: 9.5 }}>
                    {MODEL_LABELS[s.model] || s.model}
                  </td>
                  <td style={{ padding: "7px 10px", textAlign: "right", color: "#9aa8b8", fontFamily: "monospace" }}>
                    {Number(s.entry_price).toFixed(5)}
                  </td>
                  <td style={{ padding: "7px 10px", textAlign: "right", color: "#ff4455", fontFamily: "monospace" }}>
                    {Number(s.stop_loss).toFixed(5)}
                  </td>
                  <td style={{ padding: "7px 10px", textAlign: "right", fontWeight: 700, color: confColor(Number(s.confidence)) }}>
                    {Number(s.confidence).toFixed(0)}
                  </td>
                  <td style={{ padding: "7px 10px", color: "#7a8a9a", fontSize: 9.5, textTransform: "capitalize" }}>
                    {s.entry_zone || "—"}
                  </td>
                  <td style={{ padding: "7px 10px", color: "#7a8a9a", fontSize: 9.5, textTransform: "capitalize" }}>
                    {s.htf_bias || "—"}
                  </td>
                  <td style={{ padding: "7px 10px" }}>
                    {s.executed
                      ? <span style={{ color: "#00ff88", fontWeight: 700 }}>✓</span>
                      : <span style={{ color: "#1c1c28" }}>—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filtered.length === 0 && (
            <div style={{
              padding: "40px 20px", textAlign: "center",
              fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#3a5248",
            }}>
              {symbol ? `no setups for ${symbol}` : "no setups recorded yet"}
            </div>
          )}
        </div>
      </div>

      {/* Score breakdown */}
      <div>
        <div style={{
          fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
          color: "#607888", letterSpacing: "0.18em", textTransform: "uppercase",
          marginBottom: 10,
        }}>
          Confidence Score Breakdown (0-100)
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
                {["Component", "Max", "What It Measures"].map((h) => (
                  <th key={h} style={{
                    padding: "9px 10px",
                    textAlign: h === "Max" ? "right" : "left",
                    fontSize: 8.5, letterSpacing: "0.12em", textTransform: "uppercase",
                    color: "#607888", fontWeight: 600,
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {SCORE_ROWS.map(([name, max, desc]) => (
                <tr key={name} style={{ borderBottom: "1px solid rgba(28,28,40,0.5)" }}>
                  <td style={{ padding: "7px 10px", color: "#f5c518", fontWeight: 700 }}>{name}</td>
                  <td style={{ padding: "7px 10px", textAlign: "right", color: "#00ff88", fontWeight: 700 }}>{max}</td>
                  <td style={{ padding: "7px 10px", color: "#607888", fontSize: 10 }}>{desc}</td>
                </tr>
              ))}
              <tr style={{ borderTop: "2px solid #1c1c28" }}>
                <td style={{ padding: "8px 10px", color: "#9aa8b8", fontWeight: 700, fontSize: 11 }}>Total</td>
                <td style={{ padding: "8px 10px", textAlign: "right", color: "#00ff88", fontWeight: 700, fontSize: 13 }}>100</td>
                <td style={{ padding: "8px 10px", color: "#607888", fontSize: 10 }}>
                  Minimum threshold for execution: <span style={{ color: "#f5c518", fontWeight: 700 }}>55</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
