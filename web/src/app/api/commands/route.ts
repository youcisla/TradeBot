import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import { insertCommand } from "@/lib/db";

const ALLOWED_COMMANDS = new Set(["kill", "pause", "resume", "close_trade"]);

export async function POST(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await request.json();
  const command = String(body.command ?? "");
  if (!ALLOWED_COMMANDS.has(command)) {
    return NextResponse.json({ error: "Unknown command" }, { status: 400 });
  }

  await insertCommand(command, body.payload ?? undefined);
  return NextResponse.json({ ok: true, command });
}
