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

  const { data: events } = useAgentEvents(80);
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

  const equity = Number(shellStatus?.equity ?? 0);
  const balance = Number(shellStatus?.balance ?? 0);
  const dailyPnl = Number(shellStatus?.daily_pnl ?? 0);
  const openTrades = (positions ?? []).filter(t => t.status === "OPEN" || t.status === "PARTIAL");

  const feedEvents: FeedEvent[] = (events ?? []).map(ev => ({
    id: String(ev.id ?? Math.random()),
    timestamp: ev.created_at ?? ev.ts ?? new Date().toISOString(),
    agent: ev.agent ?? "system",
    level: ev.level ?? "info",
    message: ev.message ?? ev.msg ?? "",
    data: ev.data
  })).reverse();

  const pipelineAgents = useMemo(() => {
    const evts = events ?? [];
    const map = new Map<string, (typeof evts)[number]>();
    for (const ev of evts) {
      if (ev.agent && !map.has(ev.agent)) {
        map.set(ev.agent, ev);
      }
    }
    return Array.from(map.values()).slice(0, 6);
  }, [events]);

  const tradeColumns: ColumnDef<Trade>[] = [
    { header: "SYMB", accessorKey: "symbol", cell: row => <span className="font-bold text-text-1">{row.symbol}</span> },
    { header: "DIR", accessorKey: "direction", cell: row => <DirectionBadge direction={row.direction.toUpperCase()} /> },
    { header: "ENTRY", accessorKey: "entry_price", align: "right", cell: row => row.entry_price.toFixed(5) },
    { header: "P&L", accessorKey: "pnl", align: "right", cell: row => {
       const pnl = Number(row.pnl ?? 0);
       const color = pnl > 0 ? "text-gold" : pnl < 0 ? "text-red" : "text-text-3";
       return <span className={`font-bold ${color}`}>{pnl > 0 ? "+" : ""}{fmtUsd(pnl)}</span>
    }}
  ];

  return (
    <div style={{ padding: "16px 24px 96px", maxWidth: 1400, margin: "0 auto" }}>
      {/* ROW 1: Bot Status Bar */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12, marginBottom: 24 }}>
        <StatChip label="Balance" value={balance} format="currency" />
        <StatChip label="Equity" value={equity} format="currency" trend={equity >= balance ? "Nominal" : "Drawdown"} />
        <StatChip label="Daily P&L" value={dailyPnl} format="currency" trend={dailyPnl >= 0 ? "+" : "-"} />
        <StatChip label="Open Trades" value={openTrades.length} format="number" />
      </div>

      {/* Main Grid */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 24, marginBottom: 24 }}>
        {/* Agent Pipeline */}
        <Card>
          <CardHeader>Agent Pipeline Status</CardHeader>
          <CardBody>
            {pipelineAgents.length === 0 ? (
              <div style={{ color: "rgba(235,235,245,0.4)", fontStyle: "italic", fontSize: 14, padding: "8px 0" }}>No recent agent activity</div>
            ) : (
              pipelineAgents.map(ev => {
                const isActive = (new Date().getTime() - new Date(ev.created_at || ev.ts || 0).getTime()) < 60000;
                const isErr = ev.level?.toLowerCase() === 'error';
                return (
                  <div key={ev.id || Math.random()} style={{ display: "flex", alignItems: "center", gap: 16, background: "#1C1C1E", padding: "12px 16px", borderRadius: 6, border: "0.5px solid rgba(95,122,158,0.2)", marginBottom: 12 }}>
                     <span style={{ width: 8, height: 8, borderRadius: "50%", background: isErr ? "#FF453A" : isActive ? "#30D158" : "#8E8E93", flexShrink: 0, animation: isActive ? "feedPulse 2s ease-in-out infinite" : undefined }} />
                     <span style={{ width: 96, flexShrink: 0 }}><AgentBadge agent={ev.agent} /></span>
                     <span style={{ fontSize: 12, fontFamily: "ui-monospace, monospace", color: "rgba(235,235,245,0.7)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1 }}>{ev.message || ev.msg}</span>
                  </div>
                );
              })
            )}
          </CardBody>
        </Card>
      </div>

      {/* Live Positions */}
      <div style={{ marginBottom: 24 }}>
        <Card>
          <CardHeader>Live Positions</CardHeader>
          <CardBody>
            <DataTable data={openTrades.slice(0, 5)} columns={tradeColumns} />
            {openTrades.length > 5 && (
              <div style={{ padding: "12px 16px", textAlign: "center", fontSize: 12, color: "rgba(235,235,245,0.4)", borderTop: "0.5px solid rgba(95,122,158,0.2)" }}>
                + {openTrades.length - 5} more positions
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      {/* ROW 3: Live Agent Feed */}
      <div style={{ marginBottom: 24 }}>
        <CardHeader style={{ padding: "16px 0 8px", borderBottom: "none" }}>Live Intel Feed</CardHeader>
        <EventFeed events={feedEvents} />
      </div>

      {/* Quick Commands + Equity placeholder */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
        <Card variant="ghost" style={{ border: "none" }}>
          <CardHeader style={{ padding: "0 0 12px", border: "none" }}>Quick Commands</CardHeader>
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

        <Card style={{ display: "flex", alignItems: "center", justifyContent: "center", padding: 32, border: "1px dashed rgba(95,122,158,0.3)", minHeight: 140 }}>
           <span style={{ color: "rgba(235,235,245,0.3)", fontFamily: "ui-monospace, monospace", fontSize: 14 }}>[ Equity Curve Visualizer Placeholder ]</span>
        </Card>
      </div>

      {/* Feedback Toast */}
      {cmdFeedback && (
        <div style={{
          position: "fixed",
          bottom: 24,
          right: 24,
          padding: "12px 16px",
          borderRadius: 6,
          fontFamily: "var(--font-ui)",
          fontWeight: 700,
          fontSize: 14,
          textTransform: "uppercase",
          zIndex: 50,
          border: `1px solid ${cmdFeedback.ok ? "var(--buy)" : "var(--sell)"}`,
          boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
          background: "var(--surface-2)",
          color: cmdFeedback.ok ? "var(--buy)" : "var(--sell)",
          display: "flex",
          alignItems: "center",
          gap: 8,
          animation: "toastFadeIn 0.2s ease",
        }}>
          <span>{cmdFeedback.ok ? "✓" : "✗"}</span>
          {cmdFeedback.msg}
        </div>
      )}
    </div>
  );
}
