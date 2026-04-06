"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useAppShell } from "@/components/AppShell";

// ── Types ─────────────────────────────────────────────────────────────────────

interface RiskData {
  equity?: number;
  balance?: number;
  daily_pnl?: number;
  daily_pnl_pct?: number;
  monthly_pnl?: number;
  monthly_pnl_pct?: number;
  max_daily_loss?: number;
  max_daily_loss_pct?: number;
  max_total_drawdown?: number;
  max_total_drawdown_pct?: number;
  risk_per_trade_pct?: number;
  max_lot_size?: number;
  max_concurrent_trades?: number;
  open_trades?: number;
  emergency_stop?: boolean;
  emergency_reason?: string;
  wfo_enabled?: boolean;
  wfo_period?: number;
  last_retrain?: string;
}

interface Trade {
  id: number;
  symbol: string;
  direction: string;
  lot_size?: number;
  status: string;
  pnl?: number;
}

interface AgentEvent {
  id?: number;
  agent: string;
  level: string;
  message?: string;
  msg?: string;
  created_at?: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtUsd(v?: number): string {
  if (v == null || isNaN(v)) return "—";
  const f = Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (v < 0 ? "-$" : "$") + f;
}

function pnlColor(v?: number): string {
  if (v == null) return "rgba(232,234,237,0.40)";
  return v > 0 ? "#30D158" : v < 0 ? "#FF453A" : "rgba(232,234,237,0.40)";
}

function limitBar(value: number, max: number): { used: number; color: string } {
  const pct = max !== 0 ? Math.min(Math.abs(value / max), 1) * 100 : 0;
  const color = pct > 90 ? "#FF453A" : pct > 60 ? "#FF9F0A" : "#30D158";
  return { used: pct, color };
}

function relTime(iso?: string): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  const h  = Math.floor(ms / 3_600_000);
  if (h < 1)  return `${Math.floor(ms / 60_000)}m ago`;
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function relAge(ts?: string): string {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 3_600_000)  return Math.floor(ms / 60_000)    + "m";
  if (ms < 86_400_000) return Math.floor(ms / 3_600_000) + "h";
  return                      Math.floor(ms / 86_400_000) + "d";
}

// ── Tokens ─────────────────────────────────────────────────────────────────────

const C = {
  bg:       "var(--card-bg)",
  border:   "var(--card-border)",
  radius:   "var(--card-radius)",
  mono:     "var(--font-mono-stack)",
  label:    "var(--section-label)",
  positive:  "#30D158",
  negative:  "#FF453A",
  warning:   "#FF9F0A",
  cyan:     "#63D4FF",
  textDim:   "rgba(232,234,237,0.30)",
  textMid:   "rgba(232,234,237,0.55)",
};
const MONO = C.mono;

// ── Sub-components ────────────────────────────────────────────────────────────

function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return <div style={{ background: C.bg, border: `1px solid ${C.border}`, borderRadius: C.radius, overflow: "hidden", ...style }}>{children}</div>;
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <div style={{ fontSize: 11, fontWeight: 600, color: C.label, letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 14 }}>{children}</div>;
}

