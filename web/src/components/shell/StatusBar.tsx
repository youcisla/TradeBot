"use client";

import { useEffect, useState } from "react";
import { useAppShell } from "@/components/AppShell";
import { fmtPnl } from "@/lib/format";

const SESSION_COLORS: Record<string, string> = {
  asian:   "#9333EA",
  london:  "#2563EB",
  overlap: "#16A34A",
  newyork: "#D97706",
};

export default function StatusBar() {
  const { status, isRunning, openTrades, intelligence } = useAppShell();
  const [tick, setTick] = useState("—");

  useEffect(() => {
    function update() {
      setTick(
        new Date().toLocaleTimeString("en-US", {
          hour: "2-digit", minute: "2-digit", second: "2-digit",
          hour12: false, timeZone: "Europe/Paris",
        })
      );
    }
    update();
    const id = setInterval(update, 1_000);
    return () => clearInterval(id);
  }, []);

  const equity   = Number(status?.equity ?? 0);
  const balance   = Number(status?.balance ?? 0);
  const dailyPnl  = Number(status?.daily_pnl ?? 0);
  const openCount = openTrades.length;
  const session   = intelligence?.session ?? "—";
  const sessionColor = SESSION_COLORS[session] ?? "var(--text-3)";

  const fmt = (v: number) =>
    "$" + Math.abs(v).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

  const pnlColor = dailyPnl >= 0 ? "var(--green)" : "var(--red)";

  const stateColor = isRunning ? "var(--green)" : status?.state === "warning" ? "var(--amber)" : "var(--red)";

  return (
    <header style={styles.wrapper}>
      {/* Brand + state */}
      <div style={styles.brand}>
        <span style={styles.brandText}>PulseTrade</span>
        <span style={{ ...styles.dot, background: stateColor, boxShadow: `0 0 6px ${stateColor}` }} />
      </div>

      {/* KPIs */}
      <div style={styles.kpis}>
        <Kpi label="Equity"  value={fmt(equity)} />
        <Divider />
        <Kpi label="Balance" value={fmt(balance)} />
        <Divider />
        <Kpi label="Today"   value={(dailyPnl >= 0 ? "+" : "-") + fmt(Math.abs(dailyPnl))} color={pnlColor} />
        <Divider />
        <Kpi label="Open"    value={String(openCount)} />
      </div>

      {/* Session + time */}
      <div style={styles.right}>
        <div style={{ ...styles.sessionBadge, borderColor: sessionColor + "50", background: sessionColor + "18" }}>
          <span style={{ ...styles.sessionDot, background: sessionColor }} />
          <span style={{ ...styles.sessionText, color: sessionColor }}>
            {session.toUpperCase()}
          </span>
        </div>
        <span style={styles.tick}>{tick}</span>
      </div>
    </header>
  );
}

function Kpi({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div style={styles.kpi}>
      <span style={styles.kpiLabel}>{label}</span>
      <span style={{ ...styles.kpiValue, color: color ?? "var(--text-1)" }}>{value}</span>
    </div>
  );
}

function Divider() {
  return <span style={styles.divider} />;
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    position: "fixed",
    top: 0, left: 0, right: 0,
    zIndex: 100,
    height: "var(--header-h)",
    background: "var(--bg-2)",
    borderBottom: "1px solid var(--border)",
    display: "flex",
    alignItems: "center",
    padding: "0 var(--space-4)",
    gap: "var(--space-5)",
  },
  brand: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-2)",
    flexShrink: 0,
  },
  brandText: {
    fontFamily: "var(--font-mono)",
    fontSize: 13,
    fontWeight: 700,
    color: "var(--text-1)",
    letterSpacing: "0.04em",
    textTransform: "uppercase",
  },
  dot: {
    width: 7, height: 7,
    borderRadius: "50%",
    flexShrink: 0,
  },
  kpis: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-4)",
    flex: 1,
    justifyContent: "center",
  },
  kpi: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: 1,
  },
  kpiLabel: {
    fontFamily: "var(--font-mono)",
    fontSize: 9,
    color: "var(--text-3)",
    textTransform: "uppercase",
    letterSpacing: "0.06em",
  },
  kpiValue: {
    fontFamily: "var(--font-mono)",
    fontSize: 13,
    fontWeight: 600,
    letterSpacing: "-0.01em",
  },
  divider: {
    width: 1, height: 20,
    background: "var(--border)",
    flexShrink: 0,
  },
  right: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-3)",
    flexShrink: 0,
  },
  sessionBadge: {
    display: "flex",
    alignItems: "center",
    gap: 5,
    border: "1px solid",
    borderRadius: 6,
    padding: "3px 8px",
  },
  sessionDot: {
    width: 6, height: 6,
    borderRadius: "50%",
    flexShrink: 0,
  },
  sessionText: {
    fontFamily: "var(--font-mono)",
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: "0.06em",
  },
  tick: {
    fontFamily: "var(--font-mono)",
    fontSize: 12,
    color: "var(--text-2)",
  },
};
