"use client";

import PositionsCard from "@/components/command/PositionsCard";
import EventStream from "@/components/command/EventStream";
import QuickActions from "@/components/command/QuickActions";
import MacroStrip from "@/components/command/MacroStrip";

export default function CommandPage() {
  return (
    <div style={styles.root}>
      {/* Top: macro intelligence + quick actions */}
      <div style={styles.topRow}>
        <MacroStrip />
      </div>
      <div style={styles.actionsRow}>
        <QuickActions />
      </div>

      {/* Bottom: positions + events (side-by-side) */}
      <div style={styles.midRow}>
        <div style={styles.positionsWrap}>
          <PositionsCard />
        </div>
        <div style={styles.eventsWrap}>
          <EventStream />
        </div>
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
  topRow: {
    width: "100%",
  },
  actionsRow: {
    width: "100%",
  },
  // Side-by-side on desktop; layout.tsx mobile path stacks vertically
  midRow: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "var(--space-3)",
    alignItems: "start",
  },
  positionsWrap: {
    minWidth: 0,
  },
  eventsWrap: {
    minWidth: 0,
  },
};
