import { NextResponse } from "next/server";
import { getAgentEvents } from "@/lib/db";
import { apiError } from "@/lib/api-errors";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const { searchParams } = await request.nextUrl.searchParams;
    const limit = Math.min(Number(searchParams.get("limit") ?? 80), 500);

    const events = await getAgentEvents(limit);
    return NextResponse.json(events, {
      headers: { "Cache-Control": "public, s-maxage=2, must-revalidate" },
    });
  } catch (err) {
    console.error("[api/events]", (err as Error).message);
    return apiError("DB_UNAVAILABLE", "DB temporarily unavailable", 503);
  }
}
