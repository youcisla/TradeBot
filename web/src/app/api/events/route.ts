import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { getAgentEvents } from "@/lib/db";

export const dynamic = "force-dynamic";

// 30-second TTL session cache to avoid re-running next-auth on every 400ms poll
const sessionCache = new Map<string, { expires: number }>();

async function isAuthorized(request: Request): Promise<boolean> {
  // Use cookie header as cache key (avoids DB hit on every rapid poll)
  const cookieHeader = request.headers.get("cookie") ?? "";
  const cached = sessionCache.get(cookieHeader);
  if (cached && cached.expires > Date.now()) return true;

  const session = await getServerSession(authOptions);
  if (session) {
    sessionCache.set(cookieHeader, { expires: Date.now() + 30_000 });
    // Prevent unbounded growth
    if (sessionCache.size > 500) {
      const now = Date.now();
      for (const [key, val] of sessionCache) {
        if (val.expires <= now) sessionCache.delete(key);
      }
    }
    return true;
  }
  return false;
}

export async function GET(request: Request) {
  if (!(await isAuthorized(request))) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

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
