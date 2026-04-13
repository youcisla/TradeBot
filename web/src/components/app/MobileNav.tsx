"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { MOBILE_NAV } from "@/components/app/nav-config";

function isActive(href: string, pathname: string) {
  if (href === "/dashboard") return pathname === "/dashboard";
  return pathname.startsWith(href);
}

export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav
      className="flex items-center justify-around"
      style={{
        position: "fixed",
        bottom: 0,
        left: 0,
        right: 0,
        height: "var(--nav-bottom-h)",
        background: "var(--bg-2)",
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
            className="flex flex-col items-center justify-center gap-0.5 py-1 px-3 min-w-14"
            style={{ textDecoration: "none", color: active ? "var(--accent)" : "var(--text-3)" }}
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
                className="text-xs font-bold uppercase tracking-widest"
                style={{
                  fontFamily: "var(--font-ui)",
                  fontSize: 9,
                  letterSpacing: "0.04em",
                }}
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
