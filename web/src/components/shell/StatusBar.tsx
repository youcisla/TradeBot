"use client";

import { useEffect, useState } from "react";
import { useAppShell } from "@/components/AppShell";
import { cn } from "@/lib/utils";

const SESSION_COLORS: Record<string, string> = {
  asian:   "var(--purple)",
  london:  "var(--blue)",
  overlap: "var(--green)",
  newyork: "var(--orange)",
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

  const equity    = Number(status?.equity    ?? 0);
  const balance   = Number(status?.balance   ?? 0);
  const dailyPnl  = Number(status?.daily_pnl ?? 0);
  const openCount = openTrades.length;
  const session   = intelligence?.session ?? "—";
  const sessionColor = SESSION_COLORS[session] ?? "var(--text-3)";

  const fmt = (v: number) =>
    "$" + Math.abs(v).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

  const pnlColor   = dailyPnl >= 0 ? "var(--positive)" : "var(--negative)";
  const stateColor = isRunning
    ? "var(--positive)"
    : status?.state === "warning"
    ? "var(--warning)"
    : "var(--negative)";

  return (
    <header
      className="fixed top-0 left-0 right-0 z-50 flex items-center bg-[var(--bg-2)]"
      style={{ height: "var(--header-h)", borderBottom: "1px solid var(--border)", padding: "0 var(--space-4)", gap: "var(--space-5)" }}
    >
      {/* Brand + state */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <span
          className="font-mono text-sm font-bold uppercase"
          style={{ fontFamily: "var(--font-mono)", color: "var(--text-1)", letterSpacing: "0.04em" }}
        >
          PulseTrade
        </span>
        <span
          className="rounded-full flex-shrink-0"
          style={{ width: 7, height: 7, background: stateColor, boxShadow: `0 0 6px ${stateColor}` }}
        />
      </div>

      {/* KPIs */}
      <div className="flex-1 flex items-center justify-center gap-4">
        <Kpi label="Equity"  value={fmt(equity)} />
        <Divider />
        <Kpi label="Balance" value={fmt(balance)} />
        <Divider />
        <Kpi label="Today"   value={(dailyPnl >= 0 ? "+" : "-") + fmt(Math.abs(dailyPnl))} color={pnlColor} />
        <Divider />
        <Kpi label="Open"    value={String(openCount)} />
      </div>

      {/* Session + time */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <div
          className="flex items-center gap-1.5 rounded px-2 py-1"
          style={{ border: `1px solid ${sessionColor}50`, background: `${sessionColor}18` }}
        >
          <span className="rounded-full flex-shrink-0" style={{ width: 6, height: 6, background: sessionColor }} />
          <span
            className="font-mono font-bold uppercase"
            style={{ fontFamily: "var(--font-mono)", fontSize: 10, color: sessionColor, letterSpacing: "0.06em" }}
          >
            {session}
          </span>
        </div>
        <span className="font-mono text-sm" style={{ fontFamily: "var(--font-mono)", color: "var(--text-2)" }}>
          {tick}
        </span>
      </div>
    </header>
  );
}

function Kpi({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span
        className="font-mono text-[9px] uppercase tracking-widest"
        style={{ fontFamily: "var(--font-mono)", color: "var(--text-3)", letterSpacing: "0.06em" }}
      >
        {label}
      </span>
      <span
        className="font-mono text-sm font-semibold tabular-nums"
        style={{ fontFamily: "var(--font-mono)", color: color ?? "var(--text-1)", letterSpacing: "-0.01em" }}
      >
        {value}
      </span>
    </div>
  );
}

function Divider() {
  return <span className="w-px h-5 flex-shrink-0" style={{ background: "var(--border)" }} />;
}
