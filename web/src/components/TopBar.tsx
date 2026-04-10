"use client";

import { useCallback, useEffect, useState } from "react";

export default function TopBar() {
  const [data, setData] = useState<Record<string, unknown> | null>(null);
  const [tick, setTick] = useState<string>("—");

  const fetch_ = useCallback(async () => {
    try {
      const r = await fetch("/api/status");
      if (r.ok) setData(await r.json());
    } catch { /* keep last */ }
  }, []);

  useEffect(() => {
    fetch_();
    const id = setInterval(fetch_, 8_000);
    return () => clearInterval(id);
  }, [fetch_]);

  // Tick: use browser's local clock, always accurate
  useEffect(() => {
    const update = () => setTick(
      new Date().toLocaleTimeString("en-US", {
        hour: "2-digit", minute: "2-digit", second: "2-digit",
        hour12: false, timeZone: "Europe/Paris",
      })
    );
    update();
    const tid = setInterval(update, 1_000);
    return () => clearInterval(tid);
  }, []);

  if (!data) {
    return (
      <header style={styles.wrapper}>
        <div style={styles.inner}>
          <span style={styles.loading}>Loading…</span>
        </div>
      </header>
    );
  }

  const equity = Number(data.equity ?? 0);
  const balance = Number(data.balance ?? 0);
  const dailyPnl = Number(data.daily_pnl ?? 0);
  const openTrades = Number(data.open_trades ?? 0);
  const state = String(data.state ?? "—");

  const fmt = (v: number) =>
    v >= 0
      ? `$${v.toLocaleString("en-US", { minimumFractionDigits: 2 })}`
      : `-$${Math.abs(v).toLocaleString("en-US", { minimumFractionDigits: 2 })}`;

  const pnlColor = dailyPnl >= 0 ? "#16A34A" : "#DC2626";

  return (
    <header style={styles.wrapper}>
      <div style={styles.inner}>
        {/* Brand */}
        <div style={styles.brand}>
          <span style={styles.brandText}>PulseTrade</span>
          <HealthDot state={state} />
        </div>

        {/* KPIs */}
        <div style={styles.kpis}>
          <Kpi label="Equity" value={fmt(equity)} />
          <Divider />
          <Kpi label="Balance" value={fmt(balance)} />
          <Divider />
          <Kpi label="Today" value={fmt(dailyPnl)} color={pnlColor} prefix={dailyPnl >= 0 ? "+" : ""} />
          <Divider />
          <Kpi label="Open" value={String(openTrades)} />
        </div>

        {/* Session + time */}
        <div style={styles.right}>
          <span style={styles.session}>overlap</span>
          <span style={styles.tick}>{tick}</span>
        </div>
      </div>
    </header>
  );
}

function HealthDot({ state }: { state: string }) {
  const color =
    state === "running" ? "#16A34A" : state === "warning" ? "#D97706" : "#DC2626";
  return (
    <span
      style={{
        display: "inline-block",
        width: 7,
        height: 7,
        borderRadius: "50%",
        background: color,
        boxShadow: `0 0 5px ${color}`,
      }}
    />
  );
}

function Kpi({ label, value, color, prefix = "" }: { label: string; value: string; color?: string; prefix?: string }) {
  return (
    <div style={styles.kpi}>
      <span style={styles.kpiLabel}>{label}</span>
      <span style={{ ...styles.kpiValue, color: color ?? "#111111" }}>
        {prefix}{value}
      </span>
    </div>
  );
}

function Divider() {
  return <span style={styles.divider} />;
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    zIndex: 100,
    background: "#FFFFFF",
    borderBottom: "1px solid #F0F0F0",
    height: 48,
    display: "flex",
    alignItems: "center",
  },
  inner: {
    width: "100%",
    padding: "0 20px",
    display: "flex",
    alignItems: "center",
    gap: 32,
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: 8,
    flexShrink: 0,
  },
  brandText: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 13,
    fontWeight: 700,
    color: "#111111",
    letterSpacing: "0.04em",
    textTransform: "uppercase",
  },
  kpis: {
    display: "flex",
    alignItems: "center",
    gap: 20,
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
    fontSize: 9,
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  kpiValue: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 14,
    fontWeight: 600,
    color: "#111111",
    letterSpacing: "-0.02em",
  },
  divider: {
    width: 1,
    height: 20,
    background: "#E5E7EB",
  },
  right: {
    display: "flex",
    alignItems: "center",
    gap: 12,
    flexShrink: 0,
  },
  session: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 10,
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  tick: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 12,
    color: "#6B7280",
  },
  loading: {
    fontFamily: "'IBM Plex Mono', monospace",
    fontSize: 12,
    color: "#9CA3AF",
  },
};
