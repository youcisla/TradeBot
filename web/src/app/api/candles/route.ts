import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";

export const dynamic = "force-dynamic";

const CANDLE_SERVER = process.env.CANDLE_SERVER_URL || "http://localhost:5555";

export async function GET(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session)
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { searchParams } = new URL(request.url);
  const symbol = searchParams.get("symbol") || "EURUSD";
  const timeframe = searchParams.get("timeframe") || "H1";
  const count = searchParams.get("count") || "500";

  try {
    const url = `${CANDLE_SERVER}/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&count=${encodeURIComponent(count)}`;
    const res = await fetch(url, { signal: AbortSignal.timeout(10_000) });

    if (!res.ok) {
      const body = await res.text();
      return NextResponse.json(
        { error: body || "Candle server error" },
        { status: res.status }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch (err) {
    console.error("[api/candles]", (err as Error).message);
    return NextResponse.json(
      { error: "Candle server unavailable — is the bot running?" },
      { status: 503 }
    );
  }
}
