"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// ── Nav structure ─────────────────────────────────────────────────────────────

const NAV_SECTIONS = [
  {
    label: "PRIMARY",
    items: [
      { href: "/dashboard",               label: "Overview",  icon: "grid_view"         },
      { href: "/dashboard/trades",        label: "Trades",    icon: "swap_horiz"        },
      { href: "/dashboard/strategy",      label: "Strategy",  icon: "psychology"        },
      { href: "/dashboard/agent_theater", label: "Theater",   icon: "smart_toy"         },
    ],
  },
  {
    label: "ANALYTICS",
    items: [
      { href: "/dashboard/analytics", label: "Analytics", icon: "bar_chart"          },
      { href: "/dashboard/ict",       label: "ICT Engine", icon: "show_chart"        },
      { href: "/dashboard/learning",  label: "Learning",   icon: "school"            },
    ],
  },
  {
    label: "INTEL",
    items: [
      { href: "/dashboard/chart", label: "Chart",      icon: "candlestick_chart" },
      { href: "/dashboard/world", label: "World Intel", icon: "public"           },
      { href: "/dashboard/globe", label: "Globe",       icon: "language"         },
    ],
  },
  {
    label: "SYSTEM",
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
    <aside className="fixed top-11 left-0 w-[200px] bottom-0 bg-surface-container-lowest border-r border-outline-variant/15 flex flex-col z-40 overflow-y-auto">
      <nav className="flex-1 py-4 px-2">
        {NAV_SECTIONS.map((section) => (
          <div key={section.label} className="mb-5">
            <div className="text-[9px] font-bold tracking-[0.2em] text-outline px-3 mb-2">
              {section.label}
            </div>
            {section.items.map(({ href, label, icon }) => {
              const active = isActive(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={[
                    "flex items-center gap-3 px-3 py-2 text-[11px] font-bold uppercase tracking-wide duration-0 w-full",
                    active
                      ? "text-primary-fixed bg-primary-fixed/8 border-l-2 border-primary-fixed"
                      : "text-on-surface-variant hover:text-on-surface hover:bg-surface-container-high border-l-2 border-transparent",
                  ].join(" ")}
                >
                  <span
                    className="material-symbols-outlined shrink-0"
                    style={{
                      fontSize: 16,
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

      {/* Footer */}
      <div className="px-3 py-3 border-t border-outline-variant/15">
        <div className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-primary-fixed animate-pulse" />
          <span className="text-[9px] text-on-surface-variant uppercase tracking-widest">
            Bot Online
          </span>
        </div>
      </div>
    </aside>
  );
}
