import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";

export const dynamic = "force-dynamic";

const CRUCIX_URL = process.env.CRUCIX_URL || "http://localhost:3117";

export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  try {
    const res = await fetch(`${CRUCIX_URL}/api/data`, {
      signal: AbortSignal.timeout(4_000),
      cache: "no-store",
    });
    if (!res.ok) return NextResponse.json({ available: false }, { status: 200 });
    const data = await res.json();
    return NextResponse.json({ available: true, ...data });
  } catch {
    return NextResponse.json({ available: false }, { status: 200 });
  }
}
