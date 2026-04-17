import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import {
  getPendingReviewCommands,
  getCommandAuditSummary,
  getCommandHistory,
  insertCommand,
  reviewCommand,
} from "@/lib/db";
import { authOptions } from "@/lib/auth";

type RiskLevel = "low" | "medium" | "high";

type CommandPolicy = {
  risk: RiskLevel;
  requiresConfirmation: boolean;
  requiresApproval: boolean;
};

const COMMAND_TWO_STEP_APPROVAL_ENABLED =
  process.env.COMMAND_TWO_STEP_APPROVAL_ENABLED === "true";

const COMMAND_POLICIES: Record<string, CommandPolicy> = {
  pause: { risk: "low", requiresConfirmation: false, requiresApproval: false },
  resume: { risk: "low", requiresConfirmation: false, requiresApproval: false },
  close_trade: { risk: "medium", requiresConfirmation: true, requiresApproval: false },
  tool: { risk: "medium", requiresConfirmation: true, requiresApproval: false },
  close_all: { risk: "high", requiresConfirmation: true, requiresApproval: true },
  kill: { risk: "high", requiresConfirmation: true, requiresApproval: true },
};

function errorResponse(code: string, message: string, status: number) {
  return NextResponse.json({ error: { code, message } }, { status });
}

function toObjectPayload(payload: unknown): Record<string, unknown> {
  if (payload === undefined || payload === null) return {};
  if (typeof payload !== "object" || Array.isArray(payload)) {
    throw new Error("payload must be a JSON object");
  }
  return payload as Record<string, unknown>;
}

export async function GET(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    return errorResponse("UNAUTHORIZED", "Unauthorized", 401);
  }

  const { searchParams } = await request.nextUrl.searchParams;
  const rawLimit = Number(searchParams.get("limit") ?? 25);
  const limit = Number.isFinite(rawLimit) ? Math.min(Math.max(rawLimit, 1), 100) : 25;

  if (searchParams.get("summary") === "1") {
    const rawHours = Number(searchParams.get("hours") ?? 24);
    const hours = Number.isFinite(rawHours) ? rawHours : 24;
    const summary = await getCommandAuditSummary(hours);
    return NextResponse.json({ summary });
  }

  if (searchParams.get("history") === "1") {
    const items = await getCommandHistory(limit);
    return NextResponse.json({ items, count: items.length });
  }

  const items = await getPendingReviewCommands(limit);
  return NextResponse.json({
    items,
    count: items.length,
  });
}

export async function POST(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session?.user) {
    return errorResponse("UNAUTHORIZED", "Unauthorized", 401);
  }

  const body = await request.json().catch(() => null);
  if (!body || typeof body !== "object") {
    return errorResponse("INVALID_BODY", "Request body must be valid JSON", 400);
  }

  const action = String((body as Record<string, unknown>).action ?? "").trim().toLowerCase();
  const username = String(
    (session.user as Record<string, unknown>).username ?? session.user.name ?? "unknown"
  );

  if (action === "approve" || action === "deny") {
    // Role gate — if COMMAND_APPROVER_USERS is set, only listed users may review.
    const APPROVER_USERS = (process.env.COMMAND_APPROVER_USERS ?? "")
      .split(",")
      .map((u) => u.trim())
      .filter(Boolean);
    if (APPROVER_USERS.length > 0 && !APPROVER_USERS.includes(username)) {
      return errorResponse(
        "FORBIDDEN",
        "You are not authorized to approve or deny commands",
        403
      );
    }

    const id = Number((body as Record<string, unknown>).id);
    const reason = String((body as Record<string, unknown>).reason ?? "").trim();
    if (!Number.isFinite(id) || id <= 0) {
      return errorResponse("INVALID_ID", "A valid command id is required", 400);
    }
    if (reason.length < 5) {
      return errorResponse("INVALID_REASON", "A review reason is required", 400);
    }

    const updated = await reviewCommand(id, action, username, reason);
    if (updated === 0) {
      return errorResponse(
        "REVIEW_TARGET_NOT_FOUND",
        "Command not found or not awaiting approval",
        404
      );
    }

    return NextResponse.json({
      ok: true,
      action,
      id,
      reviewedBy: username,
    });
  }

  const command = String((body as Record<string, unknown>).command ?? "");
  const policy = COMMAND_POLICIES[command];
  if (!policy) {
    return errorResponse("UNKNOWN_COMMAND", "Unknown command", 400);
  }

  let payload: Record<string, unknown>;
  try {
    payload = toObjectPayload((body as Record<string, unknown>).payload);
  } catch {
    return errorResponse("INVALID_PAYLOAD", "payload must be a JSON object", 400);
  }

  if (command === "close_trade" && typeof payload.tradeId !== "string") {
    return errorResponse("MISSING_TRADE_ID", "close_trade requires payload.tradeId", 400);
  }

  if (policy.requiresConfirmation) {
    const confirmed = payload.confirmed === true;
    const reason = String(payload.reason ?? "").trim();
    if (!confirmed || reason.length < 8) {
      return errorResponse(
        "CONFIRMATION_REQUIRED",
        `Command ${command} requires payload.confirmed=true and a reason`,
        403
      );
    }
  }

  const traceId = `cmd_${crypto.randomUUID()}`;

  const auditedPayload: Record<string, unknown> = {
    ...payload,
    _meta: {
      requestedBy: username,
      requestedAt: new Date().toISOString(),
      traceId,
      riskLevel: policy.risk,
    },
  };

  const requiresApproval = policy.requiresApproval && COMMAND_TWO_STEP_APPROVAL_ENABLED;
  const queuedStatus = requiresApproval ? "pending_confirmation" : "pending";
  await insertCommand(command, auditedPayload, queuedStatus);
  return NextResponse.json({
    ok: true,
    command,
    status: queuedStatus,
    requiresApproval,
    executedBy: username,
    traceId,
    riskLevel: policy.risk,
  });
}
