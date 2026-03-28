import { NextRequest, NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
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
  const session = await getServerSession(authOptions);
  if (!session)
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const userId = (session.user as Record<string, unknown>)?.id as number | undefined;
  const { id: idStr } = await params;
  const id = Number(idStr);
  if (!id) return NextResponse.json({ error: "Invalid id" }, { status: 400 });

  const account = await getBrokerAccountById(id);
  if (!account) return NextResponse.json({ error: "Not found" }, { status: 404 });
  if (account.user_id !== null && account.user_id !== userId)
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });

  try {
    const body = await req.json();
    const { name, account_number, password, server, is_demo } = body;

    if (!name || !account_number || !server) {
      return NextResponse.json(
        { error: "Missing required fields" },
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
    return NextResponse.json({ error: "Failed to update" }, { status: 500 });
  }
}

/** DELETE /api/broker/accounts/[id] — delete a broker account */
export async function DELETE(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const session = await getServerSession(authOptions);
  if (!session)
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const userId = (session.user as Record<string, unknown>)?.id as number | undefined;
  const { id: idStr } = await params;
  const id = Number(idStr);
  if (!id) return NextResponse.json({ error: "Invalid id" }, { status: 400 });

  const account = await getBrokerAccountById(id);
  if (!account) return NextResponse.json({ error: "Not found" }, { status: 404 });
  if (account.user_id !== null && account.user_id !== userId)
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });

  try {
    await deleteBrokerAccount(id);
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("[api/broker/accounts DELETE]", (err as Error).message);
    return NextResponse.json({ error: "Failed to delete" }, { status: 500 });
  }
}

/** PATCH /api/broker/accounts/[id] — activate a broker account */
export async function PATCH(
  _req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const session = await getServerSession(authOptions);
  if (!session)
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const userId = (session.user as Record<string, unknown>)?.id as number | undefined;
  const { id: idStr } = await params;
  const id = Number(idStr);
  if (!id) return NextResponse.json({ error: "Invalid id" }, { status: 400 });

  const account = await getBrokerAccountById(id);
  if (!account) return NextResponse.json({ error: "Not found" }, { status: 404 });
  if (account.user_id !== null && account.user_id !== userId)
    return NextResponse.json({ error: "Forbidden" }, { status: 403 });

  try {
    await activateBrokerAccount(id);
    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error("[api/broker/accounts PATCH]", (err as Error).message);
    return NextResponse.json({ error: "Failed to activate" }, { status: 500 });
  }
}
