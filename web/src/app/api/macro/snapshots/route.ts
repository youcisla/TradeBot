import { NextResponse } from "next/server";
import { getMacroSnapshots } from "@/lib/db";

// GET /api/macro/snapshots?lookback_hours=&risk_tier=&limit=
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const snapshots = await getMacroSnapshots({
      lookback_hours: Number(searchParams.get("lookback_hours") ?? 24),
      risk_tier:      searchParams.get("risk_tier") ?? undefined,
      limit:          Math.min(Number(searchParams.get("limit") ?? 100), 500),
    });
    return NextResponse.json(snapshots, {
      headers: { "Cache-Control": "public, s-maxage=60, stale-while-revalidate=300" },
    });
  } catch (err) {
    console.error("[/api/macro/snapshots]", (err as Error).message);
    return NextResponse.json({ error: "DB unavailable" }, { status: 503 });
  }
}
