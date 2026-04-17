import { NextRequest, NextResponse } from "next/server";
import { rateLimit, BacktestRunSchema } from "@/lib/api-validation";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const CANDLE_SERVER = process.env.CANDLE_SERVER_URL ?? "http://localhost:5555";

export async function POST(request: NextRequest) {
  const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  if (!rateLimit(ip)) {
    return NextResponse.json(
      { error: { code: "RATE_LIMITED", message: "Slow down — max 1 req/min" } },
      { status: 429 },
    );
  }

  try {
    const body = await request.json();
    const parsed = BacktestRunSchema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json(
        { error: { code: "VALIDATION_ERROR", message: parsed.error.message } },
        { status: 400 },
      );
    }

    const { symbol, strategy = "ict_smc" } = parsed.data;

    const res = await fetch(`${CANDLE_SERVER}/api/backtest/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ symbol: symbol.toUpperCase(), strategy }),
      signal: AbortSignal.timeout(30_000),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error("[/api/backtest/run]", msg);
    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: "Failed to start backtest" } },
      { status: 500 },
    );
  }
}
