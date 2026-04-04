import { NextResponse } from "next/server";
import { getAgentEvents } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = Math.min(Number(searchParams.get("limit") ?? 80), 500);

    const events = await getAgentEvents(limit);
    return NextResponse.json(events);
  } catch (err) {
    console.error("[api/events]", (err as Error).message);
    return NextResponse.json({ error: "DB temporarily unavailable" }, { status: 503 });
  }
}
