"use client";

import { useCallback, useMemo, useState } from "react";
import { useAppShell } from "@/components/AppShell";
import { useAgentEvents, useTrades } from "@/lib/swr";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { StatChip } from "@/components/ui/StatChip";
import { AgentBadge, DirectionBadge } from "@/components/ui/Badges";
import { EventFeed, FeedEvent } from "@/components/ui/EventFeed";
import { CommandButton } from "@/components/ui/CommandButton";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Trade {
  id: number;
  symbol: string;
  direction: string;
  entry_price: number;
  open_time?: string;
  pnl?: number;
  status: string;
}

interface Signal {
  symbol: string;
  direction: string;
  confidence: number;
  strategy: string;
  entry_price: number;
  stop_loss: number;
  take_profit_1: number;
  timestamp?: string;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtUsd(v: number): string {
  const abs = Math.abs(v);
  const f = abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (v < 0 ? "-$" : "$") + f;
}

function computeHealth(events: FeedEvent[]): { score: number; label: string; color: string } {
  if (!events.length) return { score: 0, label: "NO DATA", color: "#494847" };
  const recent = events.slice(0, 20);
  const errors = recent.filter(e => (e.level || "").toLowerCase() === "error").length;
  const warns  = recent.filter(e => (e.level || "").toLowerCase() === "warn").length;
  const score  = Math.max(0, Math.min(100, 100 - errors * 15 - warns * 5));
  if (score >= 80) return { score, label: "NOMINAL",  color: "#00fd87" };
  if (score >= 60) return { score, label: "CAUTION", color: "#f0b429" };
  return               { score, label: "DEGRADED", color: "#ff453a" };
}

function relTime(ts?: string): string {
  if (!ts) return "—";
  const ms = Date.now() - new Date(ts).getTime();
  if (ms < 60_000)  return Math.floor(ms / 1_000)     + "s ago";
  if (ms < 3_600_000) return Math.floor(ms / 60_000)   + "m ago";
  return                      Math.floor(ms / 3_600_000) + "h ago";
}

// ── Sub-components ────────────────────────────────────────────────────────────

function HealthScore({ score, label, color }: { score: number; label: string; color: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
      {/* Radial progress */}
      <div style={{ position: "relative", width: 72, height: 72 }}>
        <svg width="72" height="72" viewBox="0 0 72 72" style={{ transform: "rotate(-90deg)" }}>
          <circle cx="36" cy="36" r="30" fill="none" stroke="#1a1a1a" strokeWidth="6" />
          <circle
            cx="36" cy="36" r="30" fill="none"
            stroke={color}
            strokeWidth="6"
            strokeDasharray={`${2 * Math.PI * 30}`}
            strokeDashoffset={`${2 * Math.PI * 30 * (1 - score / 100)}`}
            strokeLinecap="round"
            style={{ transition: "stroke-dashoffset 0.6s ease", filter: `drop-shadow(0 0 4px ${color})` }}
          />
        </svg>
        <div style={{
          position:   "absolute",
          inset:      0,
          display:    "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
        }}>
          <span style={{ fontSize: 15, fontFamily: "var(--font-mono)", fontWeight: 700, color }}>
            {score}
          </span>
        </div>
      </div>
      <span style={{ fontSize: 9, fontFamily: "var(--font-mono)", fontWeight: 700, color, letterSpacing: "0.12em" }}>
        {label}
      </span>
    </div>
  );
}

function StatusPulse({ running }: { running: boolean }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ position: "relative" }}>
        <div style={{
          width:        10,
          height:       10,
          borderRadius: "50%",
          background:   running ? "#00fd87" : "#494847",
          boxShadow:    running ? "0 0 8px #00fd87" : "none",
        }} />
        {running && (
          <div style={{
            position:   "absolute",
            inset:     "-4px",
            borderRadius: "50%",
            border:    "1px solid rgba(0,253,135,0.35)",
            animation:  "pulseRing 2s ease-out infinite",
          }} />
        )}
      </div>
      <span style={{
        fontSize:   11,
        fontFamily: "var(--font-mono)",
        fontWeight: 700,
        color:      running ? "#00fd87" : "#494847",
        letterSpacing: "0.10em",
        textTransform: "uppercase",
      }}>
        {running ? "LIVE" : "STOPPED"}
      </span>
    </div>
  );
}

