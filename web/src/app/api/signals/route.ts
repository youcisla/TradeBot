import { NextResponse } from "next/server";
import { getSignals, publishSignal } from "@/lib/db";

// GET /api/signals  — signal feed (mirrors AI-Trader /api/signals/feed)
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const signals = await getSignals({
      intent:   searchParams.get("intent")   ?? undefined,
      type:     searchParams.get("type")     ?? undefined,
      strategy: searchParams.get("strategy") ?? undefined,
      author:   searchParams.get("author")   ?? undefined,
      limit:    Math.min(Number(searchParams.get("limit") ?? 50), 200),
    });
    return NextResponse.json(signals, {
      headers: { "Cache-Control": "public, s-maxage=5, must-revalidate" },
    });
  } catch (err) {
    console.error("[/api/signals GET]", (err as Error).message);
    return NextResponse.json({ error: "DB unavailable" }, { status: 503 });
  }
}

// POST /api/signals  — publish a new signal
export async function POST(request: Request) {
  try {
    const body = await request.json();

    const { signal_intent, signal_type, strategy } = body;
    if (!signal_intent || !signal_type || !strategy) {
      return NextResponse.json(
        { error: "signal_intent, signal_type, and strategy are required" },
        { status: 400 }
      );
    }
    if (!["DISCUSSION", "STRATEGY", "OPERATION"].includes(signal_type)) {
      return NextResponse.json(
        { error: "signal_type must be DISCUSSION, STRATEGY, or OPERATION" },
        { status: 400 }
      );
    }
    if (!["DISCUSSION", "STRATEGY", "EXECUTION"].includes(signal_intent)) {
      return NextResponse.json(
        { error: "signal_intent must be DISCUSSION, STRATEGY, or EXECUTION" },
        { status: 400 }
      );
    }

    const id = await publishSignal(body);
    return NextResponse.json({ id }, { status: 201 });
  } catch (err) {
    console.error("[/api/signals POST]", (err as Error).message);
    return NextResponse.json({ error: "Failed to publish signal" }, { status: 500 });
  }
}
