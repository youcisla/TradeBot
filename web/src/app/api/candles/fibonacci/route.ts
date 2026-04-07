import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const CANDLE_SERVER = process.env.CANDLE_SERVER_URL || "http://localhost:5555";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const rawSymbol = searchParams.get("symbol") || "EURUSD";
  // Normalise: BTC/USD → BTCUSD, remove spaces/dashes
  const symbol = rawSymbol.replace("/", "").replace(" ", "").replace("-", "").toUpperCase();

  try {
    const url = `${CANDLE_SERVER}/fibonacci?symbol=${encodeURIComponent(symbol)}`;
    const res = await fetch(url, { signal: AbortSignal.timeout(5_000) });

    if (!res.ok) {
      return NextResponse.json(
        { levels: [], golden_zone: null },
        { status: 200 }
      );
    }

    const data = await res.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { levels: [], golden_zone: null },
      { status: 200 }
    );
  }
}
