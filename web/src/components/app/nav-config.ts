/**
 * Navigation configuration — single source of truth for all nav items.
 * Import NAV_ITEMS into Sidebar, MobileNav, and CommandPalette.
 */

export interface NavItem {
  href: string;
  label: string;
  icon: string;          // Material Symbols icon name
  badge?: string;        // Optional badge text (e.g. live count)
  badgeVariant?: "positive" | "negative" | "warning" | "info";
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard",      label: "Mission Control", icon: "dashboard"        },
  { href: "/dashboard/risk",  label: "Risk",            icon: "shield"           },
  { href: "/dashboard/chart", label: "Chart",           icon: "candlestick_chart" },
  { href: "/dashboard/system", label: "System",          icon: "monitor"           },
  { href: "/dashboard/history", label: "History",        icon: "trending_up"       },
  { href: "/dashboard/settings", label: "Settings",      icon: "settings"          },
];

/** Desktop sidebar — 8 nav items. Agent theatre hidden from mobile. */
export const DESKTOP_NAV: NavItem[] = NAV_ITEMS;

/** Mobile bottom tab bar — 5 items only (highest-traffic pages). */
export const MOBILE_NAV: NavItem[] = [
  NAV_ITEMS[0],  // Mission Control
  NAV_ITEMS[1],  // Risk
  NAV_ITEMS[2],  // Chart
  NAV_ITEMS[3],  // System
  NAV_ITEMS[5],  // Settings
];

/** Commands available in the ⌘K palette. */
export interface Command {
  id: string;
  label: string;
  icon: string;
  action: () => void;
  /** For grouping in the palette */
  group?: string;
}

export const COMMAND_ITEMS: Command[] = [
  {
    id: "pause",
    label: "Pause Bot",
    icon: "pause",
    action: () => { /* TODO: wire to pause endpoint */ },
    group: "Bot",
  },
  {
    id: "resume",
    label: "Resume Bot",
    icon: "play_arrow",
    action: () => { /* TODO: wire to resume endpoint */ },
    group: "Bot",
  },
  {
    id: "scan",
    label: "Force Scan",
    icon: "search",
    action: () => { /* TODO: wire to scan endpoint */ },
    group: "Bot",
  },
  {
    id: "goto-signals",
    label: "Go to Signals",
    icon: "radar",
    action: () => { /* TODO: router.push */ },
    group: "Navigate",
  },
  {
    id: "goto-trades",
    label: "Go to Trades",
    icon: "trending_up",
    action: () => { /* TODO: router.push */ },
    group: "Navigate",
  },
  {
    id: "goto-risk",
    label: "Go to Risk",
    icon: "shield",
    action: () => { /* TODO: router.push */ },
    group: "Navigate",
  },
];
