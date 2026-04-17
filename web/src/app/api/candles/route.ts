import { NextResponse } from "next/server";
import { apiError } from "@/lib/api-errors";

export const dynamic = "force-dynamic";

const CANDLE_SERVER = process.env.CANDLE_SERVER_URL || "http://localhost:5555";

export async function GET(request: Request) {
  const { searchParams } = await request.nextUrl.searchParams;
  const rawSymbol = searchParams.get("symbol") || "EURUSD";
  const rawTimeframe = searchParams.get("timeframe") || "H1";
  const count = searchParams.get("count") || "500";

  // Normalise: BTC/USD → BTCUSD, remove spaces/dashes
  const symbol = rawSymbol.replace("/", "").replace(" ", "").replace("-", "").toUpperCase();
  if (!/^[A-Z0-9]{3,10}$/.test(symbol)) {
    return apiError("VALIDATION_ERROR", "Invalid symbol", 400);
  }

  // Normalise timeframes: 1m→M1, 5m→M5, 15m→M15, 30m→M30, 1h→H1, 4h→H4, 1d→D1, 1w→W1, 1M→MN1
  const tfMap: Record<string, string> = {
    "1m": "M1", "5m": "M5", "15m": "M15", "30m": "M30",
    "1h": "H1", "4h": "H4", "1d": "D1", "1w": "W1", "1M": "MN1",
    "M1": "M1", "M5": "M5", "M15": "M15", "M30": "M30",
    "H1": "H1", "H4": "H4", "D1": "D1", "W1": "W1", "MN1": "MN1",
  };
  const timeframe = tfMap[rawTimeframe] || rawTimeframe;
  if (!/^(M1|M5|M15|M30|H1|H4|D1|W1|MN1)$/.test(timeframe)) {
    return apiError("VALIDATION_ERROR", "Invalid timeframe", 400);
  }
  const countNum = parseInt(count, 10);
  if (isNaN(countNum) || countNum < 1 || countNum > 1000) {
    return apiError("VALIDATION_ERROR", "count must be 1–1000", 400);
  }

  try {
    const url = `${CANDLE_SERVER}/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&count=${encodeURIComponent(count)}`;
    const res = await fetch(url, { signal: AbortSignal.timeout(30_000) });

    if (!res.ok) {
      return apiError("UPSTREAM_ERROR", "Candle server error", res.status);
    }

    const data = await res.json();
    return NextResponse.json(data, {
      headers: {
        "Cache-Control": "public, s-maxage=5, stale-while-revalidate=30",
      },
    });
  } catch (err) {
    console.error("[api/candles]", (err as Error).message);
    return apiError("UPSTREAM_ERROR", "Candle server unavailable", 503);
  }
}
