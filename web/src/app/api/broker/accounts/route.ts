import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import {
  getBrokerAccounts,
  addBrokerAccount,
  encryptValue,
} from "@/lib/db";

export const dynamic = "force-dynamic";

/** GET /api/broker/accounts — list all broker accounts (no passwords) */
export async function GET() {
  const session = await getServerSession(authOptions);
  if (!session)
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const userId = (session.user as Record<string, unknown>)?.id as number | undefined;

  try {
    const accounts = await getBrokerAccounts(userId);
    return NextResponse.json(accounts);
  } catch (err) {
    console.error("[api/broker/accounts]", (err as Error).message);
    return NextResponse.json(
      { error: "DB temporarily unavailable" },
      { status: 503 }
    );
  }
}

/** POST /api/broker/accounts — add a new broker account */
export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions);
  if (!session)
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const userId = (session.user as Record<string, unknown>)?.id as number | undefined;

  try {
    const body = await req.json();
    const { name, account_number, password, server, is_demo } = body;

    if (!name || !account_number || !password || !server) {
      return NextResponse.json(
        { error: "Missing required fields" },
        { status: 400 }
      );
    }

    const encryptedPwd = encryptValue(String(password));

    const id = await addBrokerAccount(
      String(name).slice(0, 100),
      String(account_number).slice(0, 50),
      encryptedPwd,
      String(server).slice(0, 100),
      Boolean(is_demo),
      userId
    );
    return NextResponse.json({ id }, { status: 201 });
  } catch (err) {
    console.error("[api/broker/accounts POST]", (err as Error).message);
    return NextResponse.json({ error: "Failed to add account" }, { status: 500 });
  }
}
