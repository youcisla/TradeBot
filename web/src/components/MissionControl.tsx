"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ConfirmModal from "@/components/ConfirmModal";
import { useAppShell } from "@/components/AppShell";

// ── Types ─────────────────────────────────────────────────────────────────────

interface AgentEvent {
  id?: number;
  agent: string;
  level: string;
  message?: string;
  msg?: string;
  created_at?: string;
  ts?: string;
  data?: Record<string, unknown>;
}

interface Trade {
  id: number;
  symbol: string;
  direction: string;
  entry_price: number;
  sl?: number;
  tp1?: number;
  tp2?: number;
  tp3?: number;
  tp4?: number;
  tp1_hit?: boolean;
  tp2_hit?: boolean;
  tp3_hit?: boolean;
  tp4_hit?: boolean;
  open_time?: string;
  pnl?: number;
  status: string;
}

interface SignalCandidate {
  agent: string;
  symbol?: string;
  direction?: string;
  confidence?: number;
  message?: string;
  created_at?: string;
}

// ── Agent config ───────────────────────────────────────────────────────────────

const AGENTS = [
  { key: "crucix",        label: "Crucix",    color: "var(--agent-crucix)" },
  { key: "market",        label: "Market",    color: "var(--agent-market)" },
  { key: "analysis",      label: "Analysis",  color: "var(--text-primary)" },
  { key: "strategy",      label: "Strategy",  color: "var(--agent-strategy)" },
  { key: "neural",        label: "Neural",    color: "var(--agent-neural)" },
  { key: "council",       label: "Council",   color: "var(--agent-council)" },
  { key: "risk",          label: "Risk",      color: "var(--agent-risk)" },
  { key: "execution",     label: "Execution", color: "var(--text-primary)" },
  { key: "trade_manager", label: "TradeMgr",  color: "var(--agent-trade-manager)" },
  { key: "learning",      label: "Learning",  color: "var(--agent-learning)" },
  { key: "model_manager", label: "Models",    color: "var(--agent-model-manager)" },
  { key: "logging",       label: "Logging",   color: "var(--text-muted)" },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtUsd(v: number): string {
  const abs = Math.abs(v);
  const f = abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (v < 0 ? "-$" : "$") + f;
}

function fmtPct(v: number): string {
  return (v >= 0 ? "+" : "") + v.toFixed(2) + "%";
}

function relTime(ts: string | undefined): string {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 60_000)  return Math.floor(ms / 1_000)    + "s ago";
  if (ms < 3_600_000) return Math.floor(ms / 60_000)   + "m ago";
  return                     Math.floor(ms / 3_600_000) + "h ago";
}

function tradeAge(ts: string | undefined): string {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 3_600_000)  return Math.floor(ms / 60_000)    + "m";
  if (ms < 86_400_000) return Math.floor(ms / 3_600_000) + "h";
  return                      Math.floor(ms / 86_400_000) + "d";
}

function ageMs(ts: string | undefined): number {
  if (!ts) return Infinity;
  return Date.now() - new Date(ts).getTime();
}

function evMsg(ev: AgentEvent): string {
  return ev?.message ?? ev?.msg ?? "";
}

function evTs(ev: AgentEvent): string | undefined {
  return ev?.created_at ?? ev?.ts;
}

function agentColor(key: string): string {
  return AGENTS.find(a => a.key === key)?.color ?? "var(--text-muted)";
}

function agentLabel(key: string): string {
  return AGENTS.find(a => a.key === key)?.label ?? key;
}

// ── Shared style tokens ────────────────────────────────────────────────────────

const C = {
  bg:       "var(--card-bg)",
  border:    "var(--card-border)",
  radius:    "var(--card-radius)",
  pad:       "var(--card-padding)",
  mono:      "var(--font-mono-stack)",
  label:     "var(--section-label)",
  text:      "var(--text-primary)",
  textDim:   "var(--text-muted)",
  textMid:   "var(--text-secondary)",
  positive:  "var(--buy)",
  negative:  "var(--sell)",
  warning:   "var(--health-warn)",
  accent:    "var(--accent)",
} as const;

// ── Sub-components ────────────────────────────────────────────────────────────

