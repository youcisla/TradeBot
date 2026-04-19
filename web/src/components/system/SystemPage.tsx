"use client";

import { useState } from "react";
import HealthTab from "@/components/system/HealthTab";
import LearningTab from "@/components/system/LearningTab";
import AgentsTab from "@/components/system/AgentsTab";
import BrokerTab from "@/components/system/BrokerTab";
import ConfigTab from "@/components/system/ConfigTab";
import { cn } from "@/lib/utils";

const TABS = [
  { id: "health",  label: "Health",  icon: "favorite"    },
  { id: "learning",label: "Learning", icon: "auto_graph" },
  { id: "agents",  label: "Agents",  icon: "hexagon"     },
  { id: "broker",  label: "Broker",  icon: "account_tree"},
  { id: "config",  label: "Config",  icon: "settings"    },
] as const;

type TabId = typeof TABS[number]["id"];

export default function SystemPage() {
  const [active, setActive] = useState<TabId>("health");

  return (
    <div className="flex flex-col gap-3">
      {/* Tab bar */}
      <div className="flex gap-2 flex-wrap">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            className={cn(
              "flex items-center gap-2 rounded-md px-3 py-1.5 cursor-pointer transition-all border text-xs font-semibold",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[var(--accent)]",
              active === tab.id
                ? "bg-[var(--bg-3)] border-[var(--border-active)] text-[var(--accent)]"
                : "bg-[var(--bg-2)] border-[var(--border)] text-[var(--text-2)]"
            )}
            style={{ fontFamily: "var(--font-ui)", letterSpacing: "0.03em" }}
            onClick={() => setActive(tab.id)}
          >
            <span style={{ fontSize: 14, lineHeight: 1 }}>{tab.icon}</span>
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div style={{ minHeight: 300 }}>
        {active === "health"  && <HealthTab />}
        {active === "learning" && <LearningTab />}
        {active === "agents"  && <AgentsTab />}
        {active === "broker"  && <BrokerTab />}
        {active === "config"  && <ConfigTab />}
      </div>
    </div>
  );
}
