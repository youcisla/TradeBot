import { NextResponse } from "next/server";
import { getBotStatus } from "@/lib/db";
import { swrCache } from "@/lib/api-cache";
import { apiError } from "@/lib/api-errors";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const status = await swrCache("bot_status", 3_000, getBotStatus);
    return NextResponse.json(status, {
      headers: { "Cache-Control": "public, s-maxage=3, stale-while-revalidate=5" },
    });
  } catch (err) {
    console.error("[api/status]", (err as Error).message);
    return apiError("DB_UNAVAILABLE", "DB temporarily unavailable", 503);
  }
}
