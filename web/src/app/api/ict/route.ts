import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import {
  getIctSetups,
  getIctModelStats,
  getIctConfluenceStats,
  getIctSessionStats,
} from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session)
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  try {
    const { searchParams } = new URL(request.url);
    const symbol = searchParams.get("symbol") || undefined;

    const [setups, modelStats, confluenceStats, sessionStats] =
      await Promise.all([
        getIctSetups(symbol),
        getIctModelStats(),
        getIctConfluenceStats(),
        getIctSessionStats(),
      ]);

    return NextResponse.json({
      setups,
      modelStats,
      confluenceStats: confluenceStats[0] ?? {},
      sessionStats,
    });
  } catch (err) {
    console.error("[api/ict]", (err as Error).message);
    return NextResponse.json(
      { error: "DB temporarily unavailable" },
      { status: 503 }
    );
  }
}
