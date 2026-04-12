"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/dashboard",        label: "Command",  icon: "dashboard"        },
  { href: "/dashboard/chart", label: "Chart",     icon: "candlestick_chart" },
  { href: "/dashboard/history",label: "History",   icon: "history"           },
  { href: "/dashboard/risk",  label: "Risk",     icon: "shield"           },
  { href: "/dashboard/system", label: "System",   icon: "settings"         },
];

export default function Nav() {
  const pathname = usePathname();

  function isActive(href: string) {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  }

  return (
    <>
      {/* Desktop sidebar */}
      <nav
        className="hidden lg:flex"
        style={styles.sidebar}
      >
        {TABS.map(({ href, label, icon }) => (
          <Tab key={href} href={href} label={label} icon={icon} active={isActive(href)} />
        ))}
      </nav>

      {/* Mobile bottom bar */}
      <nav
        className="lg:hidden"
        style={styles.bottomBar}
      >
        {TABS.map(({ href, label, icon }) => (
          <MobileTab key={href} href={href} label={label} icon={icon} active={isActive(href)} />
        ))}
      </nav>
    </>
  );
}

function Tab({ href, label, icon, active }: { href: string; label: string; icon: string; active: boolean }) {
  return (
    <Link
      href={href}
      style={{
        ...styles.tab,
        ...(active ? styles.tabActive : {}),
      }}
    >
      <span
        className="material-symbols-outlined"
        style={{ ...styles.icon, ...(active ? styles.iconActive : {}) }}
      >
        {icon}
      </span>
      <span style={{ ...styles.label, ...(active ? styles.labelActive : {}) }}>
        {label}
      </span>
    </Link>
  );
}

function MobileTab({ href, label, icon, active }: { href: string; label: string; icon: string; active: boolean }) {
  return (
    <Link
      href={href}
      style={{
        ...styles.mobileTab,
        ...(active ? styles.mobileTabActive : {}),
      }}
    >
      <span
        className="material-symbols-outlined"
        style={{ ...styles.mobileIcon, ...(active ? styles.mobileIconActive : {}) }}
      >
        {icon}
      </span>
      {active && (
        <span style={styles.mobileLabel}>{label}</span>
      )}
    </Link>
  );
}

const styles: Record<string, React.CSSProperties> = {
  // Desktop sidebar
  sidebar: {
    position: "fixed",
    top: "var(--header-h)",
    left: 0,
    bottom: 0,
    width: "var(--sidebar-w)",
    background: "var(--bg-2)",
    borderRight: "1px solid var(--border)",
    flexDirection: "column",
    padding: "var(--space-3) 0",
    zIndex: 90,
  },
  tab: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-3)",
    padding: "var(--space-3) var(--space-4)",
    margin: "0 var(--space-2)",
    borderRadius: "var(--radius-md)",
    textDecoration: "none",
    transition: "background 0.15s, color 0.15s",
    color: "var(--text-2)",
  },
  tabActive: {
    background: "var(--bg-3)",
    color: "var(--accent)",
  },
  icon: {
    fontSize: 18,
    fontVariationSettings: "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 18",
    flexShrink: 0,
  },
  iconActive: {
    fontVariationSettings: "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 18",
  },
  label: {
    fontFamily: "var(--font-ui)",
    fontSize: 12,
    fontWeight: 500,
    letterSpacing: "0.03em",
  },
  labelActive: {
    fontWeight: 700,
    color: "var(--accent)",
  },

  // Mobile bottom bar
  bottomBar: {
    position: "fixed",
    bottom: 0, left: 0, right: 0,
    height: "var(--nav-bottom-h)",
    background: "var(--bg-2)",
    borderTop: "1px solid var(--border)",
    zIndex: 100,
    display: "flex",
    alignItems: "center",
    justifyContent: "space-around",
  },
  mobileTab: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    gap: 3,
    padding: "6px 16px",
    textDecoration: "none",
    color: "var(--text-3)",
    transition: "color 0.15s",
    minWidth: 56,
  },
  mobileTabActive: {
    color: "var(--accent)",
  },
  mobileIcon: {
    fontSize: 22,
    fontVariationSettings: "'FILL' 0, 'wght' 300, 'GRAD' 0, 'opsz' 22",
  },
  mobileIconActive: {
    fontVariationSettings: "'FILL' 1, 'wght' 400, 'GRAD' 0, 'opsz' 22",
  },
  mobileLabel: {
    fontFamily: "var(--font-ui)",
    fontSize: 10,
    fontWeight: 700,
    letterSpacing: "0.04em",
    textTransform: "uppercase",
  },
};
