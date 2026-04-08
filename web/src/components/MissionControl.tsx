"use client";

import { useCallback, useMemo, useState } from "react";
import { useAppShell } from "@/components/AppShell";
import { useAgentEvents, useTrades } from "@/lib/swr";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { StatChip } from "@/components/ui/StatChip";
import { AgentBadge, DirectionBadge } from "@/components/ui/Badges";
import { DataTable, ColumnDef } from "@/components/ui/DataTable";
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

// ── Helpers ───────────────────────────────────────────────────────────────────
function fmtUsd(v: number): string {
  const abs = Math.abs(v);
  const f = abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (v < 0 ? "-$" : "$") + f;
}

// ── Main Page ─────────────────────────────────────────────────────────────────
export default function MissionControl() {
  const { status: shellStatus, isRunning } = useAppShell();

  const { data: events }   = useAgentEvents(80);
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

  const equity      = Number(shellStatus?.equity    ?? 0);
  const balance     = Number(shellStatus?.balance    ?? 0);
  const dailyPnl    = Number(shellStatus?.daily_pnl   ?? 0);
  const openTrades  = (positions ?? []).filter(t => t.status === "OPEN" || t.status === "PARTIAL");

  const feedEvents: FeedEvent[] = (events ?? []).map(ev => ({
    id:        String(ev.id ?? Math.random()),
    timestamp: ev.created_at ?? ev.ts ?? new Date().toISOString(),
    agent:     ev.agent ?? "system",
    level:     ev.level ?? "info",
    message:   ev.message ?? ev.msg ?? "",
    data:      ev.data,
  })).reverse();

  const pipelineAgents = useMemo(() => {
    const evts = events ?? [];
    const map  = new Map<string, (typeof evts)[number]>();
    for (const ev of evts) {
      if (ev.agent && !map.has(ev.agent)) map.set(ev.agent, ev);
    }
    return Array.from(map.values()).slice(0, 8);
  }, [events]);

  const tradeColumns: ColumnDef<Trade>[] = [
    {
      header: "Symbol",
      cell: row => <span style={{ fontWeight: 700, color: "var(--text-1)" }}>{row.symbol}</span>,
    },
    {
      header: "Dir",
      cell: row => <DirectionBadge direction={row.direction.toUpperCase()} />,
    },
    {
      header: "Entry",
      align: "right",
      cell: row => (
        <span style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}>
          {row.entry_price.toFixed(5)}
        </span>
      ),
    },
    {
      header: "P&L",
      align: "right",
      cell: row => {
        const pnl = Number(row.pnl ?? 0);
        const color = pnl > 0 ? "var(--gold)" : pnl < 0 ? "var(--red)" : "var(--text-3)";
        return (
          <span style={{ fontFamily: "var(--font-mono)", fontWeight: 700 }}>
            <span className={color}>{pnl > 0 ? "+" : ""}{fmtUsd(pnl)}</span>
          </span>
        );
      },
    },
  ];

  return (
    <div style={{ padding: "24px", maxWidth: 1400, margin: "0 auto", display: "flex", flexDirection: "column", gap: 24 }}>
      {/* ── KPI Row ─────────────────────────────────────── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
          gap: 14,
        }}
      >
        <StatChip
          label="Balance"
          value={balance}
          format="currency"
        />
        <StatChip
          label="Equity"
          value={equity}
          format="currency"
          trend={equity >= balance ? "Nominal" : "Drawdown"}
        />
        <StatChip
          label="Daily P&L"
          value={dailyPnl}
          format="currency"
          trend={dailyPnl >= 0 ? "+" : "-"}
        />
        <StatChip
          label="Open Trades"
          value={openTrades.length}
          format="number"
        />
      </div>

      {/* ── Agent Pipeline ─────────────────────────────── */}
      <Card>
        <CardHeader>Agent Pipeline Status</CardHeader>
        <CardBody style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {pipelineAgents.length === 0 ? (
            <div style={{ color: "var(--text-3)", fontStyle: "italic", fontSize: 13, padding: "8px 0" }}>
              No recent agent activity
            </div>
          ) : (
            pipelineAgents.map(ev => {
              const isActive = (Date.now() - new Date(ev.created_at || ev.ts || 0).getTime()) < 60_000;
              const isErr    = (ev.level ?? "").toLowerCase() === "error";
              return (
                <div
                  key={ev.id ?? Math.random()}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 14,
                    background: "var(--bg-3)",
                    padding: "12px 16px",
                    borderRadius: 8,
                    border: "1px solid rgba(95,122,158,0.15)",
                  }}
                >
                  <div
                    style={{
                      width:        8,
                      height:       8,
                      borderRadius: "50%",
                      background:   isErr ? "var(--red)" : isActive ? "var(--green)" : "var(--text-3)",
                      flexShrink:   0,
                      boxShadow:     isActive ? "0 0 6px var(--green)" : "none",
                    }}
                  />
                  <div style={{ width: 88, flexShrink: 0 }}>
                    <AgentBadge agent={ev.agent} />
                  </div>
                  <span
                    style={{
                      fontSize:      12,
                      fontFamily:    "var(--font-mono)",
                      color:         "rgba(244,244,245,0.65)",
                      overflow:      "hidden",
                      textOverflow:   "ellipsis",
                      whiteSpace:     "nowrap",
                      flex:           1,
                      minWidth:       0,
                    }}
                  >
                    {ev.message || ev.msg}
                  </span>
                </div>
              );
            })
          )}
        </CardBody>
      </Card>

      {/* ── Live Positions ─────────────────────────────── */}
      <Card>
        <CardHeader>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span>Live Positions</span>
            <span style={{ fontSize: 11, color: "var(--text-3)", fontFamily: "var(--font-mono)" }}>
              {openTrades.length} open
            </span>
          </div>
        </CardHeader>
        <CardBody style={{ padding: 0 }}>
          {openTrades.length === 0 ? (
            <div style={{ padding: "32px", textAlign: "center", color: "var(--text-3)", fontSize: 13 }}>
              No open positions
            </div>
          ) : (
            <>
              <DataTable data={openTrades.slice(0, 5)} columns={tradeColumns} />
              {openTrades.length > 5 && (
                <div
                  style={{
                    padding: "12px 16px",
                    textAlign: "center",
                    fontSize: 12,
                    color: "var(--text-3)",
                    borderTop: "1px solid rgba(95,122,158,0.15)",
                  }}
                >
                  + {openTrades.length - 5} more positions
                </div>
              )}
            </>
          )}
        </CardBody>
      </Card>

      {/* ── Live Intel Feed ────────────────────────────── */}
      <Card>
        <CardHeader>Live Intel Feed</CardHeader>
        <div style={{ height: 280 }}>
          <EventFeed events={feedEvents} />
        </div>
      </Card>

      {/* ── Quick Commands + Equity ───────────────────── */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 20,
        }}
      >
        {/* Commands */}
        <Card variant="ghost" style={{ border: "none" }}>
          <CardHeader style={{ border: "none", padding: "0 0 14px" }}>Quick Commands</CardHeader>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 12 }}>
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
              confirmMessage="Confirm Close All?"
            >
              Close All Positions
            </CommandButton>

            <CommandButton
              onClick={() => sendCommand("force_weekly_snap")}
              variant="info"
              confirmMessage="Confirm Snapshot?"
            >
              Force Snap
            </CommandButton>
          </div>
        </Card>

        {/* Equity visualizer placeholder */}
        <Card
          style={{
            display:        "flex",
            alignItems:     "center",
            justifyContent: "center",
            padding:        32,
            border:         "1px dashed rgba(95,122,158,0.3)",
            minHeight:      120,
          }}
        >
          <span
            style={{
              color:      "rgba(244,244,245,0.25)",
              fontFamily: "var(--font-mono)",
              fontSize:   13,
            }}
          >
            [ Equity Curve Placeholder ]
          </span>
        </Card>
      </div>

      {/* ── Feedback Toast ──────────────────────────────── */}
      {cmdFeedback && (
        <div
          style={{
            position:   "fixed",
            bottom:     24,
            right:      24,
            padding:    "12px 18px",
            borderRadius: 8,
            fontFamily: "var(--font-ui)",
            fontWeight:  700,
            fontSize:   13,
            textTransform: "uppercase",
            letterSpacing: "0.05em",
            zIndex:     50,
            border:      `1px solid ${cmdFeedback.ok ? "var(--green)" : "var(--red)"}`,
            boxShadow:  "0 8px 24px rgba(0,0,0,0.4)",
            background: "var(--bg-2)",
            color:      cmdFeedback.ok ? "var(--green)" : "var(--red)",
            display:    "flex",
            alignItems: "center",
            gap:        10,
            animation:  "toastFadeIn 0.2s ease",
          }}
        >
          <span style={{ fontSize: 16 }}>{cmdFeedback.ok ? "✓" : "✗"}</span>
          {cmdFeedback.msg}
        </div>
      )}

      <style>{`
        @keyframes toastFadeIn {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}
