"use client";

import { useCallback, useEffect, useState } from "react";

interface StatusData {
  equity: number;
  balance: number;
  daily_pnl: number;
  state: string;
  last_tick: string | null;
  open_trades: number;
}

function fmtUsd(v: number | string): string {
  const n = typeof v === "string" ? parseFloat(v) : v;
  if (isNaN(n)) return "—";
  const abs = Math.abs(n);
  const f = abs.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  return (n < 0 ? "-$" : "$") + f;
}

function HealthDot({ state }: { state: string }) {
  const color =
    state === "running" ? "#16A34A" : state === "warning" ? "#D97706" : "#DC2626";
  return (
    <span
      style={{
        display: "inline-block",
        width: 8,
        height: 8,
        borderRadius: "50%",
        background: color,
        boxShadow: `0 0 6px ${color}`,
      }}
    />
  );
}

export default function StatusStrip() {
  const [data, setData] = useState<StatusData | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      const r = await fetch("/api/status");
      if (r.ok) {
        const json = await r.json();
        setData(json);
      }
    } catch {
      // keep last data on failure
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    const id = setInterval(fetchStatus, 8_000);
    return () => clearInterval(id);
  }, [fetchStatus]);

  if (!data) {
    return (
      <header style={styles.wrapper}>
        <div style={styles.inner}>
          <span style={styles.loading}>Loading…</span>
        </div>
      </header>
    );
  }

  const pnl = typeof data.daily_pnl === "string"
    ? parseFloat(data.daily_pnl)
    : data.daily_pnl;
  const isProfit = pnl >= 0;
  const pnlColor = isProfit ? "#16A34A" : "#DC2626";

  return (
    <header style={styles.wrapper}>
      <div style={styles.inner}>
        {/* Left: brand + health */}
        <div style={styles.group}>
          <span style={styles.brand}>PulseTrade</span>
          <HealthDot state={data.state} />
          <span style={styles.label}>{data.state}</span>
        </div>

        {/* Center: KPIs */}
        <div style={styles.kpiRow}>
          <Kpi label="Equity" value={fmtUsd(data.equity)} />
          <Kpi label="Balance" value={fmtUsd(data.balance)} />
          <Kpi
            label="Today"
            value={fmtUsd(pnl)}
            color={pnlColor}
            prefix={pnl >= 0 ? "+" : ""}
          />
          <Kpi
            label="Open"
            value={String(data.open_trades)}
          />
        </div>

        {/* Right: last tick */}
        <div style={styles.group}>
          <span style={styles.tick}>
            {data.last_tick
              ? new Date(data.last_tick).toLocaleTimeString("en-US", {
                  hour: "2-digit",
                  minute: "2-digit",
                  second: "2-digit",
                  hour12: false,
                  timeZone: "Europe/Paris",
                })
              : "—"}
          </span>
        </div>
      </div>
    </header>
  );
}

function Kpi({
  label,
  value,
  color,
  prefix = "",
}: {
  label: string;
  value: string;
  color?: string;
  prefix?: string;
}) {
  return (
    <div style={styles.kpi}>
      <span style={styles.kpiLabel}>{label}</span>
      <span
        style={{
          fontFamily: "'IBM Plex Mono', monospace",
          fontSize: 14,
          fontWeight: 600,
          color: color ?? "#111111",
          letterSpacing: "-0.02em",
        }}
      >
        {prefix}
        {value}
      </span>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    zIndex: 100,
    background: "#FFFFFF",
    borderBottom: "1px solid #F5F5F7",
    boxShadow: "0 1px 4px rgba(0,0,0,0.06)",
    height: 48,
    display: "flex",
    alignItems: "center",
  },
  inner: {
    width: "100%",
    padding: "0 20px",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 24,
  },
  group: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    flexShrink: 0,
  },
  brand: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 13,
    fontWeight: 700,
    color: "#111111",
    letterSpacing: "0.04em",
    textTransform: "uppercase",
  },
  label: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    color: "#9CA3AF",
    textTransform: "capitalize",
  },
  kpiRow: {
    display: "flex",
    alignItems: "center",
    gap: 28,
    flex: 1,
    justifyContent: "center",
  },
  kpi: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 2,
  },
  kpiLabel: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  tick: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 11,
    color: "#9CA3AF",
  },
  loading: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 12,
    color: "#9CA3AF",
  },
};
