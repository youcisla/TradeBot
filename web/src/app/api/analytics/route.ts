import { NextResponse } from "next/server";
import {
  getClosedTrades,
  getSymbolStats,
  getDirectionStats,
  getDailyPnl,
  getKpis,
} from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const sinceRaw = searchParams.get("since") || undefined;
    if (sinceRaw) {
      const d = new Date(sinceRaw);
      if (isNaN(d.getTime())) {
        return NextResponse.json({ error: "Invalid since date" }, { status: 400 });
      }
    }
    const since = sinceRaw;
    const symbolRaw = searchParams.get("symbol") || undefined;
    if (symbolRaw && !/^[A-Z0-9]{3,10}$/.test(symbolRaw)) {
      return NextResponse.json({ error: "Invalid symbol" }, { status: 400 });
    }
    const symbol = symbolRaw;

    const [closedTrades, symbolStats, directionStats, dailyPnl, kpis] =
      await Promise.all([
        getClosedTrades(since, symbol),
        getSymbolStats(),
        getDirectionStats(),
        getDailyPnl(since),
        getKpis(),
      ]);

    return NextResponse.json({
      closedTrades,
      symbolStats,
      directionStats,
      dailyPnl,
      kpis: {
        winRate: kpis.total_trades > 0
          ? (Number(kpis.wins) / Number(kpis.total_trades)) * 100
          : 0,
        profitFactor: Number(kpis.avg_loss) !== 0
          ? Math.abs(Number(kpis.total_pnl) / Number(kpis.avg_loss))
          : 0,
        totalPnl:    Number(kpis.total_pnl) || 0,
        avgWin:      Number(kpis.avg_win) || 0,
        avgLoss:     Number(kpis.avg_loss) || 0,
        expectancy:  Number(kpis.avg_pnl) || 0,
        totalTrades: Number(kpis.total_trades) || 0,
        bestTrade:   Number(kpis.best_trade) || 0,
        worstTrade:  Number(kpis.worst_trade) || 0,
      },
    });
  } catch (err) {
    console.error("[api/analytics]", (err as Error).message);
    return NextResponse.json(
      { error: "DB temporarily unavailable" },
      { status: 503 }
    );
  }
}
