import { NextRequest, NextResponse } from "next/server";
import {
  getBrokerAccounts,
  addBrokerAccount,
  encryptValue,
} from "@/lib/db";
import { apiError } from "@/lib/api-errors";
import { BrokerAccountSchema } from "@/lib/api-validation";

export const dynamic = "force-dynamic";

/** GET /api/broker/accounts — list all broker accounts (no passwords) */
export async function GET() {
  // TODO(T3.2): Replace with real userId from auth session (e.g., getServerSession).
  //              Currently hardcoded as undefined — no auth gate on this endpoint.
  const userId = undefined as number | undefined;

  try {
    const accounts = await getBrokerAccounts(userId);
    return NextResponse.json(accounts);
  } catch (err) {
    console.error("[api/broker/accounts]", (err as Error).message);
    return apiError("DB_UNAVAILABLE", "DB temporarily unavailable", 503);
  }
}

/** POST /api/broker/accounts — add a new broker account */
export async function POST(req: NextRequest) {
  // TODO(T3.2): Replace with real userId from auth session.
  const userId = undefined as number | undefined;

  try {
    const body = await req.json();
    const parsed = BrokerAccountSchema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json(
        { error: { code: "VALIDATION_ERROR", message: parsed.error.message } },
        { status: 400 },
      );
    }

    const { name, account_number, password, server, is_demo } = parsed.data;
    const encryptedPwd = encryptValue(password);

    const id = await addBrokerAccount(
      name,
      account_number,
      encryptedPwd,
      server,
      is_demo,
      userId
    );
    return NextResponse.json({ id }, { status: 201 });
  } catch (err) {
    console.error("[api/broker/accounts POST]", (err as Error).message);
    return apiError("DB_ERROR", "Failed to add account", 500);
  }
}
