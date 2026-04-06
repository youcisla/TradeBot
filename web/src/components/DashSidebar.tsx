"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAppShell } from "@/components/AppShell";

const NAV_SECTIONS = [
  {
    label: "Overview",
    items: [
      { href: "/dashboard", label: "Command Center", icon: "dashboard" },
    ],
  },
  {
    label: "Operations",
    items: [
      { href: "/dashboard/trades",  label: "Trade Book",   icon: "swap_horiz"        },
      { href: "/dashboard/markets", label: "Market Intel", icon: "candlestick_chart" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { href: "/dashboard/signals",   label: "Signals",       icon: "radar"      },
      { href: "/dashboard/analytics", label: "Performance",   icon: "bar_chart"  },
      { href: "/dashboard/brain",     label: "Agent Brain",  icon: "psychology" },
      { href: "/dashboard/risk",       label: "Risk Console", icon: "shield"     },
      { href: "/dashboard/learning",  label: "Learning",     icon: "school"     },
      { href: "/dashboard/health",    label: "System Health", icon: "monitor_heart" },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/dashboard/settings", label: "Settings", icon: "settings" },
    ],
  },
];

export default function DashSidebar() {
  const pathname = usePathname();
  const { status: botStatus, isRunning } = useAppShell();

  const stateLabel = botStatus == null ? "Connecting…"
    : isRunning ? "Bot Online"
    : (botStatus.state ?? "offline").charAt(0).toUpperCase() + (botStatus.state ?? "offline").slice(1);

  function isActive(href: string) {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  }

  return (
    <>
      <aside
        className="dash-sidebar"
        style={{
          position: "fixed",
          top: 64,
          left: 0,
          width: 240,
          height: "calc(100vh - 64px)",
          background:
            "linear-gradient(175deg, var(--sidebar-bg) 0%, var(--sidebar-bg-2) 40%, var(--sidebar-bg-3) 100%)",
          borderRight: "1px solid var(--sidebar-border)",
          display: "flex",
          flexDirection: "column",
          zIndex: 40,
          overflowY: "auto",
          boxShadow: "18px 0 40px rgba(0,0,0,0.42)",
          fontFamily: "var(--font-system)",
        }}
      >
        {/* Brand area */}
        <div
          style={{
            padding: "16px 16px 14px",
            borderBottom: "1px solid var(--sidebar-separator)",
            display: "flex",
            alignItems: "center",
            gap: 12,
          }}
        >
          <div
            style={{
              width: 14,
              height: 14,
              borderRadius: 4,
              background: "linear-gradient(145deg, var(--accent) 0%, var(--buy) 100%)",
              boxShadow: "0 0 10px var(--accent-glow), 0 0 20px rgba(34,197,94,0.35)",
              transform: "rotate(45deg)",
              flexShrink: 0,
            }}
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
            <span
              style={{
                fontSize: 16,
                fontWeight: 700,
                color: "var(--sidebar-brand)",
                letterSpacing: "0.015em",
                textTransform: "uppercase",
              }}
            >
              PulseTrade
            </span>
            <span style={{ fontSize: 11, color: "var(--sidebar-text-muted)", letterSpacing: "0.08em" }}>
              Command Matrix
            </span>
          </div>
        </div>

        {/* Nav sections */}
        <nav style={{ flex: 1, padding: "8px 12px" }}>
          {NAV_SECTIONS.map((section) => (
            <div key={section.label} style={{ marginBottom: 18 }}>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                  color: "var(--sidebar-text-muted)",
                  padding: "0 8px",
                  marginBottom: 6,
                }}
              >
                {section.label}
              </div>

              {section.items.map(({ href, label, icon }) => {
                const active = isActive(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: 12,
                      minHeight: 44,
                      padding: "10px 10px",
                      borderRadius: 12,
                      textDecoration: "none",
                      background: active
                        ? "linear-gradient(135deg, var(--sidebar-accent-bg) 0%, var(--sidebar-accent-bg-2) 100%)"
                        : "transparent",
                      color: active ? "var(--sidebar-brand)" : "var(--sidebar-text)",
                      fontSize: 15,
                      fontWeight: active ? 600 : 400,
                      border: active ? "1px solid var(--sidebar-accent)" : "1px solid transparent",
                      transition: "background 150ms ease, color 150ms ease, border-color 150ms ease",
                      cursor: "pointer",
                    }}
                    onMouseEnter={(e) => {
                      if (!active) {
                        (e.currentTarget as HTMLAnchorElement).style.background =
                          "var(--sidebar-hover-bg)";
                        (e.currentTarget as HTMLAnchorElement).style.color = "var(--text-primary)";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!active) {
                        (e.currentTarget as HTMLAnchorElement).style.background = "transparent";
                        (e.currentTarget as HTMLAnchorElement).style.color = "var(--sidebar-text)";
                      }
                    }}
                  >
                    <span
                      className="material-symbols-outlined"
                      style={{
                        fontSize: 20,
                        flexShrink: 0,
                        fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0",
                        color: active ? "var(--sidebar-icon)" : "inherit",
                        transition: "color 150ms ease",
                      }}
                    >
                      {icon}
                    </span>
                    <span style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      {label}
                    </span>
                  </Link>
                );
              })}
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div
          style={{
            padding: "12px 16px",
            borderTop: "1px solid var(--sidebar-separator)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span
              style={{
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: isRunning ? "var(--buy)" : botStatus == null ? "var(--health-warn)" : "var(--sell)",
                display: "inline-block",
                animation: isRunning ? "sidebarDotPulse 2s ease-in-out infinite" : undefined,
              }}
            />
            <span
              style={{
                fontSize: 12,
                color: isRunning ? "rgba(102,246,165,0.7)" : "var(--sidebar-text-dim)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              {stateLabel}
            </span>
          </div>
          <span
            style={{
              fontSize: 12,
              color: "var(--sidebar-text-dim)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            v3
          </span>
        </div>
      </aside>

      <style>{`
        @keyframes sidebarDotPulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }
        @media (max-width: 1023px) {
          .dash-sidebar {
            display: none !important;
          }
        }
      `}</style>
    </>
  );
}
