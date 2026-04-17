import { NextResponse } from "next/server";
import { apiError } from "@/lib/api-errors";

export const dynamic = "force-dynamic";

// The candle server runs inside the Python bot on this port.
// Next.js proxies /api/broker/trades → candle server /trades
const CANDLE_SERVER = process.env.CANDLE_SERVER_URL || "http://localhost:5555";

export async function GET(request: Request) {
  try {
    const { searchParams } = await request.nextUrl.searchParams;
    const days = searchParams.get("days") || "7";

    const res = await fetch(
      `${CANDLE_SERVER}/trades?days=${encodeURIComponent(days)}`,
      { signal: AbortSignal.timeout(10_000) }
    );

    if (!res.ok) {
      return apiError("UPSTREAM_ERROR", "Broker service unavailable", 502);
    }

    const data = await res.json();
    return NextResponse.json(data, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error("[/api/broker/trades]", msg);
    return apiError("UPSTREAM_ERROR", "Broker service unavailable", 502);
  }
}
