"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MOBILE_NAV } from "@/components/app/nav-config";
import { cn } from "@/lib/utils";

function isActive(href: string, pathname: string) {
  if (href === "/dashboard") return pathname === "/dashboard";
  return pathname.startsWith(href);
}

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav
      className="flex items-center justify-around bg-[var(--bg-2)]"
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        height: "var(--nav-bottom-h)",
        borderTop: "1px solid var(--border)",
        zIndex: 100,
      }}
    >
      {MOBILE_NAV.map((item) => {
        const active = isActive(item.href, pathname);
        return (
          <Link
            key={item.href}
            href={item.href}
            className={cn(
              "flex flex-col items-center justify-center gap-0.5 py-1 px-3 min-w-14",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent)] focus-visible:ring-inset",
              active ? "text-[var(--accent)]" : "text-[var(--text-3)]"
            )}
            style={{ textDecoration: "none" }}
            aria-label={item.label}
          >
            <span
              className="material-symbols-outlined"
              style={{
                fontSize: 22,
                fontVariationSettings: active
                  ? "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 22"
                  : "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 22",
              }}
            >
              {item.icon}
            </span>
            {active && (
              <span
                className="text-[9px] font-bold uppercase tracking-[0.04em]"
                style={{ fontFamily: "var(--font-ui)" }}
              >
                {item.label}
              </span>
            )}
          </Link>
        );
      })}
    </nav>
  );
}
