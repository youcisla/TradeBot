"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/dashboard",          label: "Home",    icon: "dashboard"         },
  { href: "/dashboard/trades",   label: "Trades",  icon: "swap_horiz"        },
  { href: "/dashboard/markets",  label: "Markets", icon: "candlestick_chart" },
  { href: "/dashboard/brain",    label: "Brain",   icon: "psychology"        },
  { href: "/dashboard/settings", label: "Set",     icon: "settings"          },
];

export default function DashBottomNav() {
  const pathname = usePathname();

  return (
    <>
      <nav className="fixed bottom-0 left-0 right-0 h-[60px] bg-bg-2 border-t border-border z-50 flex items-center justify-around lg:hidden">
        {TABS.map(({ href, label, icon }) => {
          const active = href === "/dashboard"
            ? pathname === "/dashboard"
            : pathname.startsWith(href);

          return (
            <Link
              key={href}
              href={href}
              className={`flex flex-col items-center justify-center w-16 h-full transition-colors ${active ? 'text-gold' : 'text-text-3'}`}
            >
              <span className={`material-symbols-outlined text-[24px] ${active ? 'mb-1' : ''}`}>
                {icon}
              </span>
              {active && (
                <span className="text-[10px] font-ui uppercase tracking-wider font-bold">
                  {label}
                </span>
              )}
            </Link>
          );
        })}
      </nav>
    </>
  );
}
