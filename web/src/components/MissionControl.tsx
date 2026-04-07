"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useAppShell } from "@/components/AppShell";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { StatChip } from "@/components/ui/StatChip";
import { AgentBadge, DirectionBadge } from "@/components/ui/Badges";
import { DataTable, ColumnDef } from "@/components/ui/DataTable";
import { EventFeed, FeedEvent } from "@/components/ui/EventFeed";
import { CommandButton } from "@/components/ui/CommandButton";

// ── Types ─────────────────────────────────────────────────────────────────────
interface AgentEvent {
  id?: string | number;
  agent: string;
  level: string;
  message?: string;
  msg?: string;
  created_at?: string;
  ts?: string;
  data?: any;
}

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

  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [positions, setPositions] = useState<Trade[]>([]);
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

  // Format data
  const equity = Number(shellStatus?.equity ?? 0);
  const balance = Number(shellStatus?.balance ?? 0);
  const dailyPnl = Number(shellStatus?.daily_pnl ?? 0);
  const openTrades = positions.filter(t => t.status === "OPEN" || t.status === "PARTIAL");

  const feedEvents: FeedEvent[] = events.map(ev => ({
    id: String(ev.id ?? Math.random()),
    timestamp: ev.created_at ?? ev.ts ?? new Date().toISOString(),
    agent: ev.agent ?? "system",
    level: ev.level ?? "info",
    message: ev.message ?? ev.msg ?? "",
    data: ev.data
  })).reverse();

  // Extract latest event per agent for the pipeline
  const pipelineAgents = useMemo(() => {
    const map = new Map<string, AgentEvent>();
    for (const ev of events) {
      if (ev.agent && !map.has(ev.agent)) {
        map.set(ev.agent, ev);
      }
    }
    return Array.from(map.values()).slice(0, 6); // Just show top 6 recent active agents
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
    <div className="p-4 md:p-6 lg:p-8 space-y-6 max-w-7xl mx-auto pb-24">
      {/* ROW 1: Bot Status Bar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatChip label="Balance" value={balance} format="currency" />
        <StatChip label="Equity" value={equity} format="currency" trend={equity >= balance ? "Nominal" : "Drawdown"} />
        <StatChip label="Daily P&L" value={dailyPnl} format="currency" trend={dailyPnl >= 0 ? "+" : "-"} />
        <StatChip label="Open Trades" value={openTrades.length} format="number" />
      </div>

      {/* Main Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* COL 1: Agent Pipeline (60% -> 7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <Card className="h-full">
            <CardHeader>Agent Pipeline Status</CardHeader>
            <CardBody className="space-y-3">
              {pipelineAgents.length === 0 ? (
                <div className="text-text-3 italic text-sm py-4">No recent agent activity</div>
              ) : (
                pipelineAgents.map(ev => {
                  const isActive = (new Date().getTime() - new Date(ev.created_at || ev.ts || 0).getTime()) < 60000;
                  const isErr = ev.level?.toLowerCase() === 'error';
                  return (
                    <div key={ev.id || Math.random()} className="flex items-center gap-4 bg-bg-3 p-3 rounded-sm border border-border/50">
                       <span className={`w-2 h-2 rounded-full shrink-0 ${isErr ? 'bg-red' : isActive ? 'bg-green animate-pulse' : 'bg-text-3'}`} />
                       <span className="shrink-0 w-24"><AgentBadge agent={ev.agent} /></span>
                       <span className="text-xs font-mono text-text-2 truncate flex-1">{ev.message || ev.msg}</span>
                    </div>
                  );
                })
              )}
            </CardBody>
          </Card>
        </div>

        {/* COL 2: Open Trades (40% -> 5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <Card className="h-full">
            <CardHeader>Live Positions</CardHeader>
            <CardBody className="p-0">
               <DataTable data={openTrades.slice(0, 5)} columns={tradeColumns} />
               {openTrades.length > 5 && (
                 <div className="p-3 text-center text-xs text-text-3 bg-bg-3 border-t border-border">
                   + {openTrades.length - 5} more positions
                 </div>
               )}
            </CardBody>
          </Card>
        </div>

      </div>

      {/* ROW 3: Live Agent Feed */}
      <div>
        <CardHeader className="px-0 pt-4 pb-2 border-none">Live Intel Feed</CardHeader>
        <EventFeed events={feedEvents} />
      </div>

      {/* BOTTOM ROW */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-4">
        <Card variant="ghost" className="border-none">
          <CardHeader className="px-0 pb-3 border-none">Quick Commands</CardHeader>
          <div className="flex flex-wrap gap-3">
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

        {/* Equity placeholder */}
        <Card className="flex items-center justify-center p-8 border-dashed border-border text-text-3 font-mono text-sm h-[140px]">
           [ Equity Curve Visualizer Placeholder ]
        </Card>
      </div>

      {/* Feedback Toast */}
      {cmdFeedback && (
        <div className={`fixed bottom-6 right-6 px-4 py-3 rounded-sm font-ui uppercase font-bold text-sm z-50 border shadow-lg animate-in slide-in-from-bottom flex items-center gap-2 ${cmdFeedback.ok ? 'bg-bg-3 border-green text-green' : 'bg-bg-3 border-red text-red'}`}>
          <span>{cmdFeedback.ok ? '✓' : '✗'}</span>
          {cmdFeedback.msg}
        </div>
      )}

    </div>
  );
}
