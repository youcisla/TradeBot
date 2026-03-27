"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/dashboard",               label: "OVERVIEW",  icon: "grid_view"  },
  { href: "/dashboard/trades",        label: "TRADES",    icon: "swap_horiz" },
  { href: "/dashboard/strategy",      label: "STRATEGY",  icon: "psychology" },
  { href: "/dashboard/agent_theater", label: "THEATER",   icon: "smart_toy"  },
];

export default function DashBottomNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 w-full flex justify-around items-center h-16 bg-surface border-t border-outline-variant/15 z-50">
      {NAV.map(({ href, label, icon }) => {
        const active =
          href === "/dashboard"
            ? pathname === "/dashboard"
            : pathname.startsWith(href);

        return (
          <Link
            key={href}
            href={href}
            className={[
              "flex flex-col items-center justify-center pt-2 duration-0",
              active
                ? "text-primary-fixed drop-shadow-[0_0_8px_rgba(0,253,135,0.4)] border-t-2 border-primary-fixed"
                : "text-on-surface-variant hover:text-secondary",
            ].join(" ")}
          >
            <span
              className="material-symbols-outlined mb-1"
              style={{
                fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0",
                fontSize: 22,
              }}
            >
              {icon}
            </span>
            <span className="font-mono text-[10px] font-bold uppercase">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
