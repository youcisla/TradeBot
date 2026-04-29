"use client";

interface RailItem {
  id: string;
  label: string;
  icon: React.ReactNode;
}

interface RailSidebarProps {
  page: string;
  onNav: (id: string) => void;
}

function MissionIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <circle cx="12" cy="12" r="4" />
      <path d="M12 3v3M12 18v3M3 12h3M18 12h3" />
    </svg>
  );
}
function SignalsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 17l4-4 4 4 8-8" />
      <path d="M14 5h6v6" />
    </svg>
  );
}
function TradesIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <path d="M3 10h18M9 14h6" />
    </svg>
  );
}
function RiskIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l9 4v5c0 5-3.5 8-9 9-5.5-1-9-4-9-9V7l9-4z" />
    </svg>
  );
}
function AgentsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="6" cy="6" r="2.5" />
      <circle cx="18" cy="6" r="2.5" />
      <circle cx="12" cy="18" r="2.5" />
      <path d="M8 7l8 0M7 8l4 8M17 8l-4 8" />
    </svg>
  );
}
function MacroIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="9" />
      <path d="M3 12h18M12 3c3 3 3 15 0 18M12 3c-3 3-3 15 0 18" />
    </svg>
  );
}
function PerfIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 20h18M5 16l4-6 4 3 6-9" />
    </svg>
  );
}
function LearnIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l9 5-9 5-9-5 9-5z" />
      <path d="M21 12l-9 5-9-5M21 16l-9 5-9-5" />
    </svg>
  );
}
function HealthIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M3 12h4l2-5 4 10 2-5h6" />
    </svg>
  );
}
function SettingsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
    </svg>
  );
}
function UserIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="12" cy="8" r="4" />
      <path d="M4 21c0-4.5 3.5-8 8-8s8 3.5 8 8" />
    </svg>
  );
}

const items: RailItem[] = [
  { id: "mission",  label: "Mission",  icon: <MissionIcon /> },
  { id: "signals",  label: "Signals",  icon: <SignalsIcon /> },
  { id: "trades",   label: "Trades",   icon: <TradesIcon /> },
  { id: "risk",     label: "Risk",      icon: <RiskIcon /> },
  { id: "agents",   label: "Agents",    icon: <AgentsIcon /> },
  { id: "macro",    label: "Macro",     icon: <MacroIcon /> },
  { id: "perf",     label: "Perf",      icon: <PerfIcon /> },
  { id: "learn",    label: "Learning",  icon: <LearnIcon /> },
  { id: "health",   label: "Health",   icon: <HealthIcon /> },
  { id: "settings", label: "Settings", icon: <SettingsIcon /> },
];

export function RailSidebar({ page, onNav }: RailSidebarProps) {
  return (
    <aside className="rail">
      <nav>
        {items.map(({ id, label, icon }) => (
          <button
            key={id}
            className={`rail-item ${page === id ? "on" : ""}`}
            onClick={() => onNav(id)}
            title={label}
          >
            <span className="ri-ico">{icon}</span>
            <span className="ri-label">{label}</span>
            {page === id && <span className="ri-marker" />}
          </button>
        ))}
      </nav>
      <div className="rail-foot">
        <button className="rail-item" title="Operator">
          <span className="ri-ico">
            <UserIcon />
          </span>
          <span className="ri-label">Operator</span>
        </button>
      </div>
    </aside>
  );
}
