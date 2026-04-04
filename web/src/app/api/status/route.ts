import { NextResponse } from "next/server";
import { getBotStatus } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const status = await getBotStatus();
    return NextResponse.json(status, {
      headers: { "Cache-Control": "public, s-maxage=3" },
    });
  } catch (err) {
    console.error("[api/status]", (err as Error).message);
    return NextResponse.json({ error: "DB temporarily unavailable" }, { status: 503 });
  }
}