function AgentRow({ event, index }: { event: FeedEvent; index: number }) {
  const isActive = (Date.now() - new Date(event.timestamp || 0).getTime()) < 90_000;
  const isErr    = (event.level || "").toLowerCase() === "error";
  const isWarn   = (event.level || "").toLowerCase() === "warn";
  const dotColor = isErr ? "#ff453a" : isWarn ? "#f0b429" : isActive ? "#00fd87" : "#494847";

  return (
    <div style={{
      display:       "flex",
      alignItems:    "center",
      gap:           12,
      padding:       "8px 0",
      borderBottom:  index < 7 ? "1px solid rgba(95,122,158,0.08)" : "none",
    }}>
      <div style={{
        width:        8,
        height:       8,
        borderRadius: "50%",
        background:   dotColor,
        flexShrink:   0,
        boxShadow:    isActive ? `0 0 5px ${dotColor}` : "none",
      }} />
      <div style={{ width: 88, flexShrink: 0 }}>
        <AgentBadge agent={event.agent || "system"} active={isActive} />
      </div>
      <span style={{
        fontSize:      12,
        fontFamily:    "var(--font-mono)",
        color:         "rgba(244,244,245,0.55)",
        overflow:      "hidden",
        textOverflow:  "ellipsis",
        whiteSpace:    "nowrap",
        flex:          1,
        minWidth:      0,
      }}>
        {event.message || ""}
      </span>
      <span style={{
        fontSize:     10,
        fontFamily:   "var(--font-mono)",
        color:        "#494847",
        flexShrink:   0,
      }}>
        {relTime(event.timestamp)}
      </span>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function MissionControl() {
  const { status: shellStatus, isRunning } = useAppShell();

  const { data: events    } = useAgentEvents(80);
  const { data: positions } = useTrades();

  const [cmdFeedback, setCmdFeedback] = useState<{ msg: string; ok: boolean } | null>(null);

  const sendCommand = useCallback(async (command: string) => {
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
      setTimeout(() => setCmdFeedback(null), 3_000);
    }
  }, []);

  const equity     = Number(shellStatus?.equity    ?? 0);
  const balance    = Number(shellStatus?.balance    ?? 0);
  const dailyPnl   = Number(shellStatus?.daily_pnl  ?? 0);
  const openTrades = (positions ?? []).filter(t => t.status === "OPEN" || t.status === "PARTIAL");

  const feedEvents: FeedEvent[] = useMemo(() => (events ?? []).map(ev => ({
    id:        String(ev.id ?? Math.random()),
    timestamp: ev.created_at ?? ev.ts ?? new Date().toISOString(),
    agent:     ev.agent ?? "system",
    level:     ev.level ?? "info",
    message:   ev.message ?? ev.msg ?? "",
    data:      ev.data,
  })).reverse(), [events]);

  const health = useMemo(() => computeHealth(feedEvents), [feedEvents]);

  // Recent signals from strategy agent events
  const recentSignals: Signal[] = useMemo(() => {
    const sigs: Signal[] = [];
    for (const ev of feedEvents) {
      const msg: string = ev.message || "";
      // Match patterns like "Signal from unified_alpha: BUY EURUSD.s @ 1.12345 SL=1.12000 TP1=1.12600 conf=0.72"
      const match = msg.match(/([A-Z]+)\s+([A-Z0-9]+(?:\.[a-z])?)\s+BUY\s+[\s\S]*?@\s+([0-9.]+)\s+SL=([0-9.]+)\s+TP1=([0-9.]+)\s+conf=([0-9.]+)/i)
                   || msg.match(/([A-Z]+)\s+([A-Z0-9]+(?:\.[a-z])?)\s+SELL\s+[\s\S]*?@\s+([0-9.]+)\s+SL=([0-9.]+)\s+TP1=([0-9.]+)\s+conf=([0-9.]+)/i);
      if (match) {
        sigs.push({
          symbol:      match[2],
          direction:   match[1],
          entry_price: parseFloat(match[3]),
          stop_loss:   parseFloat(match[4]),
          take_profit_1: parseFloat(match[5]),
          confidence:  parseFloat(match[6]),
          strategy:    ev.agent || "unknown",
          timestamp:   ev.timestamp,
        });
      }
      if (sigs.length >= 8) break;
    }
    return sigs;
  }, [feedEvents]);

  return (
    <div style={{
      padding: "24px 28px",
      maxWidth: 1400,
      margin:  "0 auto",
      display:  "flex",
      flexDirection: "column",
      gap: 20,
    }}>
      {/* ── Command Center Header ─────────────────────────────────── */}
      <div style={{
        display:        "flex",
        alignItems:    "center",
        justifyContent: "space-between",
        padding:        "16px 20px",
        background:     "#0e0e0e",
        border:         "1px solid #2a2a2a",
        borderRadius:   10,
      }}>
        {/* Left: Identity + session info */}
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <span style={{
              fontFamily:    "var(--font-mono)",
              fontSize:      18,
              fontWeight:    700,
              color:         "#e0e0e0",
              letterSpacing: "0.05em",
            }}>
              PULSE<span style={{ color: "#00fd87" }}>TRADE</span>
            </span>
            <StatusPulse running={isRunning} />
            <span style={{
              fontFamily:  "var(--font-mono)",
              fontSize:    10,
              color:       "#494847",
              letterSpacing: "0.10em",
            }}>
              SESSION=LONDON
            </span>
          </div>
          <div style={{ display: "flex", gap: 20, marginTop: 4 }}>
            {[
              [shellStatus?.broker_name  || "—", "#adaaaa"],
              [shellStatus?.broker_server || "—", "#494847"],
              [`ACCT ${shellStatus?.broker_account || "—"}`, "#494847"],
            ].map(([val, col], i) => (
              <span key={i} style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: col as string }}>
                {val as string}
              </span>
            ))}
          </div>
        </div>

        {/* Right: Health + Uptime */}
        <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
          <HealthScore score={health.score} label={health.label} color={health.color} />
          <div style={{ display: "flex", flexDirection: "column", gap: 4, alignItems: "flex-end" }}>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#494847", letterSpacing: "0.08em" }}>
              LAST TICK
            </span>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 12, color: "#adaaaa" }}>
              {relTime(shellStatus?.last_tick)}
            </span>
          </div>
        </div>
      </div>

      {/* ── KPI Row ──────────────────────────────────────────────── */}
      <div style={{
        display:              "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(170px, 1fr))",
        gap:                  14,
      }}>
        <StatChip label="Balance"    value={balance}              format="currency" />
        <StatChip label="Equity"      value={equity}                format="currency" trend={equity >= balance ? "+" : "-"} />
        <StatChip label="Daily P&L"  value={dailyPnl}             format="currency" trend={dailyPnl >= 0 ? "+" : "-"} />
        <StatChip label="Open Trades" value={openTrades.length}     format="number" />
        <StatChip label="Symbols Scanned" value={7468}              format="number" />
        <StatChip label="Signals"     value={recentSignals.length}  format="number" />
      </div>

      {/* ── Main Grid ───────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>

        {/* Agent Pipeline */}
        <Card>
          <CardHeader>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700, letterSpacing: "0.10em", color: "#e0e0e0" }}>
                AGENT PIPELINE
              </span>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: "#494847" }}>
                {feedEvents.length} events
              </span>
            </div>
          </CardHeader>
          <CardBody style={{ display: "flex", flexDirection: "column", maxHeight: 320, overflowY: "auto" }}>
            {feedEvents.length === 0 ? (
              <div style={{ color: "#494847", fontSize: 12, padding: "16px 0", fontFamily: "var(--font-mono)" }}>
                Awaiting agent events…
              </div>
            ) : (
              feedEvents.slice(0, 12).map((ev, i) => <AgentRow key={ev.id} event={ev} index={i} />)
            )}
          </CardBody>
        </Card>

        {/* Recent Signals */}
        <Card>
          <CardHeader>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700, letterSpacing: "0.10em", color: "#e0e0e0" }}>
                RECENT SIGNALS
              </span>
            </div>
          </CardHeader>
          <CardBody style={{ padding: 0 }}>
            {recentSignals.length === 0 ? (
              <div style={{ color: "#494847", fontSize: 12, padding: "32px", textAlign: "center", fontFamily: "var(--font-mono)" }}>
                No signals detected
              </div>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid rgba(95,122,158,0.12)" }}>
                    {["Symbol", "Dir", "Entry", "SL", "Conf"].map(h => (
                      <th key={h} style={{
                        padding:  "6px 12px",
                        fontSize: 9,
                        fontFamily: "var(--font-mono)",
                        fontWeight: 700,
                        letterSpacing: "0.10em",
                        color: "#494847",
                        textAlign: h === "Symbol" || h === "Dir" ? "left" : "right",
                      }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {recentSignals.map((sig, i) => {
                    const confColor = sig.confidence >= 0.65 ? "#00fd87" : sig.confidence >= 0.55 ? "#f0b429" : "#ff453a";
                    return (
                      <tr key={i} style={{ borderBottom: "1px solid rgba(95,122,158,0.06)" }}>
                        <td style={{ padding: "7px 12px", fontFamily: "var(--font-mono)", fontSize: 12, fontWeight: 700, color: "#e0e0e0" }}>
                          {sig.symbol}
                        </td>
                        <td style={{ padding: "7px 12px" }}>
                          <DirectionBadge direction={sig.direction} />
                        </td>
                        <td style={{ padding: "7px 12px", fontFamily: "var(--font-mono)", fontSize: 11, color: "#adaaaa", textAlign: "right" }}>
                          {sig.entry_price.toFixed(5)}
                        </td>
                        <td style={{ padding: "7px 12px", fontFamily: "var(--font-mono)", fontSize: 11, color: "#ff453a", textAlign: "right" }}>
                          {sig.stop_loss.toFixed(5)}
                        </td>
                        <td style={{ padding: "7px 12px", fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700, color: confColor, textAlign: "right" }}>
                          {(sig.confidence * 100).toFixed(0)}%
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </CardBody>
        </Card>
      </div>

      {/* ── Live Feed + Commands ─────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        <Card>
          <CardHeader>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700, letterSpacing: "0.10em", color: "#e0e0e0" }}>
                LIVE INTEL FEED
              </span>
            </div>
          </CardHeader>
          <div style={{ height: 240 }}>
            <EventFeed events={feedEvents.slice(0, 40)} />
          </div>
        </Card>

        <Card>
          <CardHeader>
            <span style={{ fontFamily: "var(--font-mono)", fontSize: 11, fontWeight: 700, letterSpacing: "0.10em", color: "#e0e0e0" }}>
              QUICK COMMANDS
            </span>
          </CardHeader>
          <CardBody style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <CommandButton
              onClick={() => sendCommand(isRunning ? "pause" : "resume")}
              variant={isRunning ? "info" : "warning"}
              confirmMessage={isRunning ? "Pause Bot?" : "Resume Bot?"}
            >
              {isRunning ? "Pause Bot" : "Resume Bot"}
            </CommandButton>
            <CommandButton
              onClick={() => sendCommand("close_all")}
              variant="danger"
              confirmMessage="Close ALL positions?"
            >
              Close All Positions
            </CommandButton>
            <CommandButton
              onClick={() => sendCommand("force_weekly_snap")}
              variant="info"
              confirmMessage="Force weekly snapshot?"
            >
              Force Snapshot
            </CommandButton>
          </CardBody>
        </Card>
      </div>

      {/* ── Feedback Toast ───────────────────────────────────────── */}
      {cmdFeedback && (
        <div style={{
          position:   "fixed",
          bottom:     28,
          right:      28,
          padding:    "12px 20px",
          borderRadius: 8,
          fontFamily: "var(--font-mono)",
          fontWeight: 700,
          fontSize:   12,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          zIndex:     9999,
          border:     `1px solid ${cmdFeedback.ok ? "#00fd87" : "#ff453a"}`,
          boxShadow:  `0 8px 32px rgba(0,0,0,0.5), 0 0 12px ${cmdFeedback.ok ? "rgba(0,253,135,0.2)" : "rgba(255,69,58,0.2)"}`,
          background: "#0e0e0e",
          color:      cmdFeedback.ok ? "#00fd87" : "#ff453a",
          display:    "flex",
          alignItems: "center",
          gap:        10,
          animation:  "toastFadeIn 0.2s ease",
        }}>
          <span style={{ fontSize: 16 }}>{cmdFeedback.ok ? "✓" : "✗"}</span>
          {cmdFeedback.msg}
        </div>
      )}

      <style>{`
        @keyframes pulseRing {
          0%   { transform: scale(1);   opacity: 0.8; }
          100% { transform: scale(2.2); opacity: 0;   }
        }
        @keyframes toastFadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to   { opacity: 1; transform: translateY(0);    }
        }
      `}</style>
    </div>
  );
}
