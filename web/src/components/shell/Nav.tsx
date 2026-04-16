"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/dashboard",        label: "Command",  icon: "dashboard"        },
  { href: "/dashboard/chart", label: "Chart",     icon: "candlestick_chart" },
  { href: "/dashboard/history",label: "History",   icon: "history"           },
  { href: "/dashboard/risk",  label: "Risk",     icon: "shield"           },
  { href: "/dashboard/system", label: "System",   icon: "settings"         },
];

export default function Nav() {
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  }

  return (
    <>
      {/* Desktop sidebar */}
      <nav
        className="hidden lg:flex flex-col py-3 px-2"
        style={{ position: "fixed", top: "var(--header-h)", left: 0, bottom: 0, width: "var(--sidebar-w)", background: "var(--bg-2)", borderRight: "1px solid var(--border)", zIndex: 90 }}
      >
        {TABS.map(({ href, label, icon }) => (
          <Tab key={href} href={href} label={label} icon={icon} active={isActive(href)} />
        ))}
      </nav>

      {/* Mobile bottom bar */}
      <nav
        className="lg:hidden"
        style={{ position: "fixed", bottom: 0, left: 0, right: 0, height: "var(--nav-bottom-h)", background: "var(--bg-2)", borderTop: "1px solid var(--border)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "space-around" }}
      >
        {TABS.map(({ href, label, icon }) => (
          <MobileTab key={href} href={href} label={label} icon={icon} active={isActive(href)} />
        ))}
      </nav>
    </>
  );
}

function Tab({ href, label, icon, active }: { href: string; label: string; icon: string; active: boolean }) {
  return (
    <Link
      href={href}
      className={cn(
        "flex items-center gap-3 mx-2 py-3 px-4 rounded-md no-underline transition-colors duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent)]",
        active
          ? "bg-[var(--bg-3)] text-[var(--accent)]"
          : "text-[var(--text-2)] hover:text-[var(--text-1)]"
      )}
    >
      <span
        className="material-symbols-outlined flex-shrink-0"
        style={{ fontSize: 18, fontVariationSettings: active ? "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 18" : "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 18" }}
      >
        {icon}
      </span>
      <span
        className="text-sm font-medium"
        style={{ fontFamily: "var(--font-ui)", letterSpacing: "0.03em", fontWeight: active ? 700 : 500 }}
      >
        {label}
      </span>
    </Link>
  );
}

function MobileTab({ href, label, icon, active }: { href: string; label: string; icon: string; active: boolean }) {
  return (
    <Link
      href={href}
      className={cn(
        "flex flex-col items-center justify-center gap-0.5 py-1 px-4 no-underline transition-colors duration-150 min-w-14",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent)]",
        active ? "text-[var(--accent)]" : "text-[var(--text-3)]"
      )}
    >
      <span
        className="material-symbols-outlined"
        style={{ fontSize: 22, fontVariationSettings: active ? "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 22" : "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 22" }}
      >
        {icon}
      </span>
      {active && (
        <span className="text-[10px] font-bold uppercase" style={{ fontFamily: "var(--font-ui)", letterSpacing: "0.04em" }}>
          {label}
        </span>
      )}
    </Link>
  );
}
