import { NextResponse } from "next/server";
import { getBotStatus, getOpenTrades } from "@/lib/db";
import { swrCache } from "@/lib/api-cache";
import { apiError } from "@/lib/api-errors";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const [status, trades] = await Promise.all([
      swrCache("bot_status", 5_000, getBotStatus),
      swrCache("open_trades", 3_000, getOpenTrades),
    ]);

    if (!status) throw new Error("bot_status unavailable");

    return NextResponse.json(
      {
        status: {
          state:           status.state,
          equity:          status.equity,
          balance:         status.balance,
          daily_pnl:       status.daily_pnl,
          open_trades:     status.open_trades,
          loop_count:      (status as unknown as Record<string, unknown>)?.loop_count,
          last_tick:       status.last_tick,
          uptime_start:    status.uptime_start,
          guard_status:    status.guard_status,
          broker_account:  (status as unknown as Record<string, unknown>)?.broker_account as string | undefined,
          broker_server:   (status as unknown as Record<string, unknown>)?.broker_server as string | undefined,
          broker_name:     (status as unknown as Record<string, unknown>)?.broker_name as string | undefined,
          leverage:        Number((status as unknown as Record<string, unknown>)?.leverage ?? 0) || undefined,
          last_scan_latency_ms: (status as unknown as Record<string, unknown>)?.last_scan_latency_ms as number | undefined,
          last_reconnect_at:   (status as unknown as Record<string, unknown>)?.last_reconnect_at as string | undefined,
        },
        openTrades: trades,
        ts: Date.now(),
      },
      {
        headers: {
          "Cache-Control": "public, s-maxage=5, stale-while-revalidate=5",
        },
      }
    );
  } catch (err) {
    console.error("[api/dashboard-summary]", (err as Error).message);
    return apiError("DB_UNAVAILABLE", "DB temporarily unavailable", 503);
  }
}