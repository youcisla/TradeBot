import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { getOpenTrades, getAllTrades } from "@/lib/db";

export const dynamic = "force-dynamic";

const MAX_LIMIT = 500;

export async function GET(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  try {
    const { searchParams } = new URL(request.url);
    const all = searchParams.get("all") === "true";

    if (!all) {
      const trades = await getOpenTrades();
      return NextResponse.json(trades);
    }

    const limitParam = searchParams.get("limit");
    const cursorParam = searchParams.get("cursor"); // open_time of last seen row (ISO string)

    const limit = Math.min(
      MAX_LIMIT,
      limitParam ? Math.max(1, parseInt(limitParam, 10) || MAX_LIMIT) : MAX_LIMIT
    );

    const trades = await getAllTrades(limit, cursorParam ?? undefined);
    return NextResponse.json(trades);
  } catch (err) {
    console.error("[api/trades]", (err as Error).message);
    return NextResponse.json({ error: "DB temporarily unavailable" }, { status: 503 });
  }
}
