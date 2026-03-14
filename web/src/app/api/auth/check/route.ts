import { NextResponse } from "next/server";
import { getUserCount } from "@/lib/db";

export const dynamic = "force-dynamic";

/** GET /api/auth/check — returns whether this is the first login (no users) */
export async function GET() {
  try {
    const count = await getUserCount();
    return NextResponse.json({ firstLogin: count === 0 });
  } catch {
    return NextResponse.json({ firstLogin: false });
  }
}
