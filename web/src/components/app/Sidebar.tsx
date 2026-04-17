"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { DESKTOP_NAV } from "@/components/app/nav-config";

function isActive(href: string, pathname: string) {
  if (href === "/dashboard") return pathname === "/dashboard";
  return pathname.startsWith(href);
}

export function Sidebar() {
  const pathname = usePathname();

  return (
    <nav
      className="flex flex-col gap-1 py-3 px-2"
      style={{
        position: "fixed",
        top: "var(--header-h)",
        left: 0,
        bottom: 0,
        width: "var(--sidebar-w)",
        background: "var(--bg-2)",
        borderRight: "1px solid var(--border)",
        zIndex: 90,
      }}
    >
      {DESKTOP_NAV.map((item) => {
        const active = isActive(item.href, pathname);
        return (
          <Link
            key={item.href}
            href={item.href}
            className="flex items-center gap-3 rounded px-3 py-2.5 mx-1 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset"
            style={{
              textDecoration: "none",
              background: active ? "var(--bg-3)" : "transparent",
              color: active ? "var(--accent)" : "var(--text-2)",
            }}
          >
            <span
              className="material-symbols-outlined text-base flex-shrink-0"
              style={{
                fontVariationSettings: active
                  ? "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 18"
                  : "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 18",
              }}
            >
              {item.icon}
            </span>
            <span
              className="text-xs font-medium tracking-wide"
              style={{
                fontFamily: "var(--font-ui)",
                fontWeight: active ? 700 : 500,
                letterSpacing: "0.03em",
              }}
            >
              {item.label}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
