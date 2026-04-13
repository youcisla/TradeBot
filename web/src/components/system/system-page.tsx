"use client";

import { useState } from "react";
import { Tabs } from "@/components/ui/tabs-craft";
import HealthTab from "@/components/system/health-tab";
import LearningTab from "@/components/system/LearningTab";
import AgentsTab from "@/components/system/AgentsTab";
import BrokerTab from "@/components/system/broker-tab";
import ConfigTab from "@/components/system/ConfigTab";

const TABS = [
  { id: "health",   label: "Health",   icon: "favorite" },
  { id: "learning", label: "Learning",  icon: "psychology" },
  { id: "agents",   label: "Agents",   icon: "account_tree" },
  { id: "broker",   label: "Broker",   icon: "hub" },
  { id: "config",   label: "Config",   icon: "settings" },
];

const CONTENT: Record<string, () => React.JSX.Element> = {
  health:   () => <HealthTab />,
  learning: () => <LearningTab />,
  agents:   () => <AgentsTab />,
  broker:   () => <BrokerTab />,
  config:   () => <ConfigTab />,
};

export default function SystemPage() {
  const [active, setActive] = useState("health");

  return (
    <Tabs tabs={TABS} active={active} onChange={setActive}>
      {(id) => CONTENT[id]?.() ?? <></>}
    </Tabs>
  );
}
