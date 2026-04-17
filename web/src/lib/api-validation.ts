import { z } from "zod";
import { apiError } from "@/lib/api-errors";

// ── Rate limiting (in-memory, 1 req/min per IP) ──────────────────────────────

const _rateLimitStore = new Map<string, number>();

export function rateLimit(ip: string): boolean {
  const now = Date.now();
  const last = _rateLimitStore.get(ip);
  if (last !== undefined && now - last < 60_000) {
    return false;
  }
  _rateLimitStore.set(ip, now);
  return true;
}

// ── Signal schemas ───────────────────────────────────────────────────────

export const SignalTypeSchema = z.enum(["DISCUSSION", "STRATEGY", "OPERATION"]);
export const SignalIntentSchema = z.enum(["DISCUSSION", "STRATEGY", "EXECUTION"]);
export const SignalSchema = z.object({
  signal_intent: SignalIntentSchema,
  signal_type: SignalTypeSchema,
  strategy: z.string().min(1),
  symbol: z.string().optional(),
  direction: z.enum(["BUY", "SELL"]).optional(),
  entry_price: z.number().optional(),
  confidence: z.number().optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
});

// ── Broker account schema ─────────────────────────────────────────────────

export const BrokerAccountSchema = z.object({
  name: z.string().min(1).max(100),
  account_number: z.string().min(1).max(50),
  password: z.string().min(1),
  server: z.string().min(1).max(100),
  is_demo: z.boolean().default(false),
});

// ── Subscription schema ───────────────────────────────────────────────────

export const SubscriptionSchema = z.object({
  follower_id: z.string().min(1),
  leader_id: z.string().min(1),
  leader_strategy: z.string().optional(),
});

// ── Backtest run schema ──────────────────────────────────────────────────

export const BacktestRunSchema = z.object({
  symbol: z.string().min(1),
  strategy: z.string().optional(),
});