/** Confidence bar — shows 0–100% with tier coloring */
function ConfBar({ value, max = 100 }: { value: number; max?: number }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const color = pct >= 85 ? "var(--buy)" : pct >= 65 ? "var(--accent)" : pct >= 40 ? "var(--health-warn)" : "var(--sell)";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 4, background: "var(--surface-3)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 2, transition: "width .3s" }} />
      </div>
      <span style={{ fontSize: 11, fontFamily: C.mono, color, fontWeight: 600, minWidth: 32, textAlign: "right" }}>
        {pct.toFixed(0)}%
      </span>
    </div>
  );
}

/** Agent badge */
function AgentBadge({ agent }: { agent: string }) {
  const color = agentColor(agent);
  return (
    <span style={{
      fontSize: 9, fontWeight: 700, color: color,
      background: "var(--surface-2)", padding: "2px 6px", borderRadius: 4,
      letterSpacing: 0.4, textTransform: "uppercase", flexShrink: 0,
    }}>
      {agentLabel(agent)}
    </span>
  );
}

/** Severity dot */
function SevDot({ agent, ms }: { agent: string; ms: number }) {
  const fresh = ms < 60_000;
  const warm  = ms < 300_000;
  const color = agentColor(agent);
  return (
    <span style={{
      width: 7, height: 7, borderRadius: "50%", flexShrink: 0, display: "inline-block",
      background: fresh ? color : warm ? "var(--surface-3)" : "var(--border)",
      animation: fresh ? "dotPulse 1.8s ease-in-out infinite" : undefined,
    }} />
  );
}

/** Card wrapper */
function Card({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <div style={{
      background: C.bg, border: `1px solid ${C.border}`,
      borderRadius: C.radius, overflow: "hidden", ...style,
    }}>
      {children}
    </div>
  );
}

/** Section label */
function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={{
      fontSize: 11, fontWeight: 600, color: C.label,
      letterSpacing: 0.5, textTransform: "uppercase", marginBottom: 14,
    }}>
      {children}
    </div>
  );
}

// ── Health Strip ──────────────────────────────────────────────────────────────

