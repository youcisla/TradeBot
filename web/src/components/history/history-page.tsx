"use client";

import { Panel } from "@/components/ui/panel";
import EquityCurve from "@/components/history/EquityCurve";
import KPIRow from "@/components/history/KPIRow";
import TradeHistory from "@/components/history/trade-history";
import BreakdownChart from "@/components/history/BreakdownChart";

export default function HistoryPage() {
  return (
    <div className="flex flex-col gap-3">
      {/* Top KPIs */}
      <KPIRow />

      {/* Equity curve + breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <EquityCurve />
        <BreakdownChart />
      </div>

      {/* Trade history */}
      <TradeHistory />
    </div>
  );
}
