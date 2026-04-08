import React, { useCallback, useEffect, useMemo, useState } from "react";
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

// ── Design Tokens ─────────────────────────────────────────────────────────────
const C = {
  bg:        "var(--bg-2)",
  border:    "var(--border)",
  radius:    6,
  mono:      "var(--font-mono)",
  label:     "var(--text-3)",
  positive:  "var(--gold)",
  negative:  "var(--red)",
  warning:   "var(--orange)",
  accent:    "var(--cyan)",
  textDim:   "var(--text-3)",
  textMid:   "var(--text-2)",
};

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtUsd(v?: number): string {
  if (v == null || isNaN(v)) return "—";
  const f = Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (v < 0 ? "-$" : "$") + f;
}

function pnlColor(v?: number): string {
  if (v == null) return C.textDim;
  return v > 0 ? C.positive : v < 0 ? C.negative : C.textDim;
}

function limitBar(value: number, max: number): { used: number; color: string } {
  const pct  = max !== 0 ? Math.min(Math.abs(value / max), 1) * 100 : 0;
  const color = pct > 90 ? C.negative : pct > 60 ? C.warning : C.positive;
  return { used: pct, color };
}

function relTime(iso?: string): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  const h   = Math.floor(ms / 3_600_000);
  if (h < 1)  return `${Math.floor(ms / 60_000)}m ago`;
  if (h < 24) return `${h}h ago`;
  return `${Math.floor(h / 24)}d ago`;
}

function relAge(ts?: string): string {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 3_600_000)   return Math.floor(ms / 60_000)        + "m";
  if (ms < 86_400_000)  return Math.floor(ms / 3_600_000)     + "h";
  return                           Math.floor(ms / 86_400_000) + "d";
}

function fmtPct(v: number): string {
  return (v >= 0 ? "+" : "") + v.toFixed(2) + "%";
}

// ── Sub-components ────────────────────────────────────────────────────────────

function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div
      style={{
        background: C.bg,
        border:     `1px solid ${C.border}`,
        borderRadius: C.radius,
        overflow: "hidden",
        ...style,
      }}
    >
      {children}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontSize:     11,
        fontWeight:    700,
        color:         C.label,
        letterSpacing: 0.5,
        textTransform: "uppercase",
        marginBottom:  14,
      }}
    >
      {children}
    </div>
  );
}

function SectionRow({ children, label }: { children: React.ReactNode; label: string }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <SectionLabel>{label}</SectionLabel>
      {children}
    </div>
  );
}

