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
