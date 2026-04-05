"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/dashboard",          label: "Home",     icon: "space_dashboard" },
  { href: "/dashboard/trades",   label: "Trades",   icon: "swap_horiz"      },
  { href: "/dashboard/tools",    label: "Tools",    icon: "build"           },
  { href: "/dashboard/chart",    label: "Chart",    icon: "query_stats"     },
  { href: "/dashboard/settings", label: "Settings", icon: "settings"        },
];

export default function DashBottomNav() {
  const pathname = usePathname();

  return (
    <>
      <nav
        className="dash-bottom-nav"
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          height: 60,
          zIndex: 100,
          background: "rgba(28,28,30,0.95)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderTop: "0.5px solid rgba(84,84,88,0.5)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-around",
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", system-ui, sans-serif',
        }}
      >
        {TABS.map(({ href, label, icon }) => {
          const active =
            href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(href);

          return (
            <Link
              key={href}
              href={href}
              style={{
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 2,
                minWidth: 44,
                textDecoration: "none",
                color: active ? "#0A84FF" : "rgba(235,235,245,0.5)",
                transition: "color 150ms ease",
              }}
            >
              <span
                className="material-symbols-outlined"
                style={{
                  fontSize: 24,
                  fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0",
                }}
              >
                {icon}
              </span>
              <span
                style={{
                  fontSize: 10,
                  fontWeight: active ? 600 : 400,
                  letterSpacing: "0.02em",
                }}
              >
                {label}
              </span>
            </Link>
          );
        })}
      </nav>

      <style>{`
        @media (min-width: 1024px) {
          .dash-bottom-nav {
            display: none !important;
          }
        }
      `}</style>
    </>
  );
}
