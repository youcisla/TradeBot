import { NextResponse } from "next/server";
import { getStrategyConfidences, getTradeScores } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const [confidences, scores] = await Promise.all([
      getStrategyConfidences(),
      getTradeScores(),
    ]);

    return NextResponse.json({ confidences, scores });
  } catch (err) {
    console.error("[api/learning]", (err as Error).message);
    return NextResponse.json({ error: "DB temporarily unavailable" }, { status: 503 });
  }
}
