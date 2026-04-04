import { NextResponse } from "next/server";
import { insertCommand } from "@/lib/db";

const ALLOWED_COMMANDS = new Set(["kill", "pause", "resume", "close_trade"]);

export async function POST(request: Request) {
  const body = await request.json();
  const command = String(body.command ?? "");
  if (!ALLOWED_COMMANDS.has(command)) {
    return NextResponse.json({ error: "Unknown command" }, { status: 400 });
  }

  await insertCommand(command, body.payload ?? undefined);
  return NextResponse.json({ ok: true, command });
}
