import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { getStrategyConfidences, getTradeScores } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const [confidences, scores] = await Promise.all([
    getStrategyConfidences(),
    getTradeScores(),
  ]);

  return NextResponse.json({ confidences, scores });
}
