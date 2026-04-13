"use client";

import { useAppShell } from "@/components/AppShell";
import KpiRow from "@/components/command/KpiRow";
import { Panel } from "@/components/ui/panel";
import { EventFeed } from "@/components/ui/data-display/EventFeed";
import { SectionHeader } from "@/components/ui/section-header";
import PositionsCard from "@/components/command/PositionsCard";
import QuickActions from "@/components/command/QuickActions";
import MacroStrip from "@/components/command/MacroStrip";

export default function CommandCenter() {
  const { wsEvents } = useAppShell();

  return (
    <div className="flex flex-col gap-3">
      {/* KPI row */}
      <KpiRow />

      {/* Macro intelligence strip */}
      <MacroStrip />

      {/* Quick actions */}
      <QuickActions />

      {/* Positions + Live events */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3 items-start">
        <Panel
          title={<SectionHeader title="Open Positions" />}
          className="p-0"
        >
          <PositionsCard />
        </Panel>

        <Panel
          title={<SectionHeader title="Agent Events" />}
          className="p-0"
        >
          <EventFeed
            events={wsEvents}
            maxHeight="400px"
            emptyMessage="No events recorded"
          />
        </Panel>
      </div>
    </div>
  );
}