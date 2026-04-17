import { NextRequest, NextResponse } from "next/server";
import { apiError } from "@/lib/api-errors";
import {
  updateBrokerAccount,
  deleteBrokerAccount,
  activateBrokerAccount,
  getBrokerAccountById,
  encryptValue,
} from "@/lib/db";

export const dynamic = "force-dynamic";

/** PUT /api/broker/accounts/[id] — update a broker account */
export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: idStr } = await params;
  const id = Number(idStr);
  if (!id) return apiError("VALIDATION_ERROR", "Invalid id", 400);

  const account = await getBrokerAccountById(id);
  if (!account) return apiError("NOT_FOUND", "Account not found", 404);

  try {
    const body = await req.json();
    const { name, account_number, password, server, is_demo } = body;

    if (!name || !account_number || !server) {
      return NextResponse.json(
        { error: { code: "VALIDATION_ERROR", message: "Missing required fields" } },
        { status: 400 }
      );
    }

    await updateBrokerAccount(
      id,
      String(name).slice(0, 100),
      String(account_number).slice(0, 50),
      password ? encryptValue(String(password)) : null,
      String(server).slice(0, 100),
      Boolean(is_demo)
    );
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("[api/broker/accounts PUT]", (err as Error).message);
    return apiError("DB_ERROR", "Failed to update account", 500);
  }
}

/** DELETE /api/broker/accounts/[id] — delete a broker account */
export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: idStr } = await params;
  const id = Number(idStr);
  if (!id) return apiError("VALIDATION_ERROR", "Invalid id", 400);

  const account = await getBrokerAccountById(id);
  if (!account) return apiError("NOT_FOUND", "Account not found", 404);

  try {
    await deleteBrokerAccount(id);
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("[api/broker/accounts DELETE]", (err as Error).message);
    return apiError("DB_ERROR", "Failed to delete account", 500);
  }
}

/** PATCH /api/broker/accounts/[id] — activate a broker account */
export async function PATCH(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id: idStr } = await params;
  const id = Number(idStr);
  if (!id) return apiError("VALIDATION_ERROR", "Invalid id", 400);

  const account = await getBrokerAccountById(id);
  if (!account) return apiError("NOT_FOUND", "Account not found", 404);

  try {
    await activateBrokerAccount(id);
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("[api/broker/accounts PATCH]", (err as Error).message);
    return apiError("DB_ERROR", "Failed to activate account", 500);
  }
}
