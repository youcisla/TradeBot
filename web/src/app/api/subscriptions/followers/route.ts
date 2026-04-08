import { NextResponse } from "next/server";
import { getFollowers } from "@/lib/db";

// GET /api/subscriptions/followers?leader=  — get all followers of a leader
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const leader = searchParams.get("leader");
    if (!leader) {
      return NextResponse.json({ error: "leader query param required" }, { status: 400 });
    }
    const followers = await getFollowers(leader);
    return NextResponse.json(followers);
  } catch (err) {
    console.error("[/api/subscriptions/followers]", (err as Error).message);
    return NextResponse.json({ error: "DB unavailable" }, { status: 503 });
  }
}
