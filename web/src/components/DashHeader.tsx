"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { nowParis } from "@/lib/time";

const QUICK_LINKS = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/trades", label: "Trades" },
  { href: "/dashboard/analytics", label: "Analytics" },
  { href: "/dashboard/strategy", label: "Strategy" },
  { href: "/dashboard/settings", label: "Settings" },
];

export default function DashHeader() {
  const [localTime, setLocalTime] = useState("--:--:--");
  const pathname = usePathname();

  useEffect(() => {
    const tick = () => setLocalTime(nowParis());
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <header className="fixed top-0 left-0 w-full z-50 backdrop-blur-md border-b border-outline-variant/20 bg-[#090909cc]">
      <div className="flex items-center justify-between px-3 sm:px-4 lg:px-6 py-2.5 gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <div className="w-7 h-7 rounded-md border border-primary-fixed/35 bg-primary-fixed/10 flex items-center justify-center shrink-0">
            <span className="material-symbols-outlined text-primary-fixed" style={{ fontSize: 15 }}>
              network_node
            </span>
          </div>
          <div className="min-w-0">
            <p className="text-[9px] tracking-[0.16em] uppercase text-on-surface-variant font-semibold">NeuralFX Control Surface</p>
            <p className="text-[14px] font-bold text-on-surface truncate">Multi-Agent Trading Dashboard</p>
          </div>
        </div>

        <nav className="hidden xl:flex items-center gap-1 bg-surface-container-low/70 border border-outline-variant/20 rounded-lg p-1">
          {QUICK_LINKS.map((item) => {
            const active = item.href === "/dashboard" ? pathname === "/dashboard" : pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={[
                  "px-3 py-1.5 rounded-md text-[11px] font-semibold",
                  active
                    ? "bg-primary-fixed/15 text-primary-fixed"
                    : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high/70",
                ].join(" ")}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-2 shrink-0">
          <div className="hidden sm:flex items-center gap-2 px-2.5 py-1.5 rounded-md border border-secondary-fixed/30 bg-secondary-fixed/10">
            <span className="w-1.5 h-1.5 rounded-full bg-secondary-fixed animate-pulse" />
            <span className="text-[10px] tracking-wider uppercase font-semibold text-secondary-fixed">Live</span>
          </div>
          <div className="px-2.5 py-1.5 rounded-md border border-primary-fixed/30 bg-primary-fixed/10 text-primary-fixed font-mono text-[11px]">
            {localTime}
          </div>
        </div>
      </div>
    </header>
  );
}
