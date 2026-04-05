"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_SECTIONS = [
  {
    label: "Control",
    items: [
      { href: "/dashboard",               label: "Mission",    icon: "space_dashboard" },
      { href: "/dashboard/trades",        label: "Execution",  icon: "swap_horiz"      },
      { href: "/dashboard/strategy",      label: "Strategies", icon: "neurology"       },
      { href: "/dashboard/agent_theater", label: "Agents",     icon: "smart_toy"       },
    ],
  },
  {
    label: "Performance",
    items: [
      { href: "/dashboard/analytics", label: "Analytics", icon: "bar_chart"         },
      { href: "/dashboard/ict",       label: "ICT",        icon: "candlestick_chart" },
      { href: "/dashboard/learning",  label: "Learning",   icon: "school"            },
    ],
  },
  {
    label: "Markets",
    items: [
      { href: "/dashboard/chart", label: "Chart", icon: "query_stats" },
      { href: "/dashboard/world", label: "Macro", icon: "public"      },
      { href: "/dashboard/globe", label: "Globe", icon: "language"    },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/dashboard/tools",    label: "Tools",    icon: "build"        },
      { href: "/dashboard/settings", label: "Settings", icon: "settings"     },
      { href: "/dashboard/skills",   label: "Skills",   icon: "auto_awesome" },
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
          top: 52,
          left: 0,
          width: 256,
          height: "calc(100vh - 52px)",
          background: "#1C1C1E",
          borderRight: "0.5px solid rgba(84,84,88,0.65)",
          display: "flex",
          flexDirection: "column",
          zIndex: 40,
          overflowY: "auto",
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif',
        }}
      >
        {/* Brand area */}
        <div
          style={{
            padding: "16px 16px 14px",
            borderBottom: "0.5px solid rgba(84,84,88,0.65)",
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}
        >
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              background: "#30D158",
              boxShadow: "0 0 6px #30D158, 0 0 12px #30D15855",
              flexShrink: 0,
              animation: "sidebarDotPulse 2s ease-in-out infinite",
            }}
          />
          <span
            style={{
              fontSize: 17,
              fontWeight: 700,
              color: "#FFFFFF",
              letterSpacing: "-0.01em",
            }}
          >
            NeuralFX
          </span>
        </div>

        {/* Nav sections */}
        <nav style={{ flex: 1, padding: "8px 12px" }}>
          {NAV_SECTIONS.map((section) => (
            <div key={section.label} style={{ marginBottom: 24 }}>
              <div
                style={{
                  fontSize: 12,
                  fontWeight: 600,
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                  color: "rgba(235,235,245,0.4)",
                  padding: "0 8px",
                  marginBottom: 4,
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
                      height: 44,
                      padding: "0 10px",
                      borderRadius: 10,
                      textDecoration: "none",
                      background: active ? "rgba(120,120,128,0.36)" : "transparent",
                      color: active ? "#FFFFFF" : "rgba(235,235,245,0.6)",
                      fontSize: 15,
                      fontWeight: active ? 600 : 400,
                      transition: "background 150ms ease, color 150ms ease",
                      cursor: "pointer",
                    }}
                    onMouseEnter={(e) => {
                      if (!active) {
                        (e.currentTarget as HTMLAnchorElement).style.background = "rgba(120,120,128,0.18)";
                        (e.currentTarget as HTMLAnchorElement).style.color = "#FFFFFF";
                      }
                    }}
                    onMouseLeave={(e) => {
                      if (!active) {
                        (e.currentTarget as HTMLAnchorElement).style.background = "transparent";
                        (e.currentTarget as HTMLAnchorElement).style.color = "rgba(235,235,245,0.6)";
                      }
                    }}
                  >
                    <span
                      className="material-symbols-outlined"
                      style={{
                        fontSize: 20,
                        flexShrink: 0,
                        fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0",
                        color: active ? "#0A84FF" : "inherit",
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
            borderTop: "0.5px solid rgba(84,84,88,0.65)",
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
                background: "#30D158",
                display: "inline-block",
                animation: "sidebarDotPulse 2s ease-in-out infinite",
              }}
            />
            <span
              style={{
                fontSize: 12,
                color: "rgba(235,235,245,0.4)",
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
              color: "rgba(235,235,245,0.3)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
            }}
          >
            v2
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
