import { NextResponse } from "next/server";
import { apiError } from "@/lib/api-errors";
import { getFollowers } from "@/lib/db";

// GET /api/subscriptions/followers?leader=  — get all followers of a leader
export async function GET(request: Request) {
  try {
    const { searchParams } = await request.nextUrl.searchParams;
    const leader = searchParams.get("leader");
    if (!leader) {
      return apiError("VALIDATION_ERROR", "leader query param required", 400);
    }
    const followers = await getFollowers(leader);
    return NextResponse.json(followers);
  } catch (err) {
    console.error("[/api/subscriptions/followers]", (err as Error).message);
    return apiError("DB_UNAVAILABLE", "DB unavailable", 503);
  }
}
