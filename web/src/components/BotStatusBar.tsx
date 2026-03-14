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
    const id = setInterval(load, 10_000);
    return () => { active = false; clearInterval(id); };
  }, []);

  if (!status)
    return (
      <div className="border border-terminal-border rounded p-3 bg-terminal-surface text-matrix-dim text-sm">
        Loading status…
      </div>
    );

  const stateColor =
    status.state === "running"
      ? "text-matrix"
      : status.state === "paused"
        ? "text-yellow-400"
        : "text-red-500";

  const connected = !!status.broker_account;

  return (
    <div className="crt-scanline border border-terminal-border rounded bg-terminal-surface p-4 space-y-3 text-sm">
      {/* Row 1: Broker connection */}
      <div className="flex flex-wrap gap-6 items-center border-b border-terminal-border pb-3">
        <div>
          <span className="text-matrix-dim">BROKER </span>
          {connected ? (
            <span className="text-matrix font-bold">
              {status.broker_server}
            </span>
          ) : (
            <span className="text-yellow-400">DISCONNECTED</span>
          )}
        </div>
        {connected && (
          <>
            <div>
              <span className="text-matrix-dim">ACCOUNT </span>
              <span className="text-matrix font-bold">{status.broker_account}</span>
            </div>
            <div>
              <span className="text-matrix-dim">NAME </span>
              <span className="text-matrix">{status.broker_name || "—"}</span>
            </div>
            <div>
              <span className="text-matrix-dim">LEVERAGE </span>
              <span className="text-matrix">1:{status.leverage}</span>
            </div>
          </>
        )}
      </div>

      {/* Row 2: Trading metrics */}
      <div className="flex flex-wrap gap-6 items-center">
        <div>
          <span className="text-matrix-dim">STATE </span>
          <span className={`font-bold uppercase ${stateColor}`}>
            {status.state}
          </span>
        </div>
        <div>
          <span className="text-matrix-dim">BALANCE </span>
          <span className="text-matrix font-bold">
            ${Number(status.balance || 0).toFixed(2)}
          </span>
        </div>
        <div>
          <span className="text-matrix-dim">EQUITY </span>
          <span className="text-matrix font-bold">
            ${Number(status.equity).toFixed(2)}
          </span>
        </div>
        <div>
          <span className="text-matrix-dim">OPEN </span>
          <span className="text-matrix font-bold">{status.open_trades}</span>
        </div>
        <div>
          <span className="text-matrix-dim">DAILY P&L </span>
          <span
            className={`font-bold ${Number(status.daily_pnl) >= 0 ? "text-matrix" : "text-red-500"}`}
          >
            {Number(status.daily_pnl) >= 0 ? "+" : ""}
            {Number(status.daily_pnl).toFixed(2)}
          </span>
        </div>
        <div>
          <span className="text-matrix-dim">UPTIME </span>
          <span className="text-matrix">{timeSince(status.uptime_start)}</span>
        </div>
        <div>
          <span className="text-matrix-dim">TICK </span>
          <span className="text-matrix">{timeAgo(status.last_tick)}</span>
        </div>
      </div>
    </div>
  );
}
