"use client";

import { useEffect, useMemo, useState } from "react";
import ConfirmModal from "@/components/ConfirmModal";

//  Types 

interface BotStatus {
  state: string;
  last_tick?: string;
  equity?: number | string;
  open_trades?: number;
  daily_pnl?: number | string;
  uptime_start?: string;
  broker_account?: string;
  broker_server?: string;
  broker_name?: string;
  balance?: number | string;
  leverage?: number | string;
}

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
  open_time?: string;
  pnl?: number;
}

//  Agent pipeline 

const AGENTS = [
  { key: "crucix",        label: "Crucix",    color: "#5AC8FA" },
  { key: "market",        label: "Market",    color: "#0A84FF" },
  { key: "analysis",      label: "Analysis",  color: "#E8EAED" },
  { key: "strategy",      label: "Strategy",  color: "#34C759" },
  { key: "neural",        label: "Neural",    color: "#BF5AF2" },
  { key: "council",       label: "Council",   color: "#FF9F0A" },
  { key: "risk",          label: "Risk",      color: "#FF3B30" },
  { key: "execution",     label: "Execution", color: "#E8EAED" },
  { key: "trade_manager", label: "TradeMgr",  color: "#5AC8FA" },
];

//  Helpers 

function fmtUsd(v: number): string {
  const abs = Math.abs(v);
  const f = abs.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return (v < 0 ? "-$" : "$") + f;
}

function fmtPct(v: number): string {
  return (v >= 0 ? "+" : "") + v.toFixed(2) + "%";
}

function ageMs(ts: string | undefined): number {
  if (!ts) return Infinity;
  return Date.now() - new Date(ts).getTime();
}

function relTime(ts: string | undefined): string {
  if (!ts) return "—";
  const ms = ageMs(ts);
  if (ms < 60_000)    return Math.floor(ms / 1_000)    + "s ago";
  if (ms < 3_600_000) return Math.floor(ms / 60_000)   + "m ago";
  return                     Math.floor(ms / 3_600_000) + "h ago";
}

function tradeAge(ts: string | undefined): string {
  if (!ts) return "—";
  const ms = ageMs(ts);
  if (ms < 3_600_000)  return Math.floor(ms / 60_000)    + "m";
  if (ms < 86_400_000) return Math.floor(ms / 3_600_000) + "h";
  return                      Math.floor(ms / 86_400_000) + "d";
}

function evTs(ev: AgentEvent | undefined): string | undefined {
  return ev?.created_at ?? ev?.ts;
}

function evMsg(ev: AgentEvent | undefined): string {
  return ev?.message ?? ev?.msg ?? "";
}

//  Page 

