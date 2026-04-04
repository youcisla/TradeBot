import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const CANDLE_SERVER = process.env.CANDLE_SERVER_URL || "http://localhost:5555";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const symbol = searchParams.get("symbol") || "EURUSD";
  const timeframe = searchParams.get("timeframe") || "H1";
  const count = searchParams.get("count") || "500";

  // Validate inputs before forwarding to the internal candle server
  if (!/^[A-Z0-9]{3,10}$/.test(symbol)) {
    return NextResponse.json({ error: "Invalid symbol" }, { status: 400 });
  }
  if (!/^(M1|M5|M15|M30|H1|H4|D1|W1|MN1)$/.test(timeframe)) {
    return NextResponse.json({ error: "Invalid timeframe" }, { status: 400 });
  }
  const countNum = parseInt(count, 10);
  if (isNaN(countNum) || countNum < 1 || countNum > 1000) {
    return NextResponse.json({ error: "count must be 1–1000" }, { status: 400 });
  }

  try {
    const url = `${CANDLE_SERVER}/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&count=${encodeURIComponent(count)}`;
    const res = await fetch(url, { signal: AbortSignal.timeout(30_000) });

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
