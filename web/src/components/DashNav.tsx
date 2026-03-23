"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/dashboard",           label: "Dashboard",  icon: "⬛" },
  { href: "/dashboard/chart",     label: "Chart",      icon: "📈" },
  { href: "/dashboard/analytics", label: "Analytics",  icon: "◈" },
  { href: "/dashboard/trades",    label: "Trades",     icon: "◇" },
  { href: "/dashboard/learning",  label: "Learning",   icon: "◆" },
  { href: "/dashboard/strategy",  label: "Strategy",   icon: "◉" },
  { href: "/dashboard/ict",       label: "ICT Engine", icon: "⊕" },
  { href: "/dashboard/settings",  label: "Settings",   icon: "⚙" },
];

export default function DashNav() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  };

  return (
    <nav style={{
      borderBottom: "1px solid #1c1c28",
      background: "linear-gradient(90deg, #080810 0%, #0a0a0f 50%, #080810 100%)",
      padding: "0 20px",
      display: "flex",
      alignItems: "center",
      gap: 0,
      position: "sticky",
      top: 0,
      zIndex: 50,
    }}>
      {/* Logo */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 10,
        padding: "12px 20px 12px 0",
        borderRight: "1px solid #1c1c28",
        marginRight: 16,
        flexShrink: 0,
      }}>
        <div style={{
          width: 8, height: 8, borderRadius: "50%",
          background: "#00ff41",
          boxShadow: "0 0 10px #00ff41, 0 0 20px #00ff4155",
          animation: "navPulse 2.5s ease-in-out infinite",
        }} />
        <span style={{
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 13, fontWeight: 700,
          color: "#00ff41",
          letterSpacing: "0.15em",
          textTransform: "uppercase",
          textShadow: "0 0 12px rgba(0,255,65,0.5)",
        }}>
          NeuralFX
        </span>
      </div>

      {/* Nav links */}
      <div style={{ display: "flex", alignItems: "stretch", flex: 1, overflowX: "auto", scrollbarWidth: "none" }}>
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 6,
                padding: "0 14px",
                height: 46,
                fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace",
                fontWeight: active ? 700 : 400,
                color: active ? "#00ff41" : "#3a4a5a",
                textDecoration: "none",
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                position: "relative",
                transition: "color 0.15s",
                whiteSpace: "nowrap",
                borderBottom: active ? "2px solid #00ff41" : "2px solid transparent",
                boxShadow: active ? "0 2px 0 rgba(0,255,65,0.3)" : undefined,
              }}
              onMouseEnter={(e) => {
                if (!active) (e.currentTarget as HTMLElement).style.color = "#9aa8b8";
              }}
              onMouseLeave={(e) => {
                if (!active) (e.currentTarget as HTMLElement).style.color = "#3a4a5a";
              }}
            >
              {active && (
                <span style={{
                  width: 4, height: 4, borderRadius: "50%",
                  background: "#00ff41",
                  boxShadow: "0 0 6px #00ff41",
                  flexShrink: 0,
                }} />
              )}
              {item.label}
            </Link>
          );
        })}
      </div>

      {/* Right: session indicator */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "0 0 0 16px",
        borderLeft: "1px solid #1c1c28",
        flexShrink: 0,
        marginLeft: 8,
      }}>
        <span style={{
          fontSize: 9, color: "#607888",
          fontFamily: "'JetBrains Mono', monospace",
          letterSpacing: "0.1em",
          textTransform: "uppercase",
        }}>
          LIVE
        </span>
        <div style={{
          width: 6, height: 6, borderRadius: "50%",
          background: "#00ff41",
          boxShadow: "0 0 8px #00ff41",
          animation: "navPulse 1.8s ease-in-out infinite",
        }} />
      </div>

      <style>{`
        @keyframes navPulse {
          0%,100% { opacity: 1; }
          50%      { opacity: 0.5; }
        }
      `}</style>
    </nav>
  );
}
