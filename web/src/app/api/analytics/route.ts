import { NextRequest, NextResponse } from "next/server";
import {
  getClosedTrades,
  getSymbolStats,
  getDirectionStats,
  getDailyPnl,
  getKpis,
} from "@/lib/db";
import { apiError } from "@/lib/api-errors";

export const dynamic = "force-dynamic";

// In-memory rate-limit store (60s window, 1 req/min per IP)
const rateLimitStore = new Map<string, number>();

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;

    // ── Pagination ──────────────────────────────────────────
    const limitRaw = searchParams.get("limit") || "50";
    const limitNum = Math.min(100, Math.max(1, parseInt(limitRaw, 10) || 50));
    const cursor = searchParams.get("cursor") || undefined;

    // ── Filters ────────────────────────────────────────────
    const sinceRaw = searchParams.get("since") || undefined;
    if (sinceRaw) {
      const d = new Date(sinceRaw);
      if (isNaN(d.getTime())) {
        return apiError("VALIDATION_ERROR", "Invalid since date", 400);
      }
    }
    const since = sinceRaw;

    const symbolRaw = searchParams.get("symbol") || undefined;
    if (symbolRaw && !/^[A-Z0-9]{3,10}$/.test(symbolRaw)) {
      return apiError("VALIDATION_ERROR", "Invalid symbol", 400);
    }
    const symbol = symbolRaw;

    // ── Rate-limit gate (in-memory, per-IP, 60s window) ───
    const ip = request.headers.get("x-forwarded-for")?.split(",")[0].trim() ?? "unknown";
    const now = Date.now();
    const last = rateLimitStore.get(ip) ?? 0;
    if (now - last < 60_000) {
      return apiError("RATE_LIMITED", "Slow down — max 1 req/min", 429);
    }
    rateLimitStore.set(ip, now);

    const [closedTrades, symbolStats, directionStats, dailyPnl, kpis] =
      await Promise.all([
        getClosedTrades(since, symbol, { limit: limitNum, cursor }),
        getSymbolStats(),
        getDirectionStats(),
        getDailyPnl(since),
        getKpis() as Promise<{
          total_trades: number; wins: number; total_pnl: number;
          avg_loss: number; avg_win: number; avg_pnl: number;
          best_trade: number; worst_trade: number;
        }>,
      ]);

    // Build next-cursor from the last trade's close_time
    let nextCursor: string | undefined;
    if (closedTrades.length === limitNum) {
      const lastTrade = closedTrades[closedTrades.length - 1];
      nextCursor = lastTrade.close_time ?? undefined;
    }

    return NextResponse.json(
      {
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
        pagination: { nextCursor },
      },
      { headers: { "Cache-Control": "private, max-age=30" } }
    );
  } catch (err) {
    console.error("[api/analytics]", (err as Error).message);
    return apiError("DB_UNAVAILABLE", "DB temporarily unavailable", 503);
  }
}
