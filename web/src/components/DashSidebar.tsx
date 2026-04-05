"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

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
      { href: "/dashboard/analytics", label: "Performance",  icon: "bar_chart"  },
      { href: "/dashboard/brain",     label: "Agent Brain",  icon: "psychology" },
      { href: "/dashboard/risk",      label: "Risk Console", icon: "shield"     },
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
            "linear-gradient(175deg, rgba(16,19,26,0.95) 0%, rgba(10,12,15,0.96) 40%, rgba(8,9,11,0.98) 100%)",
          borderRight: "1px solid rgba(100,120,150,0.22)",
          display: "flex",
          flexDirection: "column",
          zIndex: 40,
          overflowY: "auto",
          boxShadow: "18px 0 40px rgba(0,0,0,0.42)",
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif',
        }}
      >
        {/* Brand area */}
        <div
          style={{
            padding: "16px 16px 14px",
            borderBottom: "1px solid rgba(100,120,150,0.25)",
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
              background: "linear-gradient(145deg, #30d6ff 0%, #66f6a5 100%)",
              boxShadow: "0 0 10px rgba(48,214,255,0.9), 0 0 20px rgba(102,246,165,0.35)",
              transform: "rotate(45deg)",
              flexShrink: 0,
            }}
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 1 }}>
            <span
              style={{
                fontSize: 16,
                fontWeight: 700,
                color: "#e7f0ff",
                letterSpacing: "0.015em",
                textTransform: "uppercase",
              }}
            >
              NeuralFX
            </span>
            <span style={{ fontSize: 11, color: "rgba(180,200,228,0.58)", letterSpacing: "0.08em" }}>
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
                  color: "rgba(171,190,219,0.48)",
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
                        ? "linear-gradient(135deg, rgba(38,120,176,0.34) 0%, rgba(24,38,59,0.7) 100%)"
                        : "transparent",
                      color: active ? "#f2f7ff" : "rgba(226,235,247,0.68)",
                      fontSize: 15,
                      fontWeight: active ? 600 : 400,
                      border: active ? "1px solid rgba(108,184,255,0.45)" : "1px solid transparent",
                      transition: "background 150ms ease, color 150ms ease, border-color 150ms ease",
                      cursor: "pointer",
                    }}
                    onMouseEnter={(e) => {
                      if (!active) {
                        (e.currentTarget as HTMLAnchorElement).style.background =
                          "rgba(88,122,160,0.18)";
                        (e.currentTarget as HTMLAnchorElement).style.color = "#FFFFFF";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!active) {
                        (e.currentTarget as HTMLAnchorElement).style.background = "transparent";
                        (e.currentTarget as HTMLAnchorElement).style.color = "rgba(226,235,247,0.68)";
                      }
                    }}
                  >
                    <span
                      className="material-symbols-outlined"
                      style={{
                        fontSize: 20,
                        flexShrink: 0,
                        fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0",
                        color: active ? "#63d4ff" : "inherit",
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
            borderTop: "1px solid rgba(100,120,150,0.25)",
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
                background: "#66f6a5",
                display: "inline-block",
                animation: "sidebarDotPulse 2s ease-in-out infinite",
              }}
            />
            <span
              style={{
                fontSize: 12,
                color: "rgba(177,198,227,0.5)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              Bot Online
            </span>
          </div>
          <span
            style={{
              fontSize: 12,
              color: "rgba(177,198,227,0.35)",
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
