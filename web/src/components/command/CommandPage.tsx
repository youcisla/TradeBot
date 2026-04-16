"use client";

import PositionsCard from "@/components/command/PositionsCard";
import EventStream from "@/components/command/EventStream";
import QuickActions from "@/components/command/QuickActions";
import MacroStrip from "@/components/command/MacroStrip";

export default function CommandPage() {
  return (
    <div className="flex flex-col gap-3">
      {/* Macro intelligence strip */}
      <MacroStrip />

      {/* Bot control actions */}
      <QuickActions />

      {/* Bottom: positions + events side-by-side */}
      <div className="grid gap-3" style={{ gridTemplateColumns: "1fr 1fr", alignItems: "start" }}>
        <PositionsCard />
        <EventStream />
      </div>
    </div>
  );
}
