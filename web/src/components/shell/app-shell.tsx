"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAppShell } from "@/components/AppShell";
import { fmtPnl } from "@/lib/format";

const TABS = [
  { href: "/dashboard",         label: "Command",  icon: "dashboard"        },
  { href: "/dashboard/chart",  label: "Chart",    icon: "candlestick_chart" },
  { href: "/dashboard/history", label: "History",  icon: "history"           },
  { href: "/dashboard/risk",   label: "Risk",     icon: "shield"           },
  { href: "/dashboard/system", label: "System",   icon: "settings"         },
];

const SESSION_COLORS: Record<string, string> = {
  asian:   "#9333EA",
  london:  "#2563EB",
  overlap: "#16A34A",
  newyork: "#D97706",
};

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { status, isRunning, openTrades, intelligence } = useAppShell();

  const equity  = Number(status?.equity  ?? 0);
  const balance = Number(status?.balance ?? 0);
  const dailyPnl = Number(status?.daily_pnl ?? 0);
  const openCount = openTrades.length;
  const session = intelligence?.session ?? "—";
  const sessionColor = SESSION_COLORS[session] ?? "var(--text-3)";

  const fmt = (v: number) =>
    "$" + Math.abs(v).toLocaleString("en-US", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });

  const pnlColor = dailyPnl >= 0 ? "var(--green)" : "var(--red)";
  const stateColor = isRunning
    ? "var(--green)"
    : status?.state === "warning"
    ? "var(--orange)"
    : "var(--red)";

  function isActive(href: string) {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  }

  return (
    <div className="min-h-screen bg-[var(--bg)] text-[var(--text-1)]">
      {/* ── Header ── */}
      <header
        className="fixed top-0 left-0 right-0 z-50 flex items-center gap-6 px-4"
        style={{
          height: "var(--header-h)",
          background: "var(--bg-2)",
          borderBottom: "1px solid var(--border)",
        }}
      >
        {/* Brand */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <span
            className="font-mono font-bold text-sm tracking-widest uppercase"
            style={{ color: "var(--text-1)", fontFamily: "var(--font-mono)" }}
          >
            PulseTrade
          </span>
          <span
            className="rounded-full flex-shrink-0"
            style={{
              width: 7, height: 7,
              background: stateColor,
              boxShadow: `0 0 6px ${stateColor}`,
            }}
          />
        </div>

        {/* KPIs */}
        <div className="flex-1 flex items-center justify-center gap-4">
          <HeaderKpi label="Equity"  value={fmt(equity)} />
          <span className="w-px h-5 flex-shrink-0" style={{ background: "var(--border)" }} />
          <HeaderKpi label="Balance" value={fmt(balance)} />
          <span className="w-px h-5 flex-shrink-0" style={{ background: "var(--border)" }} />
          <HeaderKpi
            label="Today"
            value={(dailyPnl >= 0 ? "+" : "-") + fmt(Math.abs(dailyPnl))}
            color={pnlColor}
          />
          <span className="w-px h-5 flex-shrink-0" style={{ background: "var(--border)" }} />
          <HeaderKpi label="Open" value={String(openCount)} />
        </div>

        {/* Session + clock */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <div
            className="flex items-center gap-1.5 rounded-md px-2 py-1"
            style={{
              border: `1px solid ${sessionColor}50`,
              background: `${sessionColor}18`,
            }}
          >
            <span className="rounded-full flex-shrink-0" style={{ width: 6, height: 6, background: sessionColor }} />
            <span
              className="font-mono text-xs font-bold tracking-widest uppercase"
              style={{ color: sessionColor, fontFamily: "var(--font-mono)", fontSize: 10 }}
            >
              {session}
            </span>
          </div>
          <Clock />
        </div>
      </header>

      {/* ── Desktop sidebar ── */}
      <nav
        className="hidden lg:flex flex-col gap-1 py-3 px-2"
        style={{
          position: "fixed",
          top: "var(--header-h)",
          left: 0,
          bottom: 0,
          width: "var(--sidebar-w)",
          background: "var(--bg-2)",
          borderRight: "1px solid var(--border)",
          zIndex: 90,
        }}
      >
        {TABS.map(({ href, label, icon }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-3 rounded px-3 py-2.5 mx-1 transition-colors"
              style={{
                background: active ? "var(--bg-3)" : "transparent",
                color: active ? "var(--accent)" : "var(--text-2)",
                textDecoration: "none",
              }}
            >
              <span
                className="material-symbols-outlined text-base flex-shrink-0"
                style={{
                  fontVariationSettings: active
                    ? "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 18"
                    : "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 18",
                }}
              >
                {icon}
              </span>
              <span
                className="text-xs font-medium tracking-wide"
                style={{
                  fontFamily: "var(--font-ui)",
                  fontWeight: active ? 700 : 500,
                  letterSpacing: "0.03em",
                }}
              >
                {label}
              </span>
            </Link>
          );
        })}
      </nav>

      {/* ── Mobile bottom bar ── */}
      <nav
        className="lg:hidden flex items-center justify-around"
        style={{
          position: "fixed",
          bottom: 0, left: 0, right: 0,
          height: "var(--nav-bottom-h)",
          background: "var(--bg-2)",
          borderTop: "1px solid var(--border)",
          zIndex: 100,
        }}
      >
        {TABS.map(({ href, label, icon }) => {
          const active = isActive(href);
          return (
            <Link
              key={href}
              href={href}
              className="flex flex-col items-center justify-center gap-0.5 py-1 px-3 min-w-14"
              style={{ textDecoration: "none", color: active ? "var(--accent)" : "var(--text-3)" }}
            >
              <span
                className="material-symbols-outlined"
                style={{
                  fontSize: 22,
                  fontVariationSettings: active
                    ? "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 22"
                    : "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 22",
                }}
              >
                {icon}
              </span>
              {active && (
                <span
                  className="text-xs font-bold tracking-widest uppercase"
                  style={{
                    fontFamily: "var(--font-ui)",
                    fontSize: 9,
                    letterSpacing: "0.04em",
                  }}
                >
                  {label}
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* ── Desktop main ── */}
      <main
        className="hidden lg:block"
        style={{
          paddingTop: "var(--header-h)",
          paddingLeft: "var(--sidebar-w)",
          minHeight: "100vh",
        }}
      >
        <div className="p-6">{children}</div>
      </main>

      {/* ── Mobile main ── */}
      <main
        className="lg:hidden"
        style={{
          paddingTop: "var(--header-h)",
          paddingBottom: "var(--nav-bottom-h)",
          minHeight: "100vh",
        }}
      >
        <div className="p-4">{children}</div>
      </main>
    </div>
  );
}

function HeaderKpi({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span
        className="font-mono text-xs uppercase tracking-widest"
        style={{ color: "var(--text-3)", fontFamily: "var(--font-mono)", fontSize: 9 }}
      >
        {label}
      </span>
      <span
        className="font-mono font-semibold"
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

function Clock() {
  const [tick, setTick] = useState("—");

  useEffect(() => {
    function update() {
      setTick(
        new Date().toLocaleTimeString("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
          timeZone: "Europe/Paris",
        })
      );
    }
    update();
    const id = setInterval(update, 1_000);
    return () => clearInterval(id);
  }, []);

  return (
    <span
      className="font-mono tabular-nums"
      style={{ color: "var(--text-2)", fontFamily: "var(--font-mono)", fontSize: 12 }}
    >
      {tick}
    </span>
  );
}
