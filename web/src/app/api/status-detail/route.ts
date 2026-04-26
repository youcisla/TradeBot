import { NextRequest, NextResponse } from "next/server";
import { pool } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const client = await pool.connect();
    try {
      const [statusRows, perfRows, faultRows, sessionRows] = await Promise.all([
        client.query("SELECT * FROM bot_status WHERE id = 1"),
        client.query("SELECT * FROM performance_snapshots ORDER BY created_at DESC LIMIT 1"),
        client.query("SELECT * FROM symbol_fault WHERE disabled_until > NOW() ORDER BY fail_count DESC"),
        client.query("SELECT id, started_at, ended_at, version, exit_reason FROM bot_sessions ORDER BY started_at DESC LIMIT 3"),
      ]);

      const status = statusRows.rows[0] ?? null;
      const perf = perfRows.rows[0] ?? null;
      const faults = faultRows.rows ?? [];
      const sessions = sessionRows.rows ?? [];

      return NextResponse.json(
        { status, performance: perf, symbolFaults: faults, sessions },
        {
          headers: {
            "Cache-Control": "public, s-maxage=3, stale-while-revalidate=5",
          },
        }
      );
    } finally {
      client.release();
    }
  } catch (err) {
    console.error("[api/status-detail]", (err as Error).message);
    return NextResponse.json(
      { error: "DB temporarily unavailable" },
      { status: 503 }
    );
  }
}