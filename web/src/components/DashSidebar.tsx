"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// ── Nav structure ─────────────────────────────────────────────────────────────

const NAV_SECTIONS = [
  {
    label: "Control",
    items: [
      { href: "/dashboard",               label: "Mission",   icon: "space_dashboard"   },
      { href: "/dashboard/trades",        label: "Execution", icon: "swap_horiz"        },
      { href: "/dashboard/strategy",      label: "Strategies",icon: "neurology"         },
      { href: "/dashboard/agent_theater", label: "Agents",    icon: "smart_toy"         },
    ],
  },
  {
    label: "Performance",
    items: [
      { href: "/dashboard/analytics", label: "Analytics", icon: "bar_chart"           },
      { href: "/dashboard/ict",       label: "ICT",       icon: "candlestick_chart"   },
      { href: "/dashboard/learning",  label: "Learning",  icon: "school"              },
    ],
  },
  {
    label: "Markets",
    items: [
      { href: "/dashboard/chart", label: "Chart",      icon: "query_stats"       },
      { href: "/dashboard/world", label: "Macro",      icon: "public"            },
      { href: "/dashboard/globe", label: "Globe",      icon: "language"          },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/dashboard/settings", label: "Settings", icon: "settings"      },
      { href: "/dashboard/skills",   label: "Skills",   icon: "auto_awesome"  },
    ],
  },
];

// ── Component ─────────────────────────────────────────────────────────────────

export default function DashSidebar() {
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  }

  return (
    <aside className="fixed top-14 left-0 w-[248px] bottom-0 bg-[#0a0a0a] border-r border-outline-variant/20 flex flex-col z-40 overflow-y-auto">
      <div className="px-4 pt-4 pb-3 border-b border-outline-variant/15">
        <div className="text-[9px] uppercase tracking-[0.18em] text-on-surface-variant font-semibold mb-1">Navigation</div>
        <div className="text-[13px] text-on-surface font-semibold">Fast path across all pages</div>
      </div>

      <nav className="flex-1 py-4 px-2.5">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} className="mb-6">
            <div className="text-[9px] font-bold tracking-[0.18em] uppercase text-outline px-3 mb-2">
              {section.label}
            </div>
            {section.items.map(({ href, label, icon }) => {
              const active = isActive(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={[
                    "flex items-center gap-3 px-3 py-2.5 rounded-md text-[11px] font-semibold tracking-wide duration-0 w-full",
                    active
                      ? "text-primary-fixed bg-primary-fixed/12 border border-primary-fixed/25"
                      : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high border border-transparent",
                  ].join(" ")}
                >
                  <span
                    className="material-symbols-outlined shrink-0"
                    style={{
                      fontSize: 17,
                      fontVariationSettings: active ? "'FILL' 1" : "'FILL' 0",
                      color: active ? "#00fd87" : undefined,
                    }}
                  >
                    {icon}
                  </span>
                  <span className="truncate">{label}</span>
                </Link>
              );
            })}
          </div>
        ))}
      </nav>

      <div className="px-3.5 py-3.5 border-t border-outline-variant/15 bg-surface-container-low/40">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-primary-fixed animate-pulse" />
            <span className="text-[9px] text-on-surface-variant uppercase tracking-widest">
              Bot Online
            </span>
          </div>
          <span className="text-[9px] text-secondary-fixed uppercase tracking-widest">v2</span>
        </div>
      </div>
    </aside>
  );
}
