"use client";

import { useAppShell } from "@/components/app/AppShellProvider";
import { Clock } from "@/components/app/Clock";
import { useTheme } from "@/components/ThemeProvider";

const SESSION_COLORS: Record<string, string> = {
  asian:   "var(--purple)",
  london:  "var(--blue)",
  overlap: "var(--green)",
  newyork: "var(--orange)",
};

function HeaderKpi({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span
        className="font-mono uppercase tracking-widest"
        style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 9 }}
      >
        {label}
      </span>
      <span
        className="font-mono font-semibold tabular-nums"
        style={{
          color: color ?? "var(--text-1)",
          fontFamily: "var(--font-mono)",
          fontSize: 13,
          letterSpacing: "-0.01em",
        }}
      >
        {value}
      </span>
    </div>
  );
}

export function Header() {
  const { status, isRunning, openTrades, intelligence } = useAppShell();
  const { theme, toggle } = useTheme();

  const equity     = Number(status?.equity      ?? 0);
  const balance   = Number(status?.balance    ?? 0);
  const dailyPnl  = Number(status?.daily_pnl  ?? 0);
  const openCount = openTrades.length;
  const session   = intelligence?.session ?? "—";
  const sessionColor = SESSION_COLORS[session] ?? "var(--text-3)";

  const fmt = (v: number) =>
    "$" + Math.abs(v).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

  const pnlColor  = dailyPnl >= 0 ? "var(--positive)" : "var(--negative)";
  const stateColor = isRunning
    ? "var(--positive)"
    : status?.state === "WARNING"
    ? "var(--warning)"
    : "var(--negative)";

  return (
    <header
      className="fixed top-3 left-4 right-4 z-50 flex items-center gap-6 px-4"
      style={{ backgroundColor: "var(--bg-2)", height: "var(--header-h)", borderBottom: "1px solid var(--border)" }}
    >
      {/* Brand + live indicator */}
      <div className="flex items-center gap-2 flex-shrink-0">
        <span
          className="font-bold tracking-widest uppercase"
          style={{ color: "var(--text-1)", fontFamily: "var(--font-ui)", fontSize: 13 }}
        >
          PulseTrade
        </span>
        <span
          className="rounded-full flex-shrink-0"
          style={{
            width: 7,
            height: 7,
            backgroundColor: stateColor,
            boxShadow: `0 0 6px ${stateColor}`,
            animation: isRunning ? "pulse-dot 2s ease-in-out infinite" : undefined,
          }}
        />
      </div>

      {/* KPI strip */}
      <div className="flex-1 flex items-center justify-center gap-4">
        <HeaderKpi label="Equity"  value={fmt(equity)}   color="var(--accent)" />
        <span className="w-px h-5 flex-shrink-0" style={{ backgroundColor: "var(--border)" }} />
        <HeaderKpi label="Balance" value={fmt(balance)} />
        <span className="w-px h-5 flex-shrink-0" style={{ backgroundColor: "var(--border)" }} />
        <HeaderKpi
          label="Today"
          value={(dailyPnl >= 0 ? "+" : "-") + fmt(Math.abs(dailyPnl))}
          color={pnlColor}
        />
        <span className="w-px h-5 flex-shrink-0" style={{ backgroundColor: "var(--border)" }} />
        <HeaderKpi label="Open" value={String(openCount)} />
      </div>

      {/* Session badge + clock */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <div
          className="flex items-center gap-1.5 rounded px-2 py-1"
          style={{
            border: `1px solid ${sessionColor}50`,
            backgroundColor: `${sessionColor}18`,
          }}
        >
          <span className="rounded-full flex-shrink-0" style={{ width: 6, height: 6, backgroundColor: sessionColor }} />
          <span
            className="font-mono font-bold uppercase tracking-widest"
            style={{ color: sessionColor, fontFamily: "var(--font-mono)", fontSize: 10 }}
          >
            {session}
          </span>
        </div>
        <Clock />
        <button
          onClick={toggle}
          title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          className="flex items-center justify-center rounded transition-colors duration-150"
          style={{
            backgroundColor: "var(--bg-3)",
            border: "1px solid var(--border)",
            borderRadius: 6,
            padding: "4px 8px",
            color: "var(--text-2)",
          }}
        >
          <span
            className="material-symbols-outlined text-sm"
            style={{ fontVariationSettings: "'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 16" }}
          >
            {theme === "dark" ? "wb_sunny" : "dark_mode"}
          </span>
        </button>
      </div>
    </header>
  );
}
