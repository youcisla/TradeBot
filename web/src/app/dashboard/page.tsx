import BotStatusBar from "@/components/BotStatusBar";
import AgentFeed from "@/components/AgentFeed";
import OpenTradesTable from "@/components/OpenTradesTable";
import CommandPanel from "@/components/CommandPanel";
import EquityCurve from "@/components/EquityCurve";

export const dynamic = "force-dynamic";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <BotStatusBar />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Agent feed (2 cols) */}
        <div className="lg:col-span-2">
          <AgentFeed />
        </div>

        {/* Right: Commands + equity curve */}
        <div className="space-y-6">
          <CommandPanel />
          <EquityCurve />
        </div>
      </div>

      <OpenTradesTable />
    </div>
  );
}