function HealthStrip({ onPauseResume, onCloseAll, isRunning, cmdBusy }: {
  onPauseResume: () => void;
  onCloseAll: () => void;
  isRunning: boolean;
  cmdBusy: string | null;
}) {
  const { status } = useAppShell();

  const equity   = Number(status?.equity    ?? 0);
  const balance  = Number(status?.balance   ?? 0);
  const dailyPnl = Number(status?.daily_pnl ?? 0);
  const dailyPct = equity > 0 ? (dailyPnl / equity) * 100 : 0;
  const isBotRunning = status?.state === "running";

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 0,
      background: "var(--bg)",
      borderBottom: "1px solid var(--border)",
      height: 56, padding: "0 20px",
      position: "sticky", top: 0, zIndex: 50,
      flexShrink: 0,
    }}>
      {/* Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginRight: 24, flexShrink: 0 }}>
        <div style={{
          width: 10, height: 10, borderRadius: 2,
          background: "linear-gradient(135deg, var(--accent) 0%, var(--buy) 100%)",
          boxShadow: "0 0 8px var(--accent-glow)",
        }} />
        <span style={{ fontSize: 14, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "0.05em", textTransform: "uppercase" }}>
          PulseTrade
        </span>
      </div>

      {/* Bot state pill */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginRight: 20, flexShrink: 0 }}>
        <span style={{
          width: 8, height: 8, borderRadius: "50%",
          background: isBotRunning ? "var(--buy)" : "var(--sell)",
          display: "inline-block",
          animation: isBotRunning ? "dotPulse 1.8s ease-in-out infinite" : undefined,
        }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: isBotRunning ? "var(--buy)" : "var(--sell)", textTransform: "uppercase", letterSpacing: 0.5 }}>
          {isBotRunning ? "Running" : (status?.state ?? "Offline")}
        </span>
      </div>

      {/* Separator */}
      <div style={{ width: 1, height: 24, background: "var(--border)", marginRight: 20 }} />

      {/* Broker */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginRight: 16 }}>
        <span style={{ fontSize: 11, color: C.label, textTransform: "uppercase", letterSpacing: 0.4 }}>MT5</span>
        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--buy)" }}>Connected</span>
      </div>

      {/* DB */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginRight: 16 }}>
        <span style={{ fontSize: 11, color: C.label, textTransform: "uppercase", letterSpacing: 0.4 }}>DB</span>
        <span style={{ fontSize: 11, fontWeight: 600, color: "var(--buy)" }}>OK</span>
      </div>

      {/* Separator */}
      <div style={{ width: 1, height: 24, background: "var(--border)", marginRight: 20 }} />

      {/* Balance */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", marginRight: 20 }}>
        <span style={{ fontSize: 10, color: C.label, textTransform: "uppercase", letterSpacing: 0.4 }}>Balance</span>
        <span style={{ fontSize: 14, fontWeight: 700, fontFamily: C.mono, color: "var(--text-primary)" }}>
          {fmtUsd(balance)}
        </span>
      </div>

      {/* Equity */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", marginRight: 20 }}>
        <span style={{ fontSize: 10, color: C.label, textTransform: "uppercase", letterSpacing: 0.4 }}>Equity</span>
        <span style={{ fontSize: 14, fontWeight: 700, fontFamily: C.mono, color: equity >= balance ? "var(--buy)" : "var(--sell)" }}>
          {fmtUsd(equity)}
        </span>
      </div>

      {/* Daily PnL */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", marginRight: 20 }}>
        <span style={{ fontSize: 10, color: C.label, textTransform: "uppercase", letterSpacing: 0.4 }}>Daily P&L</span>
        <span style={{ fontSize: 14, fontWeight: 700, fontFamily: C.mono, color: dailyPnl >= 0 ? "var(--buy)" : "var(--sell)" }}>
          {fmtUsd(dailyPnl)} <span style={{ fontSize: 11, fontWeight: 400 }}>({fmtPct(dailyPct)})</span>
        </span>
      </div>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* Commands */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <button
          disabled={!!cmdBusy}
          onClick={onPauseResume}
          style={{
            height: 32, padding: "0 16px",
            background:   isRunning ? "rgba(255,159,10,0.12)" : "rgba(48,209,88,0.12)",
            border:       `1px solid ${isRunning ? "rgba(255,159,10,0.35)" : "rgba(48,209,88,0.35)"}`,
            borderRadius: 8, color: isRunning ? "var(--health-warn)" : "var(--buy)",
            fontSize: 12, fontWeight: 600, cursor: cmdBusy ? "not-allowed" : "pointer",
            fontFamily: "inherit", opacity: cmdBusy && cmdBusy !== (isRunning ? "pause" : "resume") ? 0.45 : 1,
            transition: "opacity .15s",
          }}
        >
          {cmdBusy === (isRunning ? "pause" : "resume") ? "…" : isRunning ? "Pause" : "Resume"}
        </button>

        <button
          disabled={!!cmdBusy}
          onClick={onCloseAll}
          style={{
            height: 32, padding: "0 16px",
            background: "rgba(255,69,58,0.10)", border: "1px solid rgba(255,69,58,0.35)",
            borderRadius: 8, color: "var(--sell)",
            fontSize: 12, fontWeight: 600, cursor: cmdBusy ? "not-allowed" : "pointer",
            fontFamily: "inherit", opacity: cmdBusy && cmdBusy !== "close_all" ? 0.45 : 1,
            transition: "opacity .15s",
          }}
        >
          {cmdBusy === "close_all" ? "…" : "Close All"}
        </button>
      </div>
    </div>
  );
}

// ── Live Positions ─────────────────────────────────────────────────────────────

function LivePositions({ positions }: { positions: Trade[] }) {
  const open = positions.filter(t => t.status === "OPEN" || t.status === "PARTIAL");

  return (
    <Card style={{ display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "16px 20px 12px" }}>
        <SectionLabel>Live Positions ({open.length})</SectionLabel>

        {open.length === 0 ? (
          <div style={{ fontSize: 13, color: C.textDim, textAlign: "center", padding: "24px 0" }}>
            No open positions
          </div>
        ) : (
          <>
            {/* Header */}
            <div style={{
              display: "grid", gridTemplateColumns: "1fr 44px 64px 56px 40px", gap: 6,
              fontSize: 10, color: C.label, letterSpacing: 0.4, textTransform: "uppercase",
              paddingBottom: 8, borderBottom: "1px solid var(--border)", marginBottom: 4,
            }}>
              <span>Symbol</span><span>Dir</span><span style={{ textAlign: "right" }}>Entry</span>
              <span style={{ textAlign: "right" }}>P&L</span><span style={{ textAlign: "right" }}>Age</span>
            </div>
            {/* Rows */}
            {open.slice(0, 6).map(pos => {
              const isLong = /buy|long/i.test(pos.direction);
              const pnl    = Number(pos.pnl ?? 0);
              const hasPnl = pos.pnl != null;
              return (
                <div key={pos.id} style={{
                  display: "grid", gridTemplateColumns: "1fr 44px 64px 56px 40px", gap: 6,
                  fontSize: 13, padding: "7px 0",
                  borderBottom: "1px solid var(--border-subtle)",
                  alignItems: "center",
                }}>
                  <span style={{ color: "var(--text-primary)", fontWeight: 600 }}>{pos.symbol}</span>
                  <span style={{ color: isLong ? "var(--buy)" : "var(--sell)", fontSize: 10, fontWeight: 700, letterSpacing: 0.3 }}>
                    {isLong ? "LONG" : "SHORT"}
                  </span>
                  <span style={{ color: "var(--text-secondary)", fontFamily: C.mono, fontSize: 11, textAlign: "right" }}>
                    {pos.entry_price.toFixed(5)}
                  </span>
                  <span style={{
                    fontFamily: C.mono, fontSize: 12, textAlign: "right", fontWeight: 700,
                    color: !hasPnl ? C.textDim : pnl > 0 ? "var(--buy)" : pnl < 0 ? "var(--sell)" : C.textMid,
                  }}>
                    {!hasPnl ? "—" : (pnl >= 0 ? "+" : "") + fmtUsd(pnl)}
                  </span>
                  <span style={{ color: C.textDim, fontSize: 11, textAlign: "right" }}>
                    {tradeAge(pos.open_time)}
                  </span>
                </div>
              );
            })}
            {open.length > 6 && (
              <div style={{ fontSize: 11, color: C.textDim, textAlign: "center", marginTop: 8 }}>
                +{open.length - 6} more
              </div>
            )}
          </>
        )}
      </div>
    </Card>
  );
}

// ── Exposure Heatmap ─────────────────────────────────────────────────────────

function ExposureHeatmap({ positions }: { positions: Trade[] }) {
  const open = positions.filter(t => t.status === "OPEN" || t.status === "PARTIAL");

  // Build exposure map
  const exposure: Record<string, { long: number; short: number }> = {};
  for (const pos of open) {
    const sym = pos.symbol;
    const dir = /buy|long/i.test(pos.direction) ? "long" : "short";
    if (!exposure[sym]) exposure[sym] = { long: 0, short: 0 };
    exposure[sym][dir]++;
  }

  const symbols = Object.keys(exposure).sort();
  const maxCount = Math.max(1, ...symbols.map(s => exposure[s].long + exposure[s].short));

  return (
    <Card style={{ marginTop: 16 }}>
      <div style={{ padding: "16px 20px" }}>
        <SectionLabel>Exposure</SectionLabel>

        {symbols.length === 0 ? (
          <div style={{ fontSize: 12, color: C.textDim, textAlign: "center", padding: "12px 0" }}>
            No open exposure
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {symbols.map(sym => {
              const { long, short } = exposure[sym];
              const total = long + short;
              const longPct  = (long  / maxCount) * 100;
              const shortPct = (short / maxCount) * 100;
              const net = long - short;
              return (
                <div key={sym}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 3 }}>
                    <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>{sym}</span>
                    <span style={{ fontSize: 11, fontFamily: C.mono, color: net > 0 ? "var(--buy)" : net < 0 ? "var(--sell)" : C.textMid }}>
                      {net > 0 ? `+${net}` : net < 0 ? `${net}` : "—"}
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: 3, height: 6 }}>
                    <div style={{ flex: longPct, maxWidth: `${longPct}%`, background: "rgba(34,197,94,0.25)", borderRadius: 2, transition: "width .3s" }} />
                    <div style={{ flex: shortPct, maxWidth: `${shortPct}%`, background: "rgba(239,68,68,0.25)", borderRadius: 2, transition: "width .3s" }} />
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

// ── Top Signals ───────────────────────────────────────────────────────────────

function TopSignals({ events }: { events: AgentEvent[] }) {
  // Extract signals from strategy_agent and council events
  const signals = useMemo(() => {
    const candidates: SignalCandidate[] = [];
    for (const ev of events) {
      const msg = evMsg(ev);
      const agent = (ev.agent ?? "").toLowerCase();
      if (agent === "strategy" || agent === "council" || agent === "risk") {
        candidates.push({
          agent,
          message: msg,
          created_at: evTs(ev),
          // Try to extract from message
          symbol: extractSymbol(msg),
          direction: extractDirection(msg),
          confidence: extractConfidence(msg),
        });
      }
    }
    return candidates.slice(0, 5);
  }, [events]);

  return (
    <Card>
      <div style={{ padding: "16px 20px" }}>
        <SectionLabel>Top Signals</SectionLabel>

        {signals.length === 0 ? (
          <div style={{ fontSize: 12, color: C.textDim, textAlign: "center", padding: "24px 0" }}>
            No recent signals
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {signals.map((sig, i) => {
              const conf = sig.confidence ?? 0;
              const agent = (sig.agent ?? "").toLowerCase();
              const riskEv = events.find(e => e.agent === "risk");
              const riskMsg = riskEv ? evMsg(riskEv) : "";
              const blocked = /block|reject|guard/i.test(riskMsg) || /block|reject/i.test(sig.message ?? "");

              return (
                <div key={i} style={{
                  background: "var(--surface-2)", borderRadius: 10,
                  border: `1px solid ${blocked ? "var(--sell)" : "var(--border)"}`,
                  padding: "10px 12px",
                }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      {sig.symbol && (
                        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>{sig.symbol}</span>
                      )}
                      {sig.direction && (
                        <span style={{
                          fontSize: 10, fontWeight: 700, letterSpacing: 0.5,
                          color: sig.direction === "BUY" ? "var(--buy)" : "var(--sell)",
                          background: sig.direction === "BUY" ? "rgba(48,209,88,0.15)" : "rgba(255,69,58,0.15)",
                          padding: "2px 6px", borderRadius: 4,
                        }}>
                          {sig.direction}
                        </span>
                      )}
                      <AgentBadge agent={agent} />
                    </div>
                    <span style={{ fontSize: 10, color: C.textDim }}>
                      {relTime(sig.created_at)}
                    </span>
                  </div>

                  {conf > 0 && <ConfBar value={conf} />}

                  <div style={{ fontSize: 11, color: C.textMid, marginTop: 5, lineHeight: 1.4 }}>
                    {sig.message?.slice(0, 100)}{sig.message && sig.message.length > 100 ? "…" : ""}
                  </div>

                  {blocked && (
                    <div style={{
                      marginTop: 6, fontSize: 10, color: "var(--sell)",
                      background: "rgba(255,69,58,0.10)", borderRadius: 4,
                      padding: "3px 8px", display: "flex", alignItems: "center", gap: 4,
                    }}>
                      <span style={{ fontSize: 10 }}>⊘</span>
                      {extractBlockReason(riskMsg) || "Blocked by Risk Agent"}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Card>
  );
}

// ── Risk Status ───────────────────────────────────────────────────────────────

function RiskStatus({ positions }: { positions: Trade[] }) {
  const { status } = useAppShell();
  const open = positions.filter(t => t.status === "OPEN" || t.status === "PARTIAL");
  const dailyPnl = Number(status?.daily_pnl ?? 0);
  const DAILY_CAP = 500; // TODO: pull from settings API

  const pnlPct = Math.min(100, Math.abs(dailyPnl) / DAILY_CAP * 100);
  const pnlColor = dailyPnl >= 0 ? "var(--buy)" : "var(--sell)";

  return (
    <Card style={{ marginTop: 16 }}>
      <div style={{ padding: "16px 20px" }}>
        <SectionLabel>Risk Status</SectionLabel>

        {/* Daily loss cap */}
        <div style={{ marginBottom: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 5 }}>
            <span style={{ fontSize: 11, color: C.textMid }}>Daily P&L</span>
            <span style={{ fontSize: 11, fontFamily: C.mono, color: pnlColor, fontWeight: 600 }}>
              {fmtUsd(dailyPnl)} / -{fmtUsd(DAILY_CAP)}
            </span>
          </div>
          <div style={{ height: 6, background: "var(--surface-3)", borderRadius: 3, overflow: "hidden" }}>
            <div style={{
              width: `${pnlPct}%`, height: "100%",
              background: pnlColor,
              borderRadius: 3, transition: "width .3s",
            }} />
          </div>
        </div>

        {/* Open positions */}
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
          <span style={{ fontSize: 11, color: C.textMid }}>Open Positions</span>
          <span style={{ fontSize: 11, fontFamily: C.mono, color: "var(--text-primary)", fontWeight: 600 }}>{open.length}</span>
        </div>

        {/* Concentration */}
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
          <span style={{ fontSize: 11, color: C.textMid }}>Concentration</span>
          <span style={{ fontSize: 11, fontFamily: C.mono, color: "var(--text-primary)", fontWeight: 600 }}>
            {open.length > 0 ? Math.round(open.length * 25) : 0}
            <span style={{ color: C.textDim }}> / 100</span>
          </span>
        </div>

        {/* Lot scale */}
        <div style={{ display: "flex", justifyContent: "space-between" }}>
          <span style={{ fontSize: 11, color: C.textMid }}>Lot Scale</span>
          <span style={{ fontSize: 11, fontFamily: C.mono, color: "var(--accent)", fontWeight: 600 }}>100%</span>
        </div>
      </div>
    </Card>
  );
}

// ── Agent Feed Panel ──────────────────────────────────────────────────────────

function AgentFeedPanel({ events }: { events: AgentEvent[] }) {
  return (
    <Card style={{ display: "flex", flexDirection: "column" }}>
      <div style={{ padding: "16px 20px 12px", flexShrink: 0 }}>
        <SectionLabel>Agent Feed</SectionLabel>
      </div>
      <div style={{
        flex: 1, overflowY: "auto", overflowX: "hidden",
        scrollbarWidth: "thin", scrollbarColor: "var(--text-muted) transparent",
        minHeight: 0,
      }}>
        {events.length === 0 ? (
          <div style={{ fontSize: 12, color: C.textDim, textAlign: "center", padding: "24px 0" }}>
            No events yet
          </div>
        ) : (
          events.slice(0, 30).map((ev, i) => {
            const agent = (ev.agent ?? "unknown").toLowerCase();
            const ts   = evTs(ev);
            const ms   = ageMs(ts);
            const msg  = evMsg(ev);
            const isError = (ev.level ?? "").toLowerCase() === "error" || (ev.level ?? "").toLowerCase() === "critical";
            const isWarn  = (ev.level ?? "").toLowerCase() === "warn"  || (ev.level ?? "").toLowerCase() === "warning";

            return (
              <div key={ev.id ?? i} style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "8px 16px",
                borderBottom: i === events.slice(0, 30).length - 1 ? "none" : "0.5px solid var(--border)",
                background: isError ? "rgba(255,69,58,0.06)" : isWarn ? "rgba(255,159,10,0.04)" : "transparent",
                minHeight: 40,
              }}>
                <SevDot agent={agent} ms={ms} />
                <AgentBadge agent={agent} />
                <span style={{
                  flex: 1, fontSize: 12, color: isError ? "var(--sell)" : isWarn ? "var(--health-warn)" : "var(--text-primary)",
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  lineHeight: 1.4,
                }}>
                  {msg || "—"}
                </span>
                <span style={{ fontSize: 10, color: C.textDim, fontFamily: C.mono, flexShrink: 0 }}>
                  {relTime(ts)}
                </span>
              </div>
            );
          })
        )}
      </div>
    </Card>
  );
}

// ── Macro Snapshot ─────────────────────────────────────────────────────────────

function MacroSnapshot() {
  return (
    <Card style={{ marginTop: 16 }}>
      <div style={{ padding: "16px 20px" }}>
        <SectionLabel>Macro</SectionLabel>

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          {[
            { label: "Regime",    value: "NORMAL",  color: "var(--buy)" },
            { label: "VIX",       value: "18.4",    color: "var(--accent)", sub: "↑" },
            { label: "DXY",      value: "104.2",   color: "var(--text-primary)", sub: "↓" },
            { label: "Lot Scale", value: "100%",    color: "var(--accent)" },
          ].map(({ label, value, color, sub }) => (
            <div key={label} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ fontSize: 11, color: C.textMid }}>{label}</span>
              <span style={{ fontSize: 12, fontFamily: C.mono, fontWeight: 600, color }}>
                {value}{sub && <span style={{ fontSize: 10, marginLeft: 2 }}>{sub}</span>}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// ── Command Console ────────────────────────────────────────────────────────────

function CommandConsole({ onPauseResume, onCloseAll, onForceSnap, isRunning, cmdBusy }: {
  onPauseResume: () => void;
  onCloseAll: () => void;
  onForceSnap: () => void;
  isRunning: boolean;
  cmdBusy: string | null;
}) {
  return (
    <div style={{
      background: C.bg, border: `1px solid ${C.border}`, borderRadius: C.radius,
      padding: "14px 20px", display: "flex", alignItems: "center",
      gap: 12, flexWrap: "wrap",
    }}>
      <span style={{ fontSize: 11, fontWeight: 600, color: C.label, letterSpacing: 0.5, textTransform: "uppercase", marginRight: 4 }}>
        Commands
      </span>

      <button disabled={!!cmdBusy} onClick={onPauseResume} style={{
        height: 34, padding: "0 18px",
        background: isRunning ? "rgba(255,159,10,0.12)" : "rgba(48,209,88,0.12)",
        border: `1px solid ${isRunning ? "rgba(255,159,10,0.35)" : "rgba(48,209,88,0.35)"}`,
        borderRadius: 8, color: isRunning ? "var(--health-warn)" : "var(--buy)",
        fontSize: 13, fontWeight: 600, cursor: cmdBusy ? "not-allowed" : "pointer",
        fontFamily: "inherit", opacity: cmdBusy && cmdBusy !== (isRunning ? "pause" : "resume") ? 0.45 : 1,
        transition: "opacity .15s",
      }}>
        {cmdBusy === (isRunning ? "pause" : "resume") ? "…" : isRunning ? "Pause Bot" : "Resume Bot"}
      </button>

      <div style={{ width: 1, height: 20, background: "var(--border)", margin: "0 4px" }} />

      <button disabled={!!cmdBusy} onClick={onCloseAll} style={{
        height: 34, padding: "0 18px",
        background: "rgba(255,69,58,0.10)", border: "1px solid rgba(255,69,58,0.35)",
        borderRadius: 8, color: "var(--sell)",
        fontSize: 13, fontWeight: 600, cursor: cmdBusy ? "not-allowed" : "pointer",
        fontFamily: "inherit", opacity: cmdBusy && cmdBusy !== "close_all" ? 0.45 : 1,
        transition: "opacity .15s",
      }}>
        {cmdBusy === "close_all" ? "…" : "Close All Positions"}
      </button>

      <button disabled={!!cmdBusy} onClick={onForceSnap} style={{
        height: 34, padding: "0 18px",
        background: "var(--surface-2)", border: "1px solid var(--border)",
        borderRadius: 8, color: "var(--text-primary)",
        fontSize: 13, fontWeight: 600, cursor: cmdBusy ? "not-allowed" : "pointer",
        fontFamily: "inherit", opacity: cmdBusy && cmdBusy !== "force_weekly_snap" ? 0.45 : 1,
        transition: "opacity .15s",
      }}>
        {cmdBusy === "force_weekly_snap" ? "…" : "Force Weekly Snap"}
      </button>
    </div>
  );
}

// ── Signal extraction helpers ─────────────────────────────────────────────────

function extractSymbol(msg: string): string | undefined {
  const m = msg.match(/\b([A-Z]{3,6}(?:\/[A-Z]{3})?)\b/);
  return m ? m[1] : undefined;
}

function extractDirection(msg: string): string | undefined {
  if (/buy|long|bullish|upward/i.test(msg))  return "BUY";
  if (/sell|short|bearish|downward/i.test(msg)) return "SELL";
  return undefined;
}

function extractConfidence(msg: string): number {
  const m = msg.match(/(\d+(?:\.\d+)?)\s*%/);
  if (m) return parseFloat(m[1]);
  // Try to extract from "confidence: 0.XX" pattern
  const c = msg.match(/confidence[:\s]+(\d+(?:\.\d+)?)/i);
  if (c) return parseFloat(c[1]) * 100;
  return 0;
}

function extractBlockReason(msg: string): string | undefined {
  const m = msg.match(/(?:guard|block|reject)[:\s]+([^.]{3,60})/i);
  return m ? m[1].trim() : undefined;
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function MissionControlPage() {
  const { status: shellStatus, isRunning: shellRunning } = useAppShell();

  const [events,      setEvents]      = useState<AgentEvent[]>([]);
  const [positions,   setPositions]   = useState<Trade[]>([]);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmCfg,  setConfirmCfg]  = useState({
    title: "", body: "", confirmLabel: "Confirm", danger: false, cmd: "",
  });
  const [cmdBusy,     setCmdBusy]     = useState<string | null>(null);
  const [cmdFeedback, setCmdFeedback] = useState<{ msg: string; ok: boolean } | null>(null);

  // Poll events every 8s
  useEffect(() => {
    let active = true;
    const run = async () => {
      try {
        const r = await fetch("/api/events?limit=80");
        const d = await r.json();
        if (active) setEvents(Array.isArray(d) ? d : (d.events ?? []));
      } catch { /* silent */ }
    };
    run(); const id = setInterval(run, 8_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  // Poll positions every 12s
  useEffect(() => {
    let active = true;
    const run = async () => {
      try {
        const r = await fetch("/api/trades");
        const d = await r.json();
        if (active) setPositions(Array.isArray(d) ? d : (d.trades ?? []));
      } catch { /* silent */ }
    };
    run(); const id = setInterval(run, 12_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  const sendCommand = useCallback(async (command: string) => {
    setCmdBusy(command);
    setCmdFeedback(null);
    try {
      const r = await fetch("/api/commands", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ command }),
      });
      setCmdFeedback({ msg: r.ok ? "Command sent" : "Command failed", ok: r.ok });
    } catch {
      setCmdFeedback({ msg: "Network error", ok: false });
    } finally {
      setCmdBusy(null);
      setTimeout(() => setCmdFeedback(null), 3_000);
    }
  }, []);

  const openConfirm = useCallback((cfg: typeof confirmCfg) => {
    setConfirmCfg(cfg);
    setConfirmOpen(true);
  }, []);

  const isRunning = shellRunning;

  return (
    <>
      <style>{`
        @keyframes dotPulse {
          0%,100% { opacity:1; transform:scale(1); }
          50%      { opacity:0.45; transform:scale(0.78); }
        }
        @keyframes fadeIn {
          from { opacity:0; transform:translateY(-4px); }
          to   { opacity:1; transform:translateY(0); }
        }
      `}</style>

      {/* Health Strip */}
      <HealthStrip
        onPauseResume={() => sendCommand(isRunning ? "pause" : "resume")}
        onCloseAll={() => openConfirm({
          title: "Close All Positions",
          body:  "This will immediately close every open position. This action cannot be undone.",
          confirmLabel: "Close All",
          danger: true,
          cmd:   "close_all",
        })}
        isRunning={isRunning}
        cmdBusy={cmdBusy}
      />

      {/* Main content */}
      <div style={{ padding: "20px 20px 0", display: "flex", flexDirection: "column", gap: 16, flex: 1, minHeight: 0 }}>

        {/* 3-column grid — 30% / 40% / 30% per REDESIGN spec */}
        <div style={{ display: "flex", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>

          {/* Left column: Positions + Exposure */}
          <div style={{ flex: "0 1 30%", minWidth: 240, display: "flex", flexDirection: "column", gap: 0 }}>
            <LivePositions positions={positions} />
            <ExposureHeatmap positions={positions} />
          </div>

          {/* Center column: Signals + Risk Status */}
          <div style={{ flex: "1 1 40%", minWidth: 300, display: "flex", flexDirection: "column", gap: 0 }}>
            <TopSignals events={events} />
            <RiskStatus positions={positions} />
          </div>

          {/* Right column: Agent Feed + Macro */}
          <div style={{ flex: "0 1 30%", minWidth: 260, display: "flex", flexDirection: "column", gap: 0 }}>
            <AgentFeedPanel events={events} />
            <MacroSnapshot />
          </div>
        </div>

        {/* Command Console */}
        <CommandConsole
          onPauseResume={() => sendCommand(isRunning ? "pause" : "resume")}
          onCloseAll={() => openConfirm({
            title: "Close All Positions",
            body:  "This will immediately close every open position. This action cannot be undone.",
            confirmLabel: "Close All",
            danger: true,
            cmd:   "close_all",
          })}
          onForceSnap={() => sendCommand("force_weekly_snap")}
          isRunning={isRunning}
          cmdBusy={cmdBusy}
        />
      </div>

      {/* Inline feedback */}
      {cmdFeedback && (
        <div style={{
          position: "fixed", bottom: 100, left: "50%", transform: "translateX(-50%)",
          background: "var(--surface-2)", border: `1px solid ${cmdFeedback.ok ? "var(--buy)" : "var(--sell)"}`,
          borderRadius: 10, padding: "10px 20px",
          fontSize: 13, fontWeight: 600, color: cmdFeedback.ok ? "var(--buy)" : "var(--sell)",
          animation: "fadeIn .2s ease", zIndex: 200,
          boxShadow: "var(--shadow-lg)",
        }}>
          {cmdFeedback.ok ? "✓" : "✗"} {cmdFeedback.msg}
        </div>
      )}

      {/* Confirm Modal */}
      <ConfirmModal
        open={confirmOpen}
        title={confirmCfg.title}
        body={confirmCfg.body}
        confirmLabel={confirmCfg.confirmLabel}
        danger={confirmCfg.danger}
        onConfirm={() => { setConfirmOpen(false); sendCommand(confirmCfg.cmd); }}
        onCancel={() => setConfirmOpen(false)}
      />
    </>
  );
}
