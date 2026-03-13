"use client";

import { useEffect, useState } from "react";

interface BotStatus {
  state: string;
  last_tick: string | null;
  equity: number;
  open_trades: number;
  daily_pnl: number;
  uptime_start: string | null;
}

function timeSince(iso: string | null): string {
  if (!iso) return "—";
  const diff = Date.now() - new Date(iso).getTime();
  const h = Math.floor(diff / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  return `${h}h ${m}m`;
}

function timeAgo(iso: string | null): string {
  if (!iso) return "never";
  const sec = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (sec < 60) return `${sec}s ago`;
  if (sec < 3600) return `${Math.floor(sec / 60)}m ago`;
  return `${Math.floor(sec / 3600)}h ago`;
}

export default function BotStatusBar() {
  const [status, setStatus] = useState<BotStatus | null>(null);

  useEffect(() => {
    const load = () =>
      fetch("/api/status")
        .then((r) => r.json())
        .then(setStatus)
        .catch(() => {});
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
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

  return (
    <div className="crt-scanline border border-terminal-border rounded bg-terminal-surface p-4 flex flex-wrap gap-6 items-center text-sm">
      <div>
        <span className="text-matrix-dim">STATE </span>
        <span className={`font-bold uppercase ${stateColor}`}>
          {status.state}
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
  );
}
