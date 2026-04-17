import { NextResponse } from "next/server";
import { getToolCycleEvents, getToolSystemEvents } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  try {
    const { searchParams } = await request.nextUrl.searchParams;
    const cycleLimit = Math.min(Number(searchParams.get("cycleLimit") ?? 50), 500);
    const eventLimit = Math.min(Number(searchParams.get("eventLimit") ?? 200), 1000);

    const [cycles, events] = await Promise.all([
      getToolCycleEvents(cycleLimit),
      getToolSystemEvents(eventLimit),
    ]);

    return NextResponse.json({ cycles, events });
  } catch (err) {
    console.error("[api/tools]", (err as Error).message);
    return NextResponse.json({ error: "DB temporarily unavailable" }, { status: 503 });
  }
}
