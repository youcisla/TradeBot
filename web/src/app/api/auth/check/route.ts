import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * GET /api/auth/check — kept for backwards compatibility.
 * Auto-signup has been removed; always returns firstLogin: false.
 * To create the first dashboard user run: python scripts/reset_dashboard_user.py
 */
export async function GET() {
  return NextResponse.json({ firstLogin: false });
}
