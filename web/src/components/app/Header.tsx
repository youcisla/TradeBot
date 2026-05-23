"use client";

import { useState } from "react";
import { useAppShell } from "@/components/app/AppShellProvider";
import { Clock } from "@/components/app/Clock";
import { useTheme } from "@/components/ThemeProvider";
import { activateProfile } from "@/lib/swr";

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

function ProfileSwitcher() {
  const { auth } = useAppShell();
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  const activeProfile = auth.profiles.find((p) => p.is_active);
  const locked = auth.botLocked;

  async function handleSelect(profileId: number) {
    if (!auth.sessionToken || loading) return;
    setLoading(true);
    try {
      await activateProfile(profileId, auth.sessionToken);
      window.location.reload();
    } catch { /* ignore */ }
    finally { setLoading(false); setOpen(false); }
  }

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        title="Switch broker profile"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          padding: "4px 10px",
          background: "var(--bg-3)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          fontSize: 12,
          fontFamily: "var(--font-ui)",
          color: locked ? "var(--warning)" : "var(--text-1)",
          cursor: "pointer",
        }}
      >
        <span
          style={{
            width: 6, height: 6, borderRadius: "50%",
            background: activeProfile
              ? (activeProfile.is_demo ? "#0A84FF" : "#30D158")
              : "var(--warning)",
          }}
        />
        {activeProfile?.profile_label ?? (locked ? "Locked" : "No profile")}
      </button>
      {open && (
        <div
          style={{
            position: "absolute", top: "100%", right: 0, marginTop: 4,
            background: "var(--bg-2)", border: "1px solid var(--border)",
            borderRadius: 10, minWidth: 180, zIndex: 999,
            boxShadow: "0 8px 24px rgba(0,0,0,0.4)",
            overflow: "hidden",
          }}
        >
          {auth.profiles.map((p) => (
            <button
              key={p.id}
              onClick={() => handleSelect(p.id)}
              disabled={loading}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                width: "100%", padding: "10px 14px",
                background: p.is_active ? "rgba(10,132,255,0.1)" : "transparent",
                border: "none",
                fontSize: 13, fontFamily: "var(--font-ui)",
                color: "var(--text-1)",
                cursor: loading ? "not-allowed" : "pointer",
                textAlign: "left",
              }}
            >
              <span
                style={{
                  width: 8, height: 8, borderRadius: "50%", flexShrink: 0,
                  background: p.is_demo ? "#0A84FF" : "#30D158",
                }}
              />
              <span style={{ flex: 1 }}>{p.profile_label}</span>
              {p.is_active && <span style={{ fontSize: 10, color: "#0A84FF" }}>ACTIVE</span>}
            </button>
          ))}
          <button
            onClick={() => { setOpen(false); window.location.href = "/dashboard/profiles"; }}
            style={{
              display: "flex", alignItems: "center", gap: 8,
              width: "100%", padding: "10px 14px",
              background: "transparent",
              border: "none",
              borderTop: "1px solid var(--border)",
              fontSize: 12, fontFamily: "var(--font-ui)",
              color: "var(--text-3)",
              cursor: "pointer",
            }}
          >
            Manage profiles →
          </button>
        </div>
      )}
    </div>
  );
}

export function Header() {
  const { status, isRunning, openTrades, intelligence, auth } = useAppShell();
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
        <HeaderKpi label="Equity"  value={fmt(equity)}   color="var(--text-1)" />
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

      {/* Session badge + clock + profile switcher */}
      <div className="flex items-center gap-3 flex-shrink-0">
        <ProfileSwitcher />
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
