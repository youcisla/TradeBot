import { NextResponse } from "next/server";
import { getAgentReputation, getLeaderboard } from "@/lib/db";

// GET /api/agents/reputation?name=  — single agent reputation
// GET /api/agents/leaderboard      — top agents by points
export async function GET(request: Request) {
  try {
    const { searchParams } = await request.nextUrl.searchParams;
    const name = searchParams.get("name");

    if (name) {
      const rep = await getAgentReputation(name);
      if (!rep) return NextResponse.json({ error: "Agent not found" }, { status: 404 });
      return NextResponse.json(rep);
    }

    const limit = Math.min(Number(searchParams.get("limit") ?? 10), 50);
    const board = await getLeaderboard(limit);
    return NextResponse.json(board);
  } catch (err) {
    console.error("[/api/agents/reputation]", (err as Error).message);
    return NextResponse.json({ error: "DB unavailable" }, { status: 503 });
  }
}