export default function CommandCenterPage() {
  const [status,      setStatus]      = useState<BotStatus | null>(null);
  const [events,      setEvents]      = useState<AgentEvent[]>([]);
  const [positions,   setPositions]   = useState<Trade[]>([]);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [confirmCfg,  setConfirmCfg]  = useState({
    title: "", body: "", confirmLabel: "Confirm", danger: false, cmd: "",
  });

  // Poll status every 8 s
  useEffect(() => {
    let active = true;
    const run = async () => {
      try { const r = await fetch("/api/status"); if (active) setStatus(await r.json()); } catch { /* silent */ }
    };
    run(); const id = setInterval(run, 8_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  // Poll events every 10 s
  useEffect(() => {
    let active = true;
    const run = async () => {
      try {
        const r = await fetch("/api/events?limit=50");
        const d = await r.json();
        if (active) setEvents(Array.isArray(d) ? d : (d.events ?? []));
      } catch { /* silent */ }
    };
    run(); const id = setInterval(run, 10_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  // Poll open positions every 14 s
  useEffect(() => {
    let active = true;
    const run = async () => {
      try {
        const r = await fetch("/api/trades");
        const d = await r.json();
        if (active) setPositions(Array.isArray(d) ? d : (d.trades ?? []));
      } catch { /* silent */ }
    };
    run(); const id = setInterval(run, 14_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  // Latest event per agent (first occurrence wins = most recent, since events are DESC)
  const agentLatest = useMemo(() => {
    const map: Record<string, AgentEvent> = {};
    for (const ev of events) {
      const key = ev.agent?.toLowerCase().replace(/[^a-z_]/g, "");
      if (key && !map[key]) map[key] = ev;
    }
    return map;
  }, [events]);

  const councilEv = events.find(e => e.agent?.toLowerCase() === "council");
  const riskEv    = events.find(e => e.agent?.toLowerCase() === "risk");

  const isRunning = status?.state === "running";
  const equity    = Number(status?.equity    ?? 0);
  const balance   = Number(status?.balance   ?? 0);
  const dailyPnl  = Number(status?.daily_pnl ?? 0);
  const dailyPct  = equity > 0 ? (dailyPnl / equity) * 100 : 0;
  const openCount = status?.open_trades ?? positions.length;

  const sendCommand = async (command: string) => {
    try {
      await fetch("/api/commands", {
        method:  "POST",
        headers: { "Content-Type": "application/json" },
        body:    JSON.stringify({ command }),
      });
    } catch { /* silent */ }
  };

  function openConfirm(cfg: typeof confirmCfg) {
    setConfirmCfg(cfg);
    setConfirmOpen(true);
  }

  //  KPI card style helper
  const kpiCard: React.CSSProperties = {
    background:   "rgba(255,255,255,0.04)",
    border:       "1px solid rgba(255,255,255,0.09)",
    borderRadius: 12,
    padding:      "18px 20px",
  };
  const kpiLabel: React.CSSProperties = {
    fontSize:      11,
    color:         "rgba(232,234,237,0.55)",
    marginBottom:  6,
    letterSpacing: 0.5,
    textTransform: "uppercase",
  };
  const kpiValue: React.CSSProperties = {
    fontSize:    24,
    fontWeight:  700,
    color:       "#E8EAED",
    fontFamily:  '"SF Mono", SFMono-Regular, ui-monospace, monospace',
    letterSpacing: -1,
  };
  const kpiSub: React.CSSProperties = {
    fontSize:  12,
    color:     "rgba(232,234,237,0.30)",
    marginTop: 4,
  };

  return (
    <>
      <style>{`
        @keyframes dotPulse {
          0%,100% { opacity:1; transform:scale(1); }
          50%      { opacity:0.45; transform:scale(0.78); }
        }
        @keyframes livePulse {
          0%,100% { box-shadow:0 0 0 0 rgba(52,199,89,.55); }
          50%      { box-shadow:0 0 0 5px rgba(52,199,89,0); }
        }
      `}</style>

      {/*  KPI Strip  */}
      <div style={{
        display:             "grid",
        gridTemplateColumns: "repeat(4,1fr)",
        gap:                 12,
        marginBottom:        20,
      }}>

        {/* Equity */}
        <div style={kpiCard}>
          <div style={kpiLabel}>Equity</div>
          <div style={kpiValue}>{fmtUsd(equity)}</div>
          <div style={kpiSub}>Balance: {fmtUsd(balance)}</div>
        </div>

        {/* Daily P&L */}
        <div style={kpiCard}>
          <div style={kpiLabel}>Daily P&L</div>
          <div style={{ ...kpiValue, color: dailyPnl > 0 ? "#34C759" : dailyPnl < 0 ? "#FF3B30" : "#E8EAED" }}>
            {fmtUsd(dailyPnl)}
          </div>
          <div style={{ ...kpiSub, color: dailyPnl > 0 ? "#34C759" : dailyPnl < 0 ? "#FF3B30" : "rgba(232,234,237,0.30)" }}>
            {fmtPct(dailyPct)}
          </div>
        </div>

        {/* Open Trades */}
        <div style={kpiCard}>
          <div style={kpiLabel}>Open Trades</div>
          <div style={kpiValue}>{openCount}</div>
          <div style={kpiSub}>Live positions</div>
        </div>

        {/* Bot State */}
        <div style={kpiCard}>
          <div style={kpiLabel}>Bot State</div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <span style={{
              width: 10, height: 10, borderRadius: "50%", flexShrink: 0,
              display:   "inline-block",
              background: isRunning ? "#34C759" : "#FF3B30",
              animation:  isRunning ? "dotPulse 1.8s ease-in-out infinite" : undefined,
            }} />
            <span style={{ ...kpiValue, fontSize: 22 }}>
              {(status?.state ?? "offline").charAt(0).toUpperCase() +
               (status?.state ?? "offline").slice(1)}
            </span>
          </div>
          <div style={kpiSub}>Last tick {relTime(status?.last_tick)}</div>
        </div>
      </div>

      {/*  Main Row  */}
      <div style={{ display: "flex", gap: 16, alignItems: "flex-start", marginBottom: 16 }}>

        {/* Pipeline Pulse  */}
        <div style={{
          flex:         1,
          background:   "rgba(255,255,255,0.04)",
          border:       "1px solid rgba(255,255,255,0.09)",
          borderRadius: 12,
          padding:      "20px",
        }}>
          <div style={{
            fontSize: 11, fontWeight: 600, color: "rgba(232,234,237,0.55)",
            marginBottom: 14, letterSpacing: 0.5, textTransform: "uppercase",
          }}>
            Agent Pipeline
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            {AGENTS.map(agent => {
              const ev    = agentLatest[agent.key];
              const ts    = evTs(ev);
              const ms    = ageMs(ts);
              const fresh = ms < 60_000;
              const warm  = ms < 300_000;
              const msg   = evMsg(ev);
              return (
                <div key={agent.key} style={{
                  display:      "flex",
                  alignItems:   "center",
                  gap:          10,
                  padding:      "8px 10px",
                  borderRadius: 8,
                  background:   fresh ? `${agent.color}10` : "transparent",
                  border:       `1px solid ${fresh ? agent.color + "22" : "transparent"}`,
                  transition:   "background .3s",
                }}>
                  {/* Status dot */}
                  <span style={{
                    width:        7, height: 7, borderRadius: "50%", flexShrink: 0,
                    display:      "inline-block",
                    background:   fresh ? agent.color : warm ? `${agent.color}88` : "rgba(232,234,237,0.15)",
                    animation:    fresh ? "dotPulse 1.8s ease-in-out infinite" : undefined,
                  }} />
                  {/* Agent label */}
                  <span style={{
                    width: 84, flexShrink: 0, fontSize: 13, fontWeight: 600,
                    color: fresh ? agent.color : warm ? `${agent.color}CC` : "rgba(232,234,237,0.30)",
                  }}>
                    {agent.label}
                  </span>
                  {/* Last message */}
                  <span style={{
                    flex: 1, fontSize: 12, color: "rgba(232,234,237,0.55)",
                    overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                  }}>
                    {msg || "—"}
                  </span>
                  {/* Relative time */}
                  <span style={{ fontSize: 11, color: "rgba(232,234,237,0.30)", whiteSpace: "nowrap", flexShrink: 0 }}>
                    {relTime(ts)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column  */}
        <div style={{ width: 380, flexShrink: 0, display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Live Positions */}
          <div style={{
            background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.09)",
            borderRadius: 12, padding: "18px 20px",
          }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(232,234,237,0.55)", marginBottom: 12, letterSpacing: 0.5, textTransform: "uppercase" }}>
              Live Positions
            </div>
            {positions.length === 0 ? (
              <div style={{ fontSize: 13, color: "rgba(232,234,237,0.30)", textAlign: "center", padding: "20px 0" }}>
                No open positions
              </div>
            ) : (
              <>
                {/* Column headers */}
                <div style={{
                  display: "grid", gridTemplateColumns: "1fr 52px 80px 44px", gap: 8,
                  fontSize: 11, color: "rgba(232,234,237,0.30)", letterSpacing: 0.4, textTransform: "uppercase",
                  paddingBottom: 8, borderBottom: "1px solid rgba(255,255,255,0.06)", marginBottom: 6,
                }}>
                  <span>Symbol</span><span>Dir</span>
                  <span style={{ textAlign: "right" }}>Entry</span>
                  <span style={{ textAlign: "right" }}>Age</span>
                </div>
                {/* Rows */}
                {positions.slice(0, 6).map(pos => {
                  const isLong = /buy|long/i.test(pos.direction);
                  return (
                    <div key={pos.id} style={{
                      display: "grid", gridTemplateColumns: "1fr 52px 80px 44px", gap: 8,
                      fontSize: 13, padding: "5px 0", alignItems: "center",
                      borderBottom: "1px solid rgba(255,255,255,0.04)",
                    }}>
                      <span style={{ color: "#E8EAED", fontWeight: 600 }}>{pos.symbol}</span>
                      <span style={{ color: isLong ? "#34C759" : "#FF3B30", fontSize: 11, fontWeight: 700, letterSpacing: 0.3 }}>
                        {isLong ? "LONG" : "SHORT"}
                      </span>
                      <span style={{ color: "rgba(232,234,237,0.55)", fontFamily: '"SF Mono",monospace', fontSize: 12, textAlign: "right" }}>
                        {pos.entry_price.toFixed(5)}
                      </span>
                      <span style={{ color: "rgba(232,234,237,0.30)", fontSize: 11, textAlign: "right" }}>
                        {tradeAge(pos.open_time)}
                      </span>
                    </div>
                  );
                })}
                {positions.length > 6 && (
                  <div style={{ fontSize: 12, color: "rgba(232,234,237,0.30)", marginTop: 8, textAlign: "center" }}>
                    +{positions.length - 6} more
                  </div>
                )}
              </>
            )}
          </div>

          {/* Last Signal */}
          <div style={{
            background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.09)",
            borderRadius: 12, padding: "18px 20px",
          }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: "rgba(232,234,237,0.55)", marginBottom: 14, letterSpacing: 0.5, textTransform: "uppercase" }}>
              Last Signal
            </div>
            {/* Council */}
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 11, color: "rgba(232,234,237,0.30)", marginBottom: 5, letterSpacing: 0.3, textTransform: "uppercase" }}>Council</div>
              <div style={{ fontSize: 13, color: "#FF9F0A", lineHeight: 1.5 }}>
                {evMsg(councilEv).slice(0, 80) || "—"}
              </div>
              <div style={{ fontSize: 11, color: "rgba(232,234,237,0.30)", marginTop: 4 }}>{relTime(evTs(councilEv))}</div>
            </div>
            <div style={{ borderTop: "1px solid rgba(255,255,255,0.06)", marginBottom: 14 }} />
            {/* Risk */}
            <div>
              <div style={{ fontSize: 11, color: "rgba(232,234,237,0.30)", marginBottom: 5, letterSpacing: 0.3, textTransform: "uppercase" }}>Risk</div>
              <div style={{ fontSize: 13, color: "#E8EAED", lineHeight: 1.5 }}>
                {evMsg(riskEv).slice(0, 80) || "—"}
              </div>
              <div style={{ fontSize: 11, color: "rgba(232,234,237,0.30)", marginTop: 4 }}>{relTime(evTs(riskEv))}</div>
            </div>
          </div>
        </div>
      </div>

      {/*  Command Bar  */}
      <div style={{
        background:   "rgba(255,255,255,0.04)",
        border:       "1px solid rgba(255,255,255,0.09)",
        borderRadius: 12,
        padding:      "16px 20px",
        display:      "flex",
        alignItems:   "center",
        flexWrap:     "wrap",
        gap:          12,
      }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: "rgba(232,234,237,0.55)", letterSpacing: 0.5, textTransform: "uppercase", marginRight: 4 }}>
          Commands
        </span>

        {/* Pause / Resume */}
        <button
          onClick={() => sendCommand(isRunning ? "pause" : "resume")}
          style={{
            height: 38, padding: "0 20px",
            background:   isRunning ? "rgba(255,159,10,0.12)" : "rgba(52,199,89,0.12)",
            border:       `1px solid ${isRunning ? "rgba(255,159,10,0.35)" : "rgba(52,199,89,0.35)"}`,
            borderRadius: 8,
            color:        isRunning ? "#FF9F0A" : "#34C759",
            fontSize: 14, fontWeight: 600, cursor: "pointer", fontFamily: "inherit",
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.opacity = ".75"; }}
          onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.opacity = "1"; }}
        >
          {isRunning ? "Pause Bot" : "Resume Bot"}
        </button>

        {/* Close All Positions */}
        <button
          onClick={() => openConfirm({
            title:        "Close All Positions",
            body:         "This will immediately close every open position. This action cannot be undone.",
            confirmLabel: "Close All",
            danger:       true,
            cmd:          "close_all",
          })}
          style={{
            height: 38, padding: "0 20px",
            background: "rgba(255,59,48,0.10)", border: "1px solid rgba(255,59,48,0.35)",
            borderRadius: 8, color: "#FF3B30",
            fontSize: 14, fontWeight: 600, cursor: "pointer", fontFamily: "inherit",
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.opacity = ".75"; }}
          onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.opacity = "1"; }}
        >
          Close All Positions
        </button>

        {/* Force Weekly Snap */}
        <button
          onClick={() => sendCommand("force_weekly_snap")}
          style={{
            height: 38, padding: "0 20px",
            background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)",
            borderRadius: 8, color: "#E8EAED",
            fontSize: 14, fontWeight: 600, cursor: "pointer", fontFamily: "inherit",
          }}
          onMouseEnter={e => { (e.currentTarget as HTMLButtonElement).style.opacity = ".75"; }}
          onMouseLeave={e => { (e.currentTarget as HTMLButtonElement).style.opacity = "1"; }}
        >
          Force Weekly Snap
        </button>
      </div>

      {/*  Confirm Modal  */}
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