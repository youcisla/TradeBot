"use client";

import { useEffect, useState } from "react";
import { timeSince, timeAgo } from "@/lib/time";

interface BotStatus {
  state: string;
  last_tick: string | null;
  equity: number;
  open_trades: number;
  daily_pnl: number;
  uptime_start: string | null;
  broker_account: string;
  broker_server: string;
  broker_name: string;
  balance: number;
  leverage: number;
}

function Metric({ label, value, color = "#7a8a9a", glow }: {
  label: string; value: string; color?: string; glow?: boolean;
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
      <span style={{
        fontSize: 8.5, fontFamily: "'JetBrains Mono', monospace",
        color: "#2a3a4a", letterSpacing: "0.15em", textTransform: "uppercase",
      }}>
        {label}
      </span>
      <span style={{
        fontSize: 13, fontFamily: "'JetBrains Mono', monospace",
        fontWeight: 700, color,
        textShadow: glow ? `0 0 10px ${color}88` : undefined,
      }}>
        {value}
      </span>
    </div>
  );
}

function Divider() {
  return (
    <div style={{ width: 1, alignSelf: "stretch", background: "#1c1c28", flexShrink: 0, margin: "0 4px" }} />
  );
}

export default function BotStatusBar() {
  const [status, setStatus] = useState<BotStatus | null>(null);

  useEffect(() => {
    let active = true;
    const load = () =>
      fetch("/api/status")
        .then((r) => { if (!r.ok) throw new Error(r.statusText); return r.json(); })
        .then((data) => { if (active) setStatus(data); })
        .catch(() => {});
    load();
    const id = setInterval(load, 8_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  if (!status) {
    return (
      <div style={{
        border: "1px solid #1c1c28", borderRadius: 8,
        background: "#0e0e10", padding: "14px 18px",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11, color: "#2a3a4a",
        display: "flex", alignItems: "center", gap: 8,
      }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#1c2c1c", display: "inline-block" }} />
        Loading system status…
      </div>
    );
  }

  const isRunning  = status.state === "running";
  const isPaused   = status.state === "paused";
  const stateColor = isRunning ? "#00ff41" : isPaused ? "#f5c518" : "#ff4455";
  const stateLabel = status.state?.toUpperCase() ?? "UNKNOWN";
  const connected  = !!status.broker_account;
  const dailyPnl   = Number(status.daily_pnl);
  const pnlColor   = dailyPnl >= 0 ? "#00ff88" : "#ff4455";

  return (
    <div style={{
      border: "1px solid #1c1c28",
      borderRadius: 8,
      background: "linear-gradient(135deg, #0c0c14 0%, #0e0e10 100%)",
      overflow: "hidden",
      position: "relative",
    }}>
      {/* Top accent line */}
      <div style={{
        height: 2,
        background: `linear-gradient(90deg, transparent 0%, ${stateColor}44 20%, ${stateColor}88 50%, ${stateColor}44 80%, transparent 100%)`,
      }} />

      <div style={{ padding: "12px 20px", display: "flex", flexWrap: "wrap", gap: 0, alignItems: "center" }}>

        {/* State indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, paddingRight: 20 }}>
          <div style={{
            width: 8, height: 8, borderRadius: "50%",
            background: stateColor,
            boxShadow: `0 0 8px ${stateColor}, 0 0 16px ${stateColor}55`,
            animation: isRunning ? "statusPulse 2s ease-in-out infinite" : undefined,
          }} />
          <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
            <span style={{
              fontSize: 7.5, color: "#2a3a4a",
              fontFamily: "'JetBrains Mono', monospace",
              letterSpacing: "0.15em", textTransform: "uppercase",
            }}>State</span>
            <span style={{
              fontSize: 12, fontWeight: 700, color: stateColor,
              fontFamily: "'JetBrains Mono', monospace",
              textShadow: `0 0 8px ${stateColor}88`,
              letterSpacing: "0.05em",
            }}>
              {stateLabel}
            </span>
          </div>
        </div>

        <Divider />

        {/* Broker */}
        <div style={{ paddingLeft: 20, paddingRight: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {connected ? (
              <>
                <Metric label="Broker" value={status.broker_server} color="#9aa8b8" />
                <Metric label="Account" value={status.broker_account} color="#00d4ff" glow />
                {status.broker_name && <Metric label="Name" value={status.broker_name} color="#7a8a9a" />}
                <Metric label="Leverage" value={`1:${status.leverage}`} color="#7a8a9a" />
              </>
            ) : (
              <Metric label="Broker" value="DISCONNECTED" color="#ff4455" glow />
            )}
          </div>
        </div>

        <Divider />

        {/* Financial metrics */}
        <div style={{
          paddingLeft: 20, paddingRight: 20,
          display: "flex", gap: 20, alignItems: "center", flexWrap: "wrap",
        }}>
          <Metric label="Balance" value={`$${Number(status.balance || 0).toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`} color="#00ff41" glow />
          <Metric label="Equity"  value={`$${Number(status.equity).toLocaleString("en", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}  color="#00ff41" />
          <Metric
            label="Daily P&L"
            value={`${dailyPnl >= 0 ? "+" : ""}${dailyPnl.toFixed(2)}`}
            color={pnlColor}
            glow
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <span style={{ fontSize: 8.5, fontFamily: "'JetBrains Mono', monospace", color: "#2a3a4a", letterSpacing: "0.15em", textTransform: "uppercase" }}>
              Open
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
              <span style={{ fontSize: 13, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700, color: status.open_trades > 0 ? "#f5c518" : "#4a5568" }}>
                {status.open_trades}
              </span>
              <span style={{ fontSize: 8.5, color: "#2a3a4a", fontFamily: "'JetBrains Mono', monospace" }}>trades</span>
            </div>
          </div>
        </div>

        <Divider />

        {/* Time metrics */}
        <div style={{
          paddingLeft: 20,
          display: "flex", gap: 20, alignItems: "center",
        }}>
          <Metric label="Uptime" value={timeSince(status.uptime_start)} color="#7a8a9a" />
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <span style={{ fontSize: 8.5, fontFamily: "'JetBrains Mono', monospace", color: "#2a3a4a", letterSpacing: "0.15em", textTransform: "uppercase" }}>
              Last Tick
            </span>
            <span style={{
              fontSize: 13, fontFamily: "'JetBrains Mono', monospace", fontWeight: 700,
              color: status.last_tick ? "#7a8a9a" : "#ff4455",
            }}>
              {timeAgo(status.last_tick)}
            </span>
          </div>
        </div>

      </div>

      {/* Bottom scanline */}
      <div style={{
        height: 1,
        background: "repeating-linear-gradient(90deg, transparent, transparent 4px, #1c1c28 4px, #1c1c28 5px)",
        opacity: 0.5,
      }} />

      <style>{`
        @keyframes statusPulse {
          0%,100% { box-shadow: 0 0 8px #00ff41, 0 0 16px #00ff4155; }
          50%      { box-shadow: 0 0 16px #00ff41, 0 0 32px #00ff4188; }
        }
      `}</style>
    </div>
  );
}
