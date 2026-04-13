import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const CANDLE_SERVER = process.env.CANDLE_SERVER_URL ?? "http://localhost:5555";

export async function GET(request: Request) {
  try {
    const { searchParams } = await new URL(request.url);
    const jobId = searchParams.get("jobId");

    if (!jobId) {
      return NextResponse.json(
        { error: { code: "BAD_REQUEST", message: "jobId is required" } },
        { status: 400 },
      );
    }

    const res = await fetch(
      `${CANDLE_SERVER}/api/backtest/status?jobId=${encodeURIComponent(jobId)}`,
      { signal: AbortSignal.timeout(10_000) },
    );

    const data = await res.json();
    return NextResponse.json(data, {
      headers: { "Cache-Control": "no-store" },
      status: res.status,
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error("[/api/backtest/status]", msg);
    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: "Failed to get backtest status" } },
      { status: 500 },
    );
  }
}
