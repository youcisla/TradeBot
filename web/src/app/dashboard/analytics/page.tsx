import HistoryPage from "@/components/history/history-page";
import { BacktestPanel } from "@/components/backtest/backtest-panel";

export default function AnalyticsRoute() {
  return (
    <div className="flex flex-col gap-3">
      <BacktestPanel />
      <HistoryPage />
    </div>
  );
}
