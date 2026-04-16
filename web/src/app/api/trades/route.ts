import { NextResponse } from "next/server";
import { getOpenTrades, getAllTrades } from "@/lib/db";
import { swrCache } from "@/lib/api-cache";

export const dynamic = "force-dynamic";

const MAX_LIMIT = 500;

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const all = searchParams.get("all") === "true";

    if (!all) {
      const trades = await swrCache("open_trades", 3_000, getOpenTrades);
      return NextResponse.json(trades, {
        headers: { "Cache-Control": "public, s-maxage=3, stale-while-revalidate=5" },
      });
    }

    const limitParam = searchParams.get("limit");
    const cursorParam = searchParams.get("cursor"); // open_time of last seen row (ISO string)

    const limit = Math.min(
      MAX_LIMIT,
      limitParam ? Math.max(1, parseInt(limitParam, 10) || MAX_LIMIT) : MAX_LIMIT
    );

    const trades = await swrCache(`all_trades_${limit}_${cursorParam ?? ""}`, 10_000, () =>
      getAllTrades(limit, cursorParam ?? undefined)
    );
    return NextResponse.json(trades, {
      headers: { "Cache-Control": "public, s-maxage=10, stale-while-revalidate=15" },
    });
  } catch (err) {
    console.error("[api/trades]", (err as Error).message);
    return NextResponse.json({ error: "DB temporarily unavailable" }, { status: 503 });
  }
}
