"use client";

import { useState } from "react";
import HealthTab from "@/components/system/HealthTab";
import LearningTab from "@/components/system/LearningTab";
import AgentsTab from "@/components/system/AgentsTab";
import BrokerTab from "@/components/system/BrokerTab";
import ConfigTab from "@/components/system/ConfigTab";

const TABS = [
  { id: "health",  label: "Health",  icon: "♥" },
  { id: "learning",label: "Learning", icon: "◈" },
  { id: "agents",  label: "Agents",  icon: "⬡" },
  { id: "broker",  label: "Broker",  icon: "⬢" },
  { id: "config",  label: "Config",  icon: "⚙" },
] as const;

type TabId = typeof TABS[number]["id"];

export default function SystemPage() {
  const [active, setActive] = useState<TabId>("health");

  return (
    <div style={styles.root}>
      {/* Tab bar */}
      <div style={styles.tabBar}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            style={{
              ...styles.tab,
              ...(active === tab.id ? styles.tabActive : {}),
            }}
            onClick={() => setActive(tab.id)}
          >
            <span style={styles.tabIcon}>{tab.icon}</span>
            <span style={styles.tabLabel}>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={styles.content}>
        {active === "health"  && <HealthTab />}
        {active === "learning" && <LearningTab />}
        {active === "agents"  && <AgentsTab />}
        {active === "broker"  && <BrokerTab />}
        {active === "config"  && <ConfigTab />}
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    flexDirection: "column",
    gap: "var(--space-3)",
  },
  tabBar: {
    display: "flex",
    gap: "var(--space-2)",
    flexWrap: "wrap",
  },
  tab: {
    display: "flex",
    alignItems: "center",
    gap: "var(--space-2)",
    background: "var(--bg-2)",
    border: "1px solid var(--border)",
    borderRadius: "var(--radius-md)",
    color: "var(--text-2)",
    cursor: "pointer",
    fontFamily: "var(--font-ui)",
    fontSize: 12,
    fontWeight: 600,
    padding: "6px 14px",
  },
  tabActive: {
    background: "var(--bg-3)",
    border:     "1px solid var(--border-active)",
    color:      "var(--accent)",
  },
  tabIcon: {
    fontSize: 14,
    lineHeight: 1,
  },
  tabLabel: {
    letterSpacing: "0.03em",
  },
  content: {
    minHeight: 300,
  },
};
