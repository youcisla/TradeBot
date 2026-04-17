import { NextResponse } from "next/server";
import { getSignals, publishSignal } from "@/lib/db";
import { apiError } from "@/lib/api-errors";
import { rateLimit, SignalSchema } from "@/lib/api-validation";

// GET /api/signals  — signal feed (mirrors AI-Trader /api/signals/feed)
export async function GET(request: Request) {
  try {
    const { searchParams } = await request.nextUrl.searchParams;
    const signals = await getSignals({
      intent:   searchParams.get("intent")   ?? undefined,
      type:     searchParams.get("type")     ?? undefined,
      strategy: searchParams.get("strategy") ?? undefined,
      author:   searchParams.get("author")   ?? undefined,
      source:   searchParams.get("source")   ?? undefined,
      limit:    Math.min(Number(searchParams.get("limit") ?? 50), 200),
    });
    return NextResponse.json(signals, {
      headers: { "Cache-Control": "public, s-maxage=5, must-revalidate" },
    });
  } catch (err) {
    console.error("[/api/signals GET]", (err as Error).message);
    return apiError("DB_UNAVAILABLE", "DB unavailable", 503);
  }
}

// POST /api/signals  — publish a new signal
export async function POST(request: Request) {
  const ip = request.headers.get("x-forwarded-for")?.split(",")[0]?.trim() ?? "unknown";
  if (!rateLimit(ip)) {
    return NextResponse.json(
      { error: { code: "RATE_LIMITED", message: "Slow down — max 1 req/min" } },
      { status: 429 },
    );
  }

  try {
    const body = await request.json();
    const parsed = SignalSchema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json(
        { error: { code: "VALIDATION_ERROR", message: parsed.error.message } },
        { status: 400 },
      );
    }

    const id = await publishSignal(parsed.data);
    return NextResponse.json({ id }, { status: 201 });
  } catch (err) {
    console.error("[/api/signals POST]", (err as Error).message);
    return apiError("DB_ERROR", "Failed to publish signal", 500);
  }
}
