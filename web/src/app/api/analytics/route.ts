import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import {
  getClosedTrades,
  getSymbolStats,
  getDirectionStats,
  getDailyPnl,
  getKpis,
} from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session)
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

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
      kpis,
    });
  } catch (err) {
    console.error("[api/analytics]", (err as Error).message);
    return NextResponse.json(
      { error: "DB temporarily unavailable" },
      { status: 503 }
    );
  }
}
