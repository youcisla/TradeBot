/**
 * Navigation configuration — single source of truth for all nav items.
 * Import NAV_ITEMS into Sidebar, MobileNav, and CommandPalette.
 */

export interface NavItem {
  href: string;
  label: string;
  icon: string;
  badge?: string;
  badgeVariant?: "positive" | "negative" | "warning" | "info";
}

export const NAV_ITEMS: NavItem[] = [
  { href: "/dashboard",          label: "Mission Control", icon: "dashboard"        },
  { href: "/dashboard/risk",     label: "Risk",            icon: "shield"           },
  { href: "/dashboard/chart",    label: "Chart",           icon: "candlestick_chart" },
  { href: "/dashboard/system",   label: "System",          icon: "monitor"           },
  { href: "/dashboard/history",  label: "History",          icon: "trending_up"      },
  { href: "/dashboard/database", label: "Database",        icon: "storage"          },
  { href: "/dashboard/settings", label: "Settings",       icon: "settings"         },
];

export const DESKTOP_NAV: NavItem[] = NAV_ITEMS;

export const MOBILE_NAV: NavItem[] = [
  NAV_ITEMS[0],
  NAV_ITEMS[1],
  NAV_ITEMS[2],
  NAV_ITEMS[3],
  NAV_ITEMS[5],
];

export interface Command {
  id: string;
  label: string;
  icon: string;
  action: () => void;
  group?: string;
}

export const COMMAND_ITEMS: Command[] = [
  { id: "pause", label: "Pause Bot", icon: "pause", action: () => {}, group: "Bot" },
  { id: "resume", label: "Resume Bot", icon: "play_arrow", action: () => {}, group: "Bot" },
  { id: "scan", label: "Force Scan", icon: "search", action: () => {}, group: "Bot" },
  { id: "goto-signals", label: "Go to Signals", icon: "radar", action: () => {}, group: "Navigate" },
  { id: "goto-trades", label: "Go to Trades", icon: "trending_up", action: () => {}, group: "Navigate" },
  { id: "goto-risk", label: "Go to Risk", icon: "shield", action: () => {}, group: "Navigate" },
];
