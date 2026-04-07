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
      { href: "/dashboard/trades",  label: "Trade Book",   icon: "swap_horiz" },
      { href: "/dashboard/markets", label: "Market Intel", icon: "candlestick_chart" },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { href: "/dashboard/analytics", label: "Performance", icon: "bar_chart" },
      { href: "/dashboard/brain",     label: "Agent Brain", icon: "psychology" },
      { href: "/dashboard/risk",      label: "Risk Console", icon: "shield" },
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
  const { status, isRunning } = useAppShell();

  function isActive(href: string) {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  }

  const isHealthy = isRunning && status?.state !== "error";

  return (
    <>
      <aside className="fixed top-[52px] left-0 w-[220px] h-[calc(100vh-52px)] bg-bg-2 border-r border-border flex flex-col z-40 hidden lg:flex">
        <nav className="flex-1 px-2 py-4 overflow-y-auto">
          {NAV_SECTIONS.map((section) => (
            <div key={section.label} className="mb-6">
              <div className="text-[11px] font-bold uppercase tracking-widest text-text-3 px-3 mb-2">
                {section.label}
              </div>
              <div className="flex flex-col gap-1">
                {section.items.map(({ href, label, icon }) => {
                  const active = isActive(href);
                  return (
                    <Link
                      key={href}
                      href={href}
                      className={`flex items-center gap-3 px-3 py-2 font-ui uppercase font-bold text-sm tracking-wide transition-all
                        ${active ? 'bg-gold-dim border-l-2 border-gold text-gold' : 'border-l-2 border-transparent text-text-2 hover:bg-bg-3 hover:text-text-1'}
                      `}
                    >
                      <span className="material-symbols-outlined text-[18px]">
                        {icon}
                      </span>
                      {label}
                    </Link>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Bottom Health Indicator */}
        <div className="p-4 border-t border-border flex items-center gap-3">
          <span className={`w-2 h-2 rounded-full ${isHealthy ? 'bg-green animate-pulse' : 'bg-red'}`} />
          <span className="font-ui text-xs text-text-2 uppercase tracking-wider overflow-hidden text-ellipsis whitespace-nowrap">
            {isHealthy ? 'All systems nominal' : 'System Error'}
          </span>
        </div>
      </aside>
    </>
  );
}