/** Exposure heatmap — shows per-symbol directional exposure */
function ExposureHeatmap({ trades }: { trades: Trade[] }) {
  const open = trades.filter(t => t.status === "OPEN" || t.status === "PARTIAL");

  const exposure: Record<string, { long: number; short: number }> = {};
  for (const pos of open) {
    const sym = pos.symbol;
    const dir = /buy|long/i.test(pos.direction) ? "long" : "short";
    if (!exposure[sym]) exposure[sym] = { long: 0, short: 0 };
    exposure[sym][dir] += Number(pos.lot_size ?? 1);
  }

  const symbols = Object.keys(exposure).sort();
  const maxCount = Math.max(1, ...symbols.map(s => exposure[s].long + exposure[s].short));

  return (
    <Card>
      <div style={{ padding: "16px 20px" }}>
        <SectionLabel>Exposure Heatmap</SectionLabel>
        {symbols.length === 0 ? (
          <div style={{ fontSize: 12, color: C.textDim, textAlign: "center", padding: "12px 0" }}>No open positions</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {/* Header row */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 70px 70px 50px", gap: 8, fontSize: 10, color: C.label, letterSpacing: 0.4, textTransform: "uppercase", paddingBottom: 6, borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
              <span>Symbol</span><span style={{ textAlign: "right" }}>Long</span><span style={{ textAlign: "right" }}>Short</span><span style={{ textAlign: "right" }}>Net</span>
            </div>
            {symbols.map(sym => {
              const { long, short } = exposure[sym];
              const net = long - short;
              const longPct  = (long  / maxCount) * 100;
              const shortPct = (short / maxCount) * 100;
              return (
                <div key={sym}>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 70px 70px 50px", gap: 8, marginBottom: 4, alignItems: "center" }}>
                    <span style={{ fontSize: 13, fontWeight: 600, color: "#E8EAED" }}>{sym}</span>
                    <span style={{ fontSize: 12, fontFamily: MONO, color: C.positive, textAlign: "right" }}>{long.toFixed(2)}</span>
                    <span style={{ fontSize: 12, fontFamily: MONO, color: C.negative, textAlign: "right" }}>{short.toFixed(2)}</span>
                    <span style={{ fontSize: 12, fontFamily: MONO, color: net > 0 ? C.positive : net < 0 ? C.negative : C.textMid, textAlign: "right", fontWeight: 600 }}>
                      {net > 0 ? `+${net.toFixed(2)}` : net < 0 ? net.toFixed(2) : "—"}
                    </span>
                  </div>
                  {/* Bar */}
                  <div style={{ display: "flex", gap: 3, height: 5 }}>
                    <div style={{ flex: longPct,  maxWidth: `${longPct}%`,  background: C.positive + "40", borderRadius: 2 }} />
                    <div style={{ flex: shortPct, maxWidth: `${shortPct}%`, background: C.negative + "40", borderRadius: 2 }} />
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
}

/** Blocked signals list from agent events */
function BlockedSignals({ events }: { events: AgentEvent[] }) {
  const blocked = useMemo(() => {
    const result: AgentEvent[] = [];
    for (const ev of events) {
      const msg = ev.message ?? ev.msg ?? "";
      if ((ev.agent === "risk" || ev.agent === "execution") && /block|reject|guard/i.test(msg)) {
        result.push(ev);
      }
    }
    return result.slice(0, 10);
  }, [events]);

  return (
    <Card>
      <div style={{ padding: "16px 20px" }}>
        <SectionLabel>Blocked Signals</SectionLabel>
        {blocked.length === 0 ? (
          <div style={{ fontSize: 12, color: C.textDim, textAlign: "center", padding: "12px 0" }}>No blocked signals</div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {blocked.map((ev, i) => {
              const msg = ev.message ?? ev.msg ?? "";
              // Extract reason
              const reasonMatch = msg.match(/(?:guard|block|reject)[:\s]+([^.]{3,80})/i);
              const reason = reasonMatch?.[1]?.trim() || msg.slice(0, 60);
              const symbolMatch = msg.match(/\b([A-Z]{3,6}(?:\/[A-Z]{3})?)\b/);
              return (
                <div key={ev.id ?? i} style={{
                  display: "flex", alignItems: "flex-start", gap: 10,
                  padding: "10px 12px",
                  background: "rgba(255,69,58,0.06)",
                  border: "1px solid rgba(255,69,58,0.18)",
                  borderRadius: 8,
                }}>
                  <span style={{ fontSize: 14, color: C.negative, flexShrink: 0, marginTop: 1 }}>⊘</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                      <span style={{ fontSize: 12, fontWeight: 600, color: "#E8EAED" }}>
                        {symbolMatch ? symbolMatch[1] : "Signal"}
                      </span>
                      <span style={{ fontSize: 11, color: C.textDim, fontFamily: MONO }}>
                        {relAge(ev.created_at)}
                      </span>
                    </div>
                    <div style={{ fontSize: 11, color: C.negative, lineHeight: 1.4 }}>{reason}</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
}

/** Crucix status card */
function CrucixCard({ events }: { events: AgentEvent[] }) {
  // Find latest risk tier from crucix events
  const latestCrucix = events.find(e => e.agent === "crucix");
  const msg = latestCrucix ? (latestCrucix.message ?? latestCrucix.msg ?? "") : "";

  // Determine tier
  let tier: "CLEAR" | "ROUTINE" | "PRIORITY" | "FLASH" = "ROUTINE";
  let tierColor = C.cyan;
  if (/flash/i.test(msg)) { tier = "FLASH"; tierColor = C.negative; }
  else if (/priority|crisis|elevated/i.test(msg)) { tier = "PRIORITY"; tierColor = C.warning; }
  else if (/clear|safe/i.test(msg)) { tier = "CLEAR"; tierColor = C.positive; }

  const isBlackout = tier === "FLASH";

  return (
    <Card>
      <div style={{ padding: "16px 20px" }}>
        <SectionLabel>Crucix Risk Tier</SectionLabel>

        {/* Blackout banner */}
        {isBlackout && (
          <div style={{
            marginBottom: 12, padding: "8px 12px", borderRadius: 8,
            background: "rgba(255,69,58,0.15)", border: "1px solid rgba(255,69,58,0.35)",
            display: "flex", alignItems: "center", gap: 8,
          }}>
            <span style={{ fontSize: 14, color: C.negative }}>⚠</span>
            <span style={{ fontSize: 12, fontWeight: 600, color: C.negative }}>MACRO BLACKOUT — NO NEW TRADES</span>
          </div>
        )}

        {/* Tier badge */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
          <div style={{
            width: 52, height: 52, borderRadius: 12,
            background: tierColor + "15",
            border: `1.5px solid ${tierColor}40`,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 10, fontWeight: 800, color: tierColor,
            letterSpacing: 0.5, textAlign: "center",
          }}>
            {tier}
          </div>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: tierColor }}>{tier}</div>
            <div style={{ fontSize: 11, color: C.textDim }}>Risk Tier</div>
          </div>
        </div>

        {/* Lot scale */}
        {[
          { label: "Lot Scale", value: isBlackout ? "0%" : "100%", color: isBlackout ? C.negative : C.positive },
          { label: "Status", value: isBlackout ? "Blackout" : "Active", color: isBlackout ? C.negative : C.positive },
          { label: "Last Sweep", value: latestCrucix ? relAge(latestCrucix.created_at) : "—", color: C.textMid },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "7px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
            <span style={{ fontSize: 12, color: C.textMid }}>{label}</span>
            <span style={{ fontSize: 12, fontFamily: MONO, fontWeight: 600, color }}>{value}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function RiskPage() {
  const { status: shellStatus } = useAppShell();
  const [riskData,  setRiskData]  = useState<RiskData>({});
  const [trades,    setTrades]    = useState<Trade[]>([]);
  const [events,    setEvents]    = useState<AgentEvent[]>([]);
  const [loadingRd, setLoadingRd] = useState(true);
  const [loadingTr, setLoadingTr] = useState(true);

  // Fetch risk data
  const loadRisk = useCallback(async () => {
    setLoadingRd(true);
    try {
      const r = await fetch("/api/risk");
      if (r.ok) setRiskData(await r.json());
    } catch { /* silent */ }
    finally { setLoadingRd(false); }
  }, []);

  // Fetch trades for exposure
  const loadTrades = useCallback(async () => {
    setLoadingTr(true);
    try {
      const r = await fetch("/api/trades");
      const d = await r.json();
      setTrades(Array.isArray(d) ? d : (d.trades ?? []));
    } catch { /* silent */ }
    finally { setLoadingTr(false); }
  }, []);

  // Fetch events for blocked signals
  const loadEvents = useCallback(async () => {
    try {
      const r = await fetch("/api/events?limit=80");
      const d = await r.json();
      setEvents(Array.isArray(d) ? d : (d.events ?? []));
    } catch { /* silent */ }
  }, []);

  useEffect(() => {
    loadRisk(); loadTrades(); loadEvents();
    const id = setInterval(() => { loadRisk(); loadTrades(); loadEvents(); }, 15_000);
    return () => clearInterval(id);
  }, [loadRisk, loadTrades, loadEvents]);

  const equity    = Number(shellStatus?.equity    ?? 0);
  const balance   = Number(shellStatus?.balance   ?? 0);
  const dailyPnl  = Number(shellStatus?.daily_pnl ?? 0);
  const dailyPct = equity > 0 ? (dailyPnl / equity) * 100 : 0;

  const loading = loadingRd && loadingTr;

  const dailyBar   = limitBar(Math.abs(dailyPnl), riskData.max_daily_loss ?? 500);
  const tradCntBar = limitBar(trades.filter(t => t.status !== "CLOSED").length, riskData.max_concurrent_trades ?? 10);

  const card: React.CSSProperties = { background: C.bg, border: `1px solid ${C.border}`, borderRadius: C.radius };
  const sectionLabel: React.CSSProperties = { fontSize: 11, fontWeight: 600, color: C.label, letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 16 };

  return (
    <>
      {/* Emergency banner */}
      {riskData.emergency_stop && (
        <div style={{
          marginBottom: 20, padding: "14px 20px", borderRadius: 12,
          background: "rgba(255,59,48,0.12)", border: "1px solid rgba(255,59,48,0.35)",
          display: "flex", alignItems: "center", gap: 12,
        }}>
          <span style={{ fontSize: 18, fontFamily: "Material Symbols Outlined", color: C.negative }}>emergency</span>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: C.negative, letterSpacing: -0.2 }}>EMERGENCY STOP ACTIVE</div>
            {riskData.emergency_reason && (
              <div style={{ fontSize: 12, color: C.textMid, marginTop: 2 }}>{riskData.emergency_reason}</div>
            )}
          </div>
        </div>
      )}

      {/* KPI row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(160px, 1fr))", gap: 12, marginBottom: 20 }}>
        {[
          { label: "Equity", value: fmtUsd(equity), color: equity >= balance ? C.positive : C.negative },
          { label: "Balance", value: fmtUsd(balance), color: "#E8EAED" },
          { label: "Daily P&L", value: fmtUsd(dailyPnl), color: dailyPnl >= 0 ? C.positive : C.negative },
          { label: "Daily %", value: fmtPct(dailyPct), color: dailyPnl >= 0 ? C.positive : C.negative },
        ].map(({ label, value, color }) => (
          <div key={label} style={{ ...card, padding: "18px 20px" }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: C.label, letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 6 }}>{label}</div>
            <div style={{ fontSize: 20, fontWeight: 700, color, fontFamily: MONO, letterSpacing: -0.5 }}>{value}</div>
          </div>
        ))}
      </div>

      {/* Daily loss limit + exposure heatmap */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
        {/* Daily loss limit */}
        <Card>
          <div style={{ padding: "20px" }}>
            <SectionLabel>Daily Loss Limit</SectionLabel>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <span style={{ fontSize: 22, fontWeight: 700, color: pnlColor(dailyPnl), fontFamily: MONO }}>
                {fmtUsd(dailyPnl)}
              </span>
              <span style={{ fontSize: 13, color: C.textMid, fontFamily: MONO, alignSelf: "flex-end", marginBottom: 2 }}>
                / {fmtUsd(riskData.max_daily_loss)}
              </span>
            </div>
            <div style={{ height: 8, background: "rgba(255,255,255,0.06)", borderRadius: 4, overflow: "hidden", marginBottom: 8 }}>
              <div style={{ height: "100%", width: `${dailyBar.used}%`, background: dailyBar.color, borderRadius: 4, transition: "width .3s" }} />
            </div>
            <div style={{ fontSize: 11, color: C.textDim, fontFamily: MONO }}>
              {dailyBar.used.toFixed(1)}% of daily limit
            </div>
          </div>
        </Card>

        {/* Open positions gauge */}
        <Card>
          <div style={{ padding: "20px" }}>
            <SectionLabel>Open Positions</SectionLabel>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <span style={{ fontSize: 40, fontWeight: 700, color: C.cyan, fontFamily: MONO, lineHeight: 1 }}>
                {trades.filter(t => t.status !== "CLOSED").length}
              </span>
              <span style={{ fontSize: 13, color: C.textMid, fontFamily: MONO, alignSelf: "flex-end", marginBottom: 6 }}>
                / {riskData.max_concurrent_trades ?? "—"} allowed
              </span>
            </div>
            <div style={{ height: 8, background: "rgba(255,255,255,0.06)", borderRadius: 4, overflow: "hidden", marginBottom: 8 }}>
              <div style={{ height: "100%", width: `${tradCntBar.used}%`, background: tradCntBar.color, borderRadius: 4, transition: "width .3s" }} />
            </div>
            <div style={{ fontSize: 11, color: C.textDim, fontFamily: MONO }}>
              {tradCntBar.used.toFixed(0)}% slot utilisation
            </div>
          </div>
        </Card>
      </div>

      {/* Exposure heatmap + blocked signals + Crucix */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 280px", gap: 16 }}>
        <ExposureHeatmap trades={trades} />
        <BlockedSignals events={events} />
        <CrucixCard events={events} />
      </div>

      {/* Position sizing + WFO */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 16 }}>
        <Card>
          <div style={{ padding: "20px" }}>
            <SectionLabel>Position Sizing</SectionLabel>
            {[
              { label: "Risk per Trade", value: riskData.risk_per_trade_pct != null ? `${riskData.risk_per_trade_pct.toFixed(2)}%` : "—" },
              { label: "Max Lot Size", value: riskData.max_lot_size != null ? String(riskData.max_lot_size) : "—" },
              { label: "Max Concurrent Trades", value: riskData.max_concurrent_trades != null ? String(riskData.max_concurrent_trades) : "—" },
            ].map(({ label, value }) => (
              <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                <span style={{ fontSize: 12, color: C.textMid }}>{label}</span>
                <span style={{ fontSize: 14, fontWeight: 600, color: "#E8EAED", fontFamily: MONO }}>{value}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card>
          <div style={{ padding: "20px" }}>
            <SectionLabel>Walk-Forward Optimisation</SectionLabel>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
              <div style={{
                width: 8, height: 8, borderRadius: "50%",
                background: riskData.wfo_enabled ? C.positive : C.textDim,
                boxShadow: riskData.wfo_enabled ? `0 0 6px ${C.positive}` : "none",
              }} />
              <span style={{ fontSize: 14, fontWeight: 600, color: riskData.wfo_enabled ? C.positive : C.textMid }}>
                {riskData.wfo_enabled ? "Enabled" : "Disabled"}
              </span>
            </div>
            {[
              { label: "Retrain Period", value: riskData.wfo_period != null ? `${riskData.wfo_period}d` : "—" },
              { label: "Last Retrain",   value: relTime(riskData.last_retrain) },
            ].map(({ label, value }) => (
              <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "10px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                <span style={{ fontSize: 12, color: C.textMid }}>{label}</span>
                <span style={{ fontSize: 13, fontWeight: 600, color: "#E8EAED", fontFamily: MONO }}>{value}</span>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </>
  );
}

function fmtPct(v: number): string {
  return (v >= 0 ? "+" : "") + v.toFixed(2) + "%";
}
