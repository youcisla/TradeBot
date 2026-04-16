"use client";

import EquityCurve from "@/components/history/EquityCurve";
import KPIRow from "@/components/history/KPIRow";
import TradeHistory from "@/components/history/TradeHistory";
import BreakdownChart from "@/components/history/BreakdownChart";

export default function HistoryPage() {
  return (
    <div className="flex flex-col gap-3">
      {/* Top KPIs */}
      <KPIRow />

      {/* Equity curve + breakdown side by side */}
      <div className="grid gap-3" style={{ gridTemplateColumns: "1fr 1fr", alignItems: "start" }}>
        <EquityCurve />
        <BreakdownChart />
      </div>

      {/* Trade history */}
      <TradeHistory />
    </div>
  );
}
