"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/dashboard",               label: "HOME",      icon: "space_dashboard"  },
  { href: "/dashboard/trades",        label: "TRADES",    icon: "swap_horiz" },
  { href: "/dashboard/analytics",     label: "ANALYTICS", icon: "bar_chart"  },
  { href: "/dashboard/strategy",      label: "MODELS",    icon: "neurology"  },
  { href: "/dashboard/settings",      label: "SETTINGS",  icon: "settings"   },
];

export default function DashBottomNav() {
  const pathname = usePathname();

  return (
    <nav className="fixed bottom-0 left-0 w-full flex justify-around items-center h-16 bg-[#0a0a0aee] backdrop-blur-md border-t border-outline-variant/20 z-50">
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
              "flex flex-col items-center justify-center pt-2 min-w-[62px] duration-0",
              active
                ? "text-primary-fixed drop-shadow-[0_0_8px_rgba(0,253,135,0.4)]"
                : "text-on-surface-variant hover:text-secondary",
            ].join(" ")}
          >
            <span
              className="material-symbols-outlined mb-1"
              style={{
                fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0",
                fontSize: 20,
              }}
            >
              {icon}
            </span>
            <span className="font-mono text-[9px] font-bold uppercase tracking-wide">{label}</span>
          </Link>
        );
      })}
    </nav>
  );
}
