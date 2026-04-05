import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { insertCommand } from "@/lib/db";
import { authOptions } from "@/lib/auth";

const ALLOWED_COMMANDS = new Set(["kill", "pause", "resume", "close_trade", "close_all", "tool"]);

export async function POST(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const command = String(body.command ?? "");
  if (!ALLOWED_COMMANDS.has(command)) {
    return NextResponse.json({ error: "Unknown command" }, { status: 400 });
  }

  await insertCommand(command, body.payload ?? undefined);
  const username = String((session.user as Record<string, unknown>).username ?? session.user.name ?? "unknown");
  return NextResponse.json({ ok: true, command, executedBy: username });
}
