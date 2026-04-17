import { NextResponse } from "next/server";
import { getSubscriptions, followLeader, unfollowLeader } from "@/lib/db";
import { apiError } from "@/lib/api-errors";

// GET /api/subscriptions?follower=&leader=  — list subscriptions
// POST /api/subscriptions                — follow a leader
// DELETE /api/subscriptions?leader=&follower= — unfollow
export async function GET(request: Request) {
  try {
    const { searchParams } = await request.nextUrl.searchParams;
    const subs = await getSubscriptions({
      follower: searchParams.get("follower") ?? undefined,
      leader:   searchParams.get("leader")   ?? undefined,
    });
    return NextResponse.json(subs);
  } catch (err) {
    console.error("[/api/subscriptions GET]", (err as Error).message);
    return apiError("DB_UNAVAILABLE", "DB unavailable", 503);
  }
}

export async function POST(request: Request) {
  try {
    const { follower_id, leader_id, leader_strategy } = await request.json();
    if (!follower_id || !leader_id) {
      return apiError("VALIDATION_ERROR", "follower_id and leader_id are required", 400);
    }
    const id = await followLeader(
      follower_id,
      leader_id,
      leader_strategy ?? "all"
    );
    return NextResponse.json({ id }, { status: 201 });
  } catch (err) {
    console.error("[/api/subscriptions POST]", (err as Error).message);
    return apiError("DB_ERROR", "Failed to follow", 500);
  }
}

export async function DELETE(request: Request) {
  try {
    const { searchParams } = await request.nextUrl.searchParams;
    const follower_id = searchParams.get("follower");
    const leader_id   = searchParams.get("leader");
    if (!follower_id || !leader_id) {
      return apiError("VALIDATION_ERROR", "follower and leader query params are required", 400);
    }
    const deleted = await unfollowLeader(follower_id, leader_id);
    return NextResponse.json({ ok: deleted });
  } catch (err) {
    console.error("[/api/subscriptions DELETE]", (err as Error).message);
    return apiError("DB_ERROR", "Failed to unfollow", 500);
  }
}
