"use client";

import { useEffect, useState, useCallback } from "react";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Setup {
  id: number; symbol: string; direction: string; model: string;
  entry_price: number; stop_loss: number;
  take_profit_1: number; take_profit_2: number; take_profit_3: number;
  confidence: number; htf_bias: string; htf_regime: string;
  premium_discount: string; entry_zone: string; reason: string;
  confluences: Record<string, unknown>; missing: string[];
  session: string; executed: boolean; created_at: string;
}

interface ModelStat    { model: string; total: number; executed: number; avg_confidence: number; }
interface SessionStat  { session: string; total: number; executed: number; avg_confidence: number; }
interface ConfluenceStats {
  total_setups: number; htf_aligned: number; swept: number; mss: number;
  displacement: number; fvg: number; ob: number; session_valid: number;
  avg_confidence: number;
}

// ── Constants ─────────────────────────────────────────────────────────────────

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
  ["HTF Bias",         "15", "H4/D1 directional alignment"],
  ["Premium/Discount", "12", "Correct price zone for direction"],
  ["Liquidity Sweep",  "15", "Recent sweep quality & recency"],
  ["MSS Quality",      "15", "Market structure shift confirmation"],
  ["Displacement",     "10", "Impulsive candle intent confirmation"],
  ["FVG Quality",      "8",  "Fair value gap presence & zone"],
  ["OB Quality",       "8",  "Order block confluence"],
  ["Session/Time",     "7",  "Killzone & macro window activity"],
  ["Target Clarity",   "5",  "Clear opposing liquidity for TP"],
  ["R:R Quality",      "5",  "Risk-reward ratio assessment"],
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function confColor(v: number): string {
  if (v >= 70) return "#00fd87";
  if (v >= 55) return "#ffb86c";
  if (v >= 40) return "#e966ff";
  return "#ff716c";
}

function dirColor(dir: string): string {
  return dir === "BUY" ? "#00fd87" : dir === "SELL" ? "#ff716c" : "#adaaaa";
}

