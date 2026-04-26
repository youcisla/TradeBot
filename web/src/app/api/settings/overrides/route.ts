import { NextRequest, NextResponse } from "next/server";
import { pool } from "@/lib/db";

export const dynamic = "force-dynamic";

// GET /api/settings/overrides — list all overrides
export async function GET() {
  try {
    const client = await pool.connect();
    try {
      const result = await client.query(
        "SELECT key, value, updated_at FROM bot_settings_overrides ORDER BY key"
      );
      return NextResponse.json({ overrides: result.rows });
    } finally {
      client.release();
    }
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}

// POST /api/settings/overrides — upsert override
export async function POST(req: NextRequest) {
  try {
    const { key, value } = await req.json();
    if (!key || typeof value !== "string") {
      return NextResponse.json({ error: "key and value are required" }, { status: 400 });
    }

    const client = await pool.connect();
    try {
      await client.query(
        `INSERT INTO bot_settings_overrides (key, value, updated_at)
         VALUES ($1, $2, NOW())
         ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value, updated_at = NOW()`,
        [key, value]
      );
      await client.query(
        `INSERT INTO bot_commands (command, payload, status, created_at)
         VALUES ('set_override', $1::jsonb, 'pending', NOW())`,
        [JSON.stringify({ key, value })]
      );
      return NextResponse.json({ ok: true, key, value });
    } finally {
      client.release();
    }
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}

// DELETE /api/settings/overrides — clear an override
export async function DELETE(req: NextRequest) {
  try {
    const { key } = await req.json();
    if (!key) return NextResponse.json({ error: "key is required" }, { status: 400 });

    const client = await pool.connect();
    try {
      await client.query("DELETE FROM bot_settings_overrides WHERE key = $1", [key]);
      await client.query(
        `INSERT INTO bot_commands (command, payload, status, created_at)
         VALUES ('clear_override', $1::jsonb, 'pending', NOW())`,
        [JSON.stringify({ key })]
      );
      return NextResponse.json({ ok: true, key });
    } finally {
      client.release();
    }
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}