// ── Exposure Heatmap ──────────────────────────────────────────────────────────
function ExposureHeatmap({ trades }: { trades: Trade[] }) {
  const open = trades.filter(t => t.status === "OPEN" || t.status === "PARTIAL");

  const exposure: Record<string, { long: number; short: number }> = {};
  for (const pos of open) {
    const sym = pos.symbol;
    const dir = /buy|long/i.test(pos.direction) ? "long" : "short";
    if (!exposure[sym]) exposure[sym] = { long: 0, short: 0 };
    exposure[sym][dir] += Number(pos.lot_size ?? 1);
  }

  const symbols  = Object.keys(exposure).sort();
  const maxCount = Math.max(1, ...symbols.map(s => exposure[s].long + exposure[s].short));

  return (
    <Card>
      <div style={{ padding: "20px" }}>
        <SectionLabel>Exposure Heatmap</SectionLabel>
        {symbols.length === 0 ? (
          <div style={{ fontSize: 12, color: C.textDim, textAlign: "center", padding: "16px 0" }}>
            No open positions
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {/* Header */}
            <div
              style={{
                display:              "grid",
                gridTemplateColumns:  "1fr 64px 64px 48px",
                gap:                  8,
                fontSize:             10,
                color:                C.label,
                letterSpacing:        0.4,
                textTransform:        "uppercase",
                paddingBottom:        6,
                borderBottom:         `1px solid ${C.border}`,
              }}
            >
              <span>Symbol</span>
              <span style={{ textAlign: "right" }}>Long</span>
              <span style={{ textAlign: "right" }}>Short</span>
              <span style={{ textAlign: "right" }}>Net</span>
            </div>
            {symbols.map(sym => {
              const { long, short } = exposure[sym];
              const net      = long - short;
              const longPct  = (long  / maxCount) * 100;
              const shortPct = (short / maxCount) * 100;
              return (
                <div key={sym}>
                  <div
                    style={{
                      display:              "grid",
                      gridTemplateColumns:  "1fr 64px 64px 48px",
                      gap:                  8,
                      marginBottom:         5,
                      alignItems:            "center",
                    }}
                  >
                    <span style={{ fontSize: 13, fontWeight: 600, color: "var(--text-1)" }}>{sym}</span>
                    <span style={{ fontSize: 12, fontFamily: C.mono, color: C.positive, textAlign: "right" }}>
                      {long.toFixed(2)}
                    </span>
                    <span style={{ fontSize: 12, fontFamily: C.mono, color: C.negative, textAlign: "right" }}>
                      {short.toFixed(2)}
                    </span>
                    <span
                      style={{
                        fontSize:   12,
                        fontFamily: C.mono,
                        fontWeight: 600,
                        color:      net > 0 ? C.positive : net < 0 ? C.negative : C.textMid,
                        textAlign:  "right",
                      }}
                    >
                      {net > 0 ? `+${net.toFixed(2)}` : net < 0 ? net.toFixed(2) : "—"}
                    </span>
                  </div>
                  {/* Bar */}
                  <div style={{ display: "flex", gap: 3, height: 5 }}>
                    <div
                      style={{
                        flex:        longPct,
                        maxWidth:    `${longPct}%`,
                        background:  C.positive + "40",
                        borderRadius: 2,
                      }}
                    />
                    <div
                      style={{
                        flex:        shortPct,
                        maxWidth:    `${shortPct}%`,
                        background:  C.negative + "40",
                        borderRadius: 2,
                      }}
                    />
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

// ── Blocked Signals ────────────────────────────────────────────────────────────
function BlockedSignals({ events }: { events: AgentEvent[] }) {
  const blocked = useMemo(() => {
    const result: AgentEvent[] = [];
    for (const ev of events) {
      const msg = ev.message ?? ev.msg ?? "";
      if ((ev.agent === "risk" || ev.agent === "execution") && /block|reject|guard/i.test(msg)) {
        result.push(ev);
      }
    }
    return result.slice(0, 8);
  }, [events]);

  return (
    <Card>
      <div style={{ padding: "20px" }}>
        <SectionLabel>Blocked Signals</SectionLabel>
        {blocked.length === 0 ? (
          <div style={{ fontSize: 12, color: C.textDim, textAlign: "center", padding: "16px 0" }}>
            No blocked signals
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {blocked.map((ev, i) => {
              const msg         = ev.message ?? ev.msg ?? "";
              const reasonMatch = msg.match(/(?:guard|block|reject)[:\s]+([^.]{3,80})/i);
              const reason      = reasonMatch?.[1]?.trim() || msg.slice(0, 60);
              const symbolMatch = msg.match(/\b([A-Z]{3,6}(?:\/[A-Z]{3})?)\b/);
              return (
                <div
                  key={ev.id ?? i}
                  style={{
                    display:        "flex",
                    alignItems:     "flex-start",
                    gap:            10,
                    padding:        "10px 12px",
                    background:     "rgba(239,68,68,0.06)",
                    border:         "1px solid rgba(239,68,68,0.18)",
                    borderRadius:    8,
                  }}
                >
                  <span style={{ fontSize: 14, color: C.negative, flexShrink: 0, marginTop: 1 }}>⊘</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        display:        "flex",
                        justifyContent:  "space-between",
                        marginBottom:    3,
                      }}
                    >
                      <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-1)" }}>
                        {symbolMatch ? symbolMatch[1] : "Signal"}
                      </span>
                      <span style={{ fontSize: 11, color: C.textDim, fontFamily: C.mono }}>
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

// ── Crucix Card ────────────────────────────────────────────────────────────────
function CrucixCard({ events }: { events: AgentEvent[] }) {
  const latestCrucix = events.find(e => e.agent === "crucix");
  const msg          = latestCrucix ? (latestCrucix.message ?? latestCrucix.msg ?? "") : "";

  let tier: "CLEAR" | "ROUTINE" | "PRIORITY" | "FLASH" = "ROUTINE";
  let tierColor = C.accent;
  if (/flash/i.test(msg))                              { tier = "FLASH";   tierColor = C.negative; }
  else if (/priority|crisis|elevated/i.test(msg))      { tier = "PRIORITY"; tierColor = C.warning;  }
  else if (/clear|safe/i.test(msg))                    { tier = "CLEAR";   tierColor = C.positive; }

  const isBlackout = tier === "FLASH";

  return (
    <Card>
      <div style={{ padding: "20px" }}>
        <SectionLabel>Crucix Risk Tier</SectionLabel>

        {isBlackout && (
          <div
            style={{
              marginBottom: 12,
              padding:     "8px 12px",
              borderRadius: 8,
              background:  "rgba(239,68,68,0.15)",
              border:       "1px solid rgba(239,68,68,0.35)",
              display:     "flex",
              alignItems:   "center",
              gap:          8,
            }}
          >
            <span style={{ fontSize: 14, color: C.negative }}>⚠</span>
            <span style={{ fontSize: 12, fontWeight: 600, color: C.negative }}>
              MACRO BLACKOUT — NO NEW TRADES
            </span>
          </div>
        )}

        <div style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 16 }}>
          <div
            style={{
              width:        52,
              height:       52,
              borderRadius: 12,
              background:   tierColor + "15",
              border:       `1.5px solid ${tierColor}40`,
              display:      "flex",
              alignItems:   "center",
              justifyContent: "center",
              fontSize:     10,
              fontWeight:   800,
              color:        tierColor,
              letterSpacing: 0.5,
              textAlign:    "center",
              flexShrink:   0,
            }}
          >
            {tier}
          </div>
          <div>
            <div style={{ fontSize: 18, fontWeight: 700, color: tierColor }}>{tier}</div>
            <div style={{ fontSize: 11, color: C.textDim }}>Risk Tier</div>
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
          {[
            { label: "Lot Scale",    value: isBlackout ? "0%"     : "100%",   color: isBlackout ? C.negative : C.positive },
            { label: "Status",       value: isBlackout ? "Blackout" : "Active", color: isBlackout ? C.negative : C.positive },
            { label: "Last Sweep",   value: latestCrucix ? relAge(latestCrucix.created_at) : "—", color: C.textMid },
          ].map(({ label, value, color }) => (
            <div
              key={label}
              style={{
                display:        "flex",
                justifyContent: "space-between",
                padding:        "9px 0",
                borderBottom:   "1px solid rgba(255,255,255,0.04)",
              }}
            >
              <span style={{ fontSize: 12, color: C.textMid }}>{label}</span>
              <span style={{ fontSize: 12, fontFamily: C.mono, fontWeight: 600, color }}>{value}</span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function RiskPage() {
  const { status: shellStatus } = useAppShell();
  const [riskData, setRiskData] = useState<RiskData>({});
  const [trades,   setTrades]   = useState<Trade[]>([]);
  const [events,   setEvents]   = useState<AgentEvent[]>([]);
  const [loadingRd, setLoadingRd] = useState(true);
  const [loadingTr, setLoadingTr] = useState(true);

  const loadRisk = useCallback(async () => {
    setLoadingRd(true);
    try {
      const r = await fetch("/api/risk");
      if (r.ok) setRiskData(await r.json());
    } catch { /* silent */ }
    finally    { setLoadingRd(false); }
  }, []);

  const loadTrades = useCallback(async () => {
    setLoadingTr(true);
    try {
      const r  = await fetch("/api/trades");
      const d  = await r.json();
      setTrades(Array.isArray(d) ? d : (d.trades ?? []));
    } catch { /* silent */ }
    finally    { setLoadingTr(false); }
  }, []);

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
  const dailyPct  = equity > 0 ? (dailyPnl / equity) * 100 : 0;

  const dailyBar    = limitBar(Math.abs(dailyPnl), riskData.max_daily_loss ?? 500);
  const tradCntBar  = limitBar(trades.filter(t => t.status !== "CLOSED").length, riskData.max_concurrent_trades ?? 10);
  const openCount   = trades.filter(t => t.status !== "CLOSED").length;

  return (
    <div style={{ padding: "24px", maxWidth: 1400, margin: "0 auto", display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Emergency banner */}
      {riskData.emergency_stop && (
        <div
          style={{
            padding:     "14px 20px",
            borderRadius: 8,
            background:  "rgba(239,68,68,0.10)",
            border:       "1px solid rgba(239,68,68,0.30)",
            display:     "flex",
            alignItems:  "center",
            gap:         12,
          }}
        >
          <span style={{ fontSize: 18, color: C.negative }}>emergency</span>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: C.negative, letterSpacing: -0.2 }}>
              EMERGENCY STOP ACTIVE
            </div>
            {riskData.emergency_reason && (
              <div style={{ fontSize: 12, color: C.textMid, marginTop: 2 }}>
                {riskData.emergency_reason}
              </div>
            )}
          </div>
        </div>
      )}

      {/* KPI row */}
      <div
        style={{
          display:               "grid",
          gridTemplateColumns:  "repeat(auto-fill, minmax(160px, 1fr))",
          gap:                   14,
        }}
      >
        {[
          { label: "Equity",     value: fmtUsd(equity),    color: equity >= balance ? C.positive : C.negative },
          { label: "Balance",    value: fmtUsd(balance),   color: "var(--text-1)" },
          { label: "Daily P&L", value: fmtUsd(dailyPnl),  color: dailyPnl >= 0 ? C.positive : C.negative },
          { label: "Daily %",   value: fmtPct(dailyPct), color: dailyPnl >= 0 ? C.positive : C.negative },
        ].map(({ label, value, color }) => (
          <div
            key={label}
            style={{
              background: C.bg,
              border:     `1px solid ${C.border}`,
              borderRadius: C.radius,
              padding:    "16px 18px",
            }}
          >
            <div
              style={{
                fontSize:     11,
                fontWeight:   700,
                color:        C.label,
                letterSpacing: 0.5,
                textTransform: "uppercase",
                marginBottom:  6,
              }}
            >
              {label}
            </div>
            <div
              style={{
                fontSize:   20,
                fontWeight:  700,
                color,
                fontFamily: C.mono,
                letterSpacing: "-0.5px",
              }}
            >
              {value}
            </div>
          </div>
        ))}
      </div>

      {/* Daily loss limit + Open positions */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap:    16,
        }}
      >
        <Card>
          <div style={{ padding: "20px" }}>
            <SectionLabel>Daily Loss Limit</SectionLabel>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <span style={{ fontSize: 22, fontWeight: 700, color: pnlColor(dailyPnl), fontFamily: C.mono }}>
                {fmtUsd(dailyPnl)}
              </span>
              <span style={{ fontSize: 13, color: C.textMid, fontFamily: C.mono, alignSelf: "flex-end", marginBottom: 2 }}>
                / {fmtUsd(riskData.max_daily_loss)}
              </span>
            </div>
            <div
              style={{
                height:     8,
                background: "var(--bg-3)",
                borderRadius: 4,
                overflow:   "hidden",
                marginBottom: 8,
              }}
            >
              <div
                style={{
                  height:       "100%",
                  width:        `${dailyBar.used}%`,
                  background:   dailyBar.color,
                  borderRadius: 4,
                  transition:   "width .3s",
                }}
              />
            </div>
            <div style={{ fontSize: 11, color: C.textDim, fontFamily: C.mono }}>
              {dailyBar.used.toFixed(1)}% of daily limit
            </div>
          </div>
        </Card>

        <Card>
          <div style={{ padding: "20px" }}>
            <SectionLabel>Open Positions</SectionLabel>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
              <span
                style={{
                  fontSize:   40,
                  fontWeight: 700,
                  color:      C.accent,
                  fontFamily: C.mono,
                  lineHeight: 1,
                }}
              >
                {openCount}
              </span>
              <span
                style={{
                  fontSize:   13,
                  color:      C.textMid,
                  fontFamily: C.mono,
                  alignSelf:  "flex-end",
                  marginBottom: 6,
                }}
              >
                / {riskData.max_concurrent_trades ?? "—"} allowed
              </span>
            </div>
            <div
              style={{
                height:     8,
                background: "var(--bg-3)",
                borderRadius: 4,
                overflow:   "hidden",
                marginBottom: 8,
              }}
            >
              <div
                style={{
                  height:       "100%",
                  width:        `${tradCntBar.used}%`,
                  background:   tradCntBar.color,
                  borderRadius: 4,
                  transition:   "width .3s",
                }}
              />
            </div>
            <div style={{ fontSize: 11, color: C.textDim, fontFamily: C.mono }}>
              {tradCntBar.used.toFixed(0)}% slot utilisation
            </div>
          </div>
        </Card>
      </div>

      {/* Exposure heatmap + Blocked + Crucix */}
      <div
        style={{
          display:               "grid",
          gridTemplateColumns:  "1fr 1fr 300px",
          gap:                    16,
        }}
      >
        <ExposureHeatmap trades={trades} />
        <BlockedSignals  events={events} />
        <CrucixCard      events={events} />
      </div>

      {/* Position sizing + WFO */}
      <div
        style={{
          display:               "grid",
          gridTemplateColumns:    "1fr 1fr",
          gap:                    16,
        }}
      >
        <Card>
          <div style={{ padding: "20px" }}>
            <SectionLabel>Position Sizing</SectionLabel>
            <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
              {[
                { label: "Risk per Trade",      value: riskData.risk_per_trade_pct != null ? `${riskData.risk_per_trade_pct.toFixed(2)}%`  : "—" },
                { label: "Max Lot Size",        value: riskData.max_lot_size != null          ? String(riskData.max_lot_size)              : "—" },
                { label: "Max Concurrent Trades", value: riskData.max_concurrent_trades != null ? String(riskData.max_concurrent_trades) : "—" },
              ].map(({ label, value }) => (
                <div
                  key={label}
                  style={{
                    display:        "flex",
                    justifyContent: "space-between",
                    alignItems:     "center",
                    padding:        "10px 0",
                    borderBottom:   "1px solid rgba(255,255,255,0.04)",
                  }}
                >
                  <span style={{ fontSize: 12, color: C.textMid }}>{label}</span>
                  <span
                    style={{
                      fontSize:   14,
                      fontWeight: 600,
                      color:      "var(--text-1)",
                      fontFamily: C.mono,
                    }}
                  >
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Card>

        <Card>
          <div style={{ padding: "20px" }}>
            <SectionLabel>Walk-Forward Optimisation</SectionLabel>
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
              <div
                style={{
                  width:        8,
                  height:       8,
                  borderRadius: "50%",
                  background:   riskData.wfo_enabled ? C.positive : C.textDim,
                  boxShadow:    riskData.wfo_enabled ? `0 0 6px ${C.positive}` : "none",
                }}
              />
              <span
                style={{
                  fontSize:   14,
                  fontWeight: 600,
                  color:      riskData.wfo_enabled ? C.positive : C.textMid,
                }}
              >
                {riskData.wfo_enabled ? "Enabled" : "Disabled"}
              </span>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>
              {[
                { label: "Retrain Period", value: riskData.wfo_period != null ? `${riskData.wfo_period}d`   : "—" },
                { label: "Last Retrain",   value: relTime(riskData.last_retrain) },
              ].map(({ label, value }) => (
                <div
                  key={label}
                  style={{
                    display:        "flex",
                    justifyContent: "space-between",
                    alignItems:     "center",
                    padding:        "10px 0",
                    borderBottom:   "1px solid rgba(255,255,255,0.04)",
                  }}
                >
                  <span style={{ fontSize: 12, color: C.textMid }}>{label}</span>
                  <span
                    style={{
                      fontSize:   13,
                      fontWeight: 600,
                      color:      "var(--text-1)",
                      fontFamily: C.mono,
                    }}
                  >
                    {value}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
