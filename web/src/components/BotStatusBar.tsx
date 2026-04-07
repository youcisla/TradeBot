"use client";

import useSWR from "swr";
import { timeSince } from "@/lib/time";

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

interface ChipProps {
  label: string;
  value: string;
  valueColor?: string;
}

function Chip({ label, value, valueColor = "#FFFFFF" }: ChipProps) {
  return (
    <div
      style={{
        background: "#1C1C1E",
        borderRadius: 10,
        padding: "8px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 3,
        flexShrink: 0,
      }}
    >
      <span
        style={{
          fontSize: 11,
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          color: "rgba(235,235,245,0.4)",
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif',
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontSize: 15,
          fontWeight: 600,
          color: valueColor,
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif',
          letterSpacing: "-0.01em",
        }}
      >
        {value}
      </span>
    </div>
  );
}

function StateChip({ state }: { state: string }) {
  const isRunning = state === "running";
  const isPaused = state === "paused";
  const dotColor = isRunning ? "#30D158" : isPaused ? "#FF9F0A" : "#8E8E93";
  const label = state?.toUpperCase() ?? "—";

  return (
    <div
      style={{
        background: "#1C1C1E",
        borderRadius: 10,
        padding: "8px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 3,
        flexShrink: 0,
      }}
    >
      <span
        style={{
          fontSize: 11,
          fontWeight: 600,
          textTransform: "uppercase",
          letterSpacing: "0.06em",
          color: "rgba(235,235,245,0.4)",
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif',
        }}
      >
        State
      </span>
      <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: dotColor,
            display: "inline-block",
            flexShrink: 0,
            boxShadow: isRunning ? `0 0 6px ${dotColor}` : undefined,
            animation: isRunning ? "statusDotPulse 2s ease-in-out infinite" : undefined,
          }}
        />
        <span
          style={{
            fontSize: 15,
            fontWeight: 600,
            color: dotColor,
            fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif',
            letterSpacing: "0.01em",
          }}
        >
          {label}
        </span>
      </div>
    </div>
  );
}

const fetcher = (url: string) => fetch(url).then(r => r.json());

export default function BotStatusBar() {
  const { data: status } = useSWR<BotStatus>("/api/status", fetcher, {
    refreshInterval: 8_000,
    revalidateOnFocus: true,
    keepPreviousData: true,
  });

  if (!status) {
    return (
      <div
        style={{
          background: "#1C1C1E",
          borderRadius: 10,
          padding: "10px 16px",
          display: "flex",
          alignItems: "center",
          gap: 8,
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif',
        }}
      >
        <span
          style={{
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: "#8E8E93",
            display: "inline-block",
          }}
        />
        <span style={{ fontSize: 14, color: "rgba(235,235,245,0.4)" }}>
          Loading status…
        </span>
      </div>
    );
  }

  const dailyPnl = Number(status.daily_pnl);
  const pnlPositive = dailyPnl >= 0;
  const pnlColor = pnlPositive ? "#30D158" : "#FF453A";
  const pnlFormatted = `${pnlPositive ? "+" : ""}${dailyPnl.toFixed(2)}`;

  const equity = Number(status.equity).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });

  const balance = Number(status.balance || 0).toLocaleString("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });

  return (
    <>
      <div
        style={{
          display: "flex",
          gap: 8,
          overflowX: "auto",
          paddingBottom: 2,
          scrollbarWidth: "none",
          WebkitOverflowScrolling: "touch",
        } as React.CSSProperties}
      >
        <StateChip state={status.state} />
        <Chip label="Equity" value={equity} />
        <Chip label="Balance" value={balance} />
        <Chip
          label="Open Trades"
          value={String(status.open_trades)}
          valueColor={status.open_trades > 0 ? "#FF9F0A" : "#FFFFFF"}
        />
        <Chip label="Daily P&L" value={pnlFormatted} valueColor={pnlColor} />
        <Chip label="Uptime" value={timeSince(status.uptime_start)} valueColor="rgba(235,235,245,0.6)" />
      </div>

      <style>{`
        @keyframes statusDotPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
      `}</style>
    </>
  );
}
