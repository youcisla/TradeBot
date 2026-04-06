"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/dashboard",          label: "Home",    icon: "dashboard"         },
  { href: "/dashboard/signals", label: "Signals", icon: "radar"            },
  { href: "/dashboard/trades",  label: "Trades",  icon: "swap_horiz"       },
  { href: "/dashboard/brain",   label: "Brain",  icon: "psychology"       },
  { href: "/dashboard/settings",label: "Settings",icon: "settings"         },
];

export default function DashBottomNav() {
  const pathname = usePathname();

  return (
    <>
      <nav
        className="dash-bottom-nav"
        style={{
          position: "fixed",
          bottom: 10,
          left: 10,
          right: 10,
          height: 62,
          zIndex: 100,
          background: "rgba(10,14,19,0.86)",
          backdropFilter: "blur(14px)",
          WebkitBackdropFilter: "blur(14px)",
          border: "1px solid rgba(112,143,179,0.42)",
          borderRadius: 16,
          boxShadow: "0 18px 26px rgba(0,0,0,0.44)",
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
                color: active ? "#6bd9ff" : "rgba(224,235,248,0.55)",
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
