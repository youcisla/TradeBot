"use client";

import { useBotStatus } from "@/lib/swr";
import { Chip, Sdot } from "@/components/ui/chip";

function BrandIcon() {
  return (
    <svg width="22" height="22" viewBox="0 0 22 22">
      <circle
        cx="11"
        cy="11"
        r="10"
        fill="none"
        stroke="var(--accent)"
        strokeWidth="1.2"
      />
      <path
        d="M3 13l5-5 4 4 7-7"
        fill="none"
        stroke="var(--accent)"
        strokeWidth="1.2"
      />
    </svg>
  );
}

function PauseIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="6" y="5" width="4" height="14" />
      <rect x="14" y="5" width="4" height="14" />
    </svg>
  );
}

function BellIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M6 8a6 6 0 1 1 12 0c0 7 3 7 3 9H3c0-2 3-2 3-9z" />
      <path d="M10 21h4" />
    </svg>
  );
}

function SearchIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="7" />
      <path d="m21 21-4.5-4.5" />
    </svg>
  );
}

interface TopStripProps {
  onCmd?: (cmd: string) => void;
  brokerConnected?: boolean;
  dbOk?: boolean;
}

export function TopStrip({
  onCmd,
  brokerConnected = true,
  dbOk = true,
}: TopStripProps) {
  const { data: status } = useBotStatus();

  const equity    = typeof status?.equity    === "number" ? status.equity    : 0;
  const balance   = typeof status?.balance   === "number" ? status.balance   : 0;
  const dailyPnl  = typeof status?.daily_pnl === "number" ? status.daily_pnl : 0;
  const state     = status?.state ?? "—";
  const brokerOk  = !!status?.broker_account;

  const fmt = (v: number) => {
    return "$" + Math.abs(v).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  };

  return (
    <div className="topstrip">
      <div className="brand">
        <div className="brand-mark">
          <BrandIcon />
        </div>
        <div className="brand-text">
          <div className="bn">PulseTrade</div>
          <div className="bs">Operations Console</div>
        </div>
      </div>

      <div className="hbar" />

      <div className="state-pill">
        <Sdot
          tone={state === "RUNNING" ? "pos" : state === "ERROR" ? "neg" : "warn"}
          live={state === "RUNNING"}
        />
        <span style={{ fontWeight: 500, letterSpacing: ".04em" }}>
          {state}
        </span>
        <span className="dim mono" style={{ marginLeft: 8 }}>
          {status?.broker_name ?? "—"} · {Number(status?.leverage ?? 0) > 0 ? `×${status?.leverage}` : "—"}
        </span>
      </div>

      <Chip tone={brokerOk ? "pos" : "neg"}>
        <Sdot tone={brokerOk ? "pos" : "neg"} /> MT5 · {status?.last_scan_latency_ms ?? "—"}ms
      </Chip>
      <Chip tone={dbOk ? "pos" : "neg"}>
        <Sdot tone={dbOk ? "pos" : "neg"} /> DB · live
      </Chip>
      <Chip tone="warn">
        <Sdot tone="warn" live /> Crucix · PRIORITY · ×0.50
      </Chip>

      <div style={{ flex: 1 }} />

      <div className="kpis">
        <div className="kpi">
          <span className="label">Balance</span>
          <span className="mono tnum">{fmt(balance)}</span>
        </div>
        <div className="kpi">
          <span className="label">Equity</span>
          <span
            className="mono tnum"
            style={{ color: equity >= balance ? "var(--pos)" : "var(--neg)" }}
          >
            {fmt(equity)}
          </span>
        </div>
        <div className="kpi">
          <span className="label">Day P&amp;L</span>
          <span
            className="mono tnum"
            style={{ color: dailyPnl >= 0 ? "var(--pos)" : "var(--neg)" }}
          >
            {dailyPnl >= 0 ? "+" : "−"}{fmt(dailyPnl)}
          </span>
        </div>
        <div className="kpi">
          <span className="label">Open Trades</span>
          <span className="mono tnum">
            {status?.open_trades ?? 0}
          </span>
        </div>
      </div>

      <button
        className="iconbtn"
        title="Command palette ⌘K"
        onClick={() => onCmd && onCmd("palette")}
      >
        <SearchIcon />
      </button>
      <button className="iconbtn" title="Pause">
        <PauseIcon />
      </button>
      <button className="iconbtn" title="Notifications">
        <span style={{ position: "relative", display: "flex" }}>
          <BellIcon />
          <span
            style={{
              position: "absolute",
              top: -1,
              right: -1,
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "var(--neg)",
            }}
          />
        </span>
      </button>
    </div>
  );
}
