import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

// The candle server runs inside the Python bot on this port.
// Next.js proxies /api/broker/trades → candle server /trades
const CANDLE_SERVER = process.env.CANDLE_SERVER_URL || "http://localhost:5555";

export async function GET(request: Request) {
  try {
    const url = new URL(request.url);
    const days = url.searchParams.get("days") || "7";

    const res = await fetch(
      `${CANDLE_SERVER}/trades?days=${encodeURIComponent(days)}`,
      { signal: AbortSignal.timeout(10_000) }
    );

    if (!res.ok) {
      const body = await res.text();
      return NextResponse.json({ error: body }, { status: res.status });
    }

    const data = await res.json();
    return NextResponse.json(data, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error("[/api/broker/trades]", msg);
    return NextResponse.json(
      { error: "Broker server unavailable — is the bot running?" },
      { status: 503 }
    );
  }
}