function fmtTime(iso: string): string {
  try { return new Date(iso).toLocaleString(); } catch { return "—"; }
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ICTPage() {
  const [symbol,           setSymbol]           = useState<string | null>(null);
  const [setups,           setSetups]           = useState<Setup[]>([]);
  const [modelStats,       setModelStats]       = useState<ModelStat[]>([]);
  const [confluenceStats,  setConfluenceStats]  = useState<ConfluenceStats | null>(null);
  const [sessionStats,     setSessionStats]     = useState<SessionStat[]>([]);
  const [loading,          setLoading]          = useState(true);

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

  const filtered  = symbol ? setups.filter((s) => s.symbol === symbol) : setups;
  const allSymbols = Array.from(new Set(setups.map((s) => s.symbol))).filter(Boolean);

  return (
    <div className="flex flex-col gap-6 mt-6">

      {/* ── Page Header ── */}
      <div className="border-l-4 border-tertiary pl-6 py-2 bg-surface-container-low">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-tertiary text-[10px] font-bold tracking-[0.2em] uppercase">SMART MONEY</span>
          <span className="w-2 h-2 rounded-full bg-tertiary animate-pulse" />
        </div>
        <h1 className="text-3xl md:text-5xl font-extrabold tracking-tighter uppercase mb-2">
          ICT Engine
        </h1>
        <p className="text-on-surface-variant text-sm font-mono">
          7-layer institutional order flow analysis · 6 setup models · 10-component confidence scoring
        </p>
      </div>

      {/* ── Symbol Filter ── */}
      {allSymbols.length > 0 && (
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => setSymbol(null)}
            className={[
              "text-[10px] font-bold tracking-widest uppercase px-3 py-1 border duration-0",
              !symbol
                ? "border-tertiary text-tertiary bg-tertiary/10"
                : "border-outline-variant/30 text-on-surface-variant hover:border-outline",
            ].join(" ")}
          >
            ALL
          </button>
          {allSymbols.map((s) => (
            <button
              key={s}
              onClick={() => setSymbol(s === symbol ? null : s)}
              className={[
                "text-[10px] font-bold tracking-widest uppercase px-3 py-1 border duration-0",
                symbol === s
                  ? "border-tertiary text-tertiary bg-tertiary/10"
                  : "border-outline-variant/30 text-on-surface-variant hover:border-outline",
              ].join(" ")}
            >
              {s}
            </button>
          ))}
        </div>
      )}

      {/* ── KPI Row ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-1 bg-outline-variant/10">
        {[
          { label: "TOTAL SETUPS",   value: confluenceStats?.total_setups ?? 0, color: "#ffb86c" },
          { label: "AVG CONFIDENCE", value: `${Number(confluenceStats?.avg_confidence ?? 0).toFixed(0)}/100`, color: "#00fd87" },
          { label: "MODELS ACTIVE",  value: modelStats.length, color: "#00d2fd" },
          { label: "SESSIONS",       value: sessionStats.length, color: "#e966ff" },
        ].map(({ label, value, color }) => (
          <div key={label} className="bg-surface p-5">
            <div className="text-[9px] text-outline tracking-[0.2em] uppercase mb-1">{label}</div>
            <div className="text-2xl font-extrabold" style={{ color }}>{value}</div>
          </div>
        ))}
      </div>

      {loading && (
        <div className="flex flex-col items-center justify-center py-16 gap-4">
          <div className="w-6 h-6 border-2 border-outline-variant border-t-tertiary rounded-full animate-spin" />
          <span className="text-[9px] text-outline tracking-[0.3em] uppercase">Loading ICT analysis…</span>
        </div>
      )}

      {!loading && (
        <>
          {/* ── 2-col Analysis Cards ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">

            {/* Model Distribution */}
            <div className="bg-surface-container-low border border-outline-variant/10 border-t-2 p-5" style={{ borderTopColor: "#ffb86c" }}>
              <h3 className="text-[9px] font-bold tracking-[0.2em] uppercase text-outline mb-4 pb-3 border-b border-outline-variant/15">
                Setup Model Distribution
              </h3>
              {modelStats.length === 0 ? (
                <div className="text-[11px] text-outline py-4">No setups detected yet.</div>
              ) : (
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="border-b border-outline-variant/15">
                      {["Model", "Total", "Exec'd", "Score"].map((h) => (
                        <th key={h} className={`py-2 text-[9px] font-bold tracking-widest uppercase text-outline ${h !== "Model" ? "text-right" : "text-left"}`}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {modelStats.map((m) => (
                      <tr key={m.model} className="border-b border-outline-variant/5">
                        <td className="py-2 text-on-surface-variant font-bold">{MODEL_LABELS[m.model] || m.model}</td>
                        <td className="py-2 text-right text-outline">{m.total}</td>
                        <td className="py-2 text-right text-outline">{m.executed}</td>
                        <td className="py-2 text-right font-bold" style={{ color: confColor(m.avg_confidence) }}>
                          {Number(m.avg_confidence).toFixed(0)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* Confluence Frequency */}
            <div className="bg-surface-container-low border border-outline-variant/10 border-t-2 p-5" style={{ borderTopColor: "#00d2fd" }}>
              <h3 className="text-[9px] font-bold tracking-[0.2em] uppercase text-outline mb-4 pb-3 border-b border-outline-variant/15">
                Confluence Frequency
              </h3>
              {!confluenceStats || confluenceStats.total_setups === 0 ? (
                <div className="text-[11px] text-outline py-4">No data yet.</div>
              ) : (
                <div className="flex flex-col gap-3">
                  {CONFLUENCE_LABELS.map(([key, label]) => {
                    const count = (confluenceStats as unknown as Record<string, number>)[key] ?? 0;
                    const pct   = confluenceStats.total_setups > 0
                      ? Math.round((count / confluenceStats.total_setups) * 100)
                      : 0;
                    const color = pct >= 70 ? "#00fd87" : pct >= 50 ? "#ffb86c" : "#ff716c";
                    return (
                      <div key={key} className="flex items-center gap-3">
                        <span className="text-[10px] text-on-surface-variant w-32 shrink-0">{label}</span>
                        <div className="flex-1 h-1 bg-surface-container-high overflow-hidden">
                          <div className="h-full" style={{ width: `${pct}%`, background: color }} />
                        </div>
                        <span className="text-[10px] font-bold w-9 text-right shrink-0" style={{ color }}>{pct}%</span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Session Distribution */}
            <div className="bg-surface-container-low border border-outline-variant/10 border-t-2 p-5" style={{ borderTopColor: "#e966ff" }}>
              <h3 className="text-[9px] font-bold tracking-[0.2em] uppercase text-outline mb-4 pb-3 border-b border-outline-variant/15">
                Session Distribution
              </h3>
              {sessionStats.length === 0 ? (
                <div className="text-[11px] text-outline py-4">No session data.</div>
              ) : (
                <table className="w-full text-[11px]">
                  <thead>
                    <tr className="border-b border-outline-variant/15">
                      {["Session", "Setups", "Exec'd", "Score"].map((h) => (
                        <th key={h} className={`py-2 text-[9px] font-bold tracking-widest uppercase text-outline ${h !== "Session" ? "text-right" : "text-left"}`}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sessionStats.map((s) => (
                      <tr key={s.session} className="border-b border-outline-variant/5">
                        <td className="py-2 text-on-surface-variant font-bold capitalize">{s.session}</td>
                        <td className="py-2 text-right text-outline">{s.total}</td>
                        <td className="py-2 text-right text-outline">{s.executed}</td>
                        <td className="py-2 text-right font-bold" style={{ color: confColor(s.avg_confidence) }}>
                          {Number(s.avg_confidence).toFixed(0)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            {/* How It Works */}
            <div className="bg-surface-container-low border border-outline-variant/10 border-t-2 border-t-secondary p-5">
              <h3 className="text-[9px] font-bold tracking-[0.2em] uppercase text-outline mb-4 pb-3 border-b border-outline-variant/15">
                How the ICT Engine Works
              </h3>
              <div className="flex flex-col gap-2.5 text-[11px] text-on-surface-variant">
                {[
                  ["HTF Bias",         "H4/D1 structure for directional filter"],
                  ["Market Structure", "Swing points, BOS, MSS detection"],
                  ["Liquidity",        "BSL/SSL mapping + sweep detection"],
                  ["Displacement",     "Impulsive candle / intent confirmation"],
                  ["FVG",              "Fair Value Gap detection + fill tracking"],
                  ["Order Blocks",     "Supply/demand zones + validation"],
                  ["Session/Time",     "Killzone + macro window scoring"],
                ].map(([name, desc], i) => (
                  <div key={name} className="flex gap-3">
                    <span className="text-outline shrink-0 w-4">{i + 1}.</span>
                    <span>
                      <span className="text-secondary font-bold">{name}</span>
                      {" — "}{desc}
                    </span>
                  </div>
                ))}
                <p className="mt-2 pt-3 border-t border-outline-variant/15 text-outline">
                  After analysis, <span className="text-tertiary font-bold">6 setup models</span> score{" "}
                  <span className="text-primary-fixed font-bold">0–100</span> from 10 weighted components.
                  Threshold for execution: <span className="text-secondary font-bold">55</span>.
                </p>
              </div>
            </div>
          </div>

          {/* ── Recent Setups Table ── */}
          <div>
            <h3 className="text-[9px] font-bold tracking-[0.3em] text-outline uppercase mb-4">
              Recent Setups
            </h3>
            <div className="overflow-x-auto bg-surface-container border border-outline-variant/10">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="border-b border-outline-variant/15">
                    {["Time","Symbol","Dir","Model","Entry","SL","Score","Zone","Bias","Exec"].map((h) => (
                      <th
                        key={h}
                        className={[
                          "px-3 py-2.5 text-[9px] font-bold tracking-[0.15em] uppercase text-outline whitespace-nowrap",
                          ["Entry","SL","Score"].includes(h) ? "text-right" : "text-left",
                        ].join(" ")}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {filtered.slice(0, 50).map((s, i) => (
                    <tr
                      key={s.id}
                      className={`border-b border-outline-variant/5 hover:bg-surface-bright duration-0 ${i % 2 === 0 ? "bg-surface-container-low" : ""}`}
                    >
                      <td className="px-3 py-2 text-outline whitespace-nowrap">{fmtTime(s.created_at)}</td>
                      <td className="px-3 py-2 text-secondary font-bold">{s.symbol}</td>
                      <td className="px-3 py-2">
                        <span
                          className="text-[9px] font-bold px-2 py-0.5 border"
                          style={{
                            color: dirColor(s.direction),
                            background: `${dirColor(s.direction)}18`,
                            borderColor: `${dirColor(s.direction)}33`,
                          }}
                        >
                          {s.direction}
                        </span>
                      </td>
                      <td className="px-3 py-2 text-on-surface-variant">{MODEL_LABELS[s.model] || s.model}</td>
                      <td className="px-3 py-2 text-right text-on-surface font-mono">{Number(s.entry_price).toFixed(5)}</td>
                      <td className="px-3 py-2 text-right text-error font-mono">{Number(s.stop_loss).toFixed(5)}</td>
                      <td className="px-3 py-2 text-right font-bold" style={{ color: confColor(Number(s.confidence)) }}>
                        {Number(s.confidence).toFixed(0)}
                      </td>
                      <td className="px-3 py-2 text-outline capitalize">{s.entry_zone || "—"}</td>
                      <td className="px-3 py-2 text-outline capitalize">{s.htf_bias || "—"}</td>
                      <td className="px-3 py-2">
                        {s.executed
                          ? <span className="text-primary-fixed font-bold">✓</span>
                          : <span className="text-outline-variant">—</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              {filtered.length === 0 && (
                <div className="py-10 text-center text-[11px] text-outline uppercase tracking-widest">
                  {symbol ? `No setups for ${symbol}` : "No setups recorded yet"}
                </div>
              )}
            </div>
          </div>

          {/* ── Score Breakdown ── */}
          <div>
            <h3 className="text-[9px] font-bold tracking-[0.3em] text-outline uppercase mb-4">
              Confidence Score Breakdown (0–100)
            </h3>
            <div className="overflow-x-auto bg-surface-container border border-outline-variant/10">
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="border-b border-outline-variant/15">
                    {["Component", "Max", "What It Measures"].map((h) => (
                      <th
                        key={h}
                        className={`px-3 py-2.5 text-[9px] font-bold tracking-widest uppercase text-outline ${h === "Max" ? "text-right" : "text-left"}`}
                      >
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {SCORE_ROWS.map(([name, max, desc]) => (
                    <tr key={name} className="border-b border-outline-variant/5">
                      <td className="px-3 py-2 text-secondary font-bold">{name}</td>
                      <td className="px-3 py-2 text-right text-primary-fixed font-bold">{max}</td>
                      <td className="px-3 py-2 text-outline">{desc}</td>
                    </tr>
                  ))}
                  <tr className="border-t-2 border-outline-variant/30">
                    <td className="px-3 py-2.5 text-on-surface font-bold">Total</td>
                    <td className="px-3 py-2.5 text-right text-primary-fixed font-extrabold text-lg">100</td>
                    <td className="px-3 py-2.5 text-outline">
                      Minimum threshold for execution:{" "}
                      <span className="text-secondary font-bold">55</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
