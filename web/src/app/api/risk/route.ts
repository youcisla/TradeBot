import { NextResponse } from "next/server";
import { getBotStatus, getAgentEvents, getMonthlyPnl } from "@/lib/db";
import { swrCache } from "@/lib/api-cache";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const [status, events, monthlyPnl] = await Promise.all([
      swrCache("bot_status", 3_000, getBotStatus),
      swrCache("agent_events_300", 5_000, () => getAgentEvents(300)),
      swrCache("monthly_pnl", 10_000, getMonthlyPnl),
    ]);

    // Latest WFO alert event emitted by learning_agent.run_wfo_assessment()
    // Keys: { overfitting, stability, num_windows, strategy }
    const wfoEvent = events.find(
      (e) => e.agent === "learning" && e.data != null && "overfitting" in e.data
    );

    // Emergency evidence — risk agent emits events mentioning "emergency" when
    // set_emergency_caps() is called from the main loop after a WFO alert.
    const emergencyEvent = events.find(
      (e) =>
        e.agent === "risk" &&
        typeof e.message === "string" &&
        e.message.toLowerCase().includes("emergency")
    );

    const balance = status?.balance ?? 0;
    const equity = status?.equity ?? 0;
    const dailyPnl = status?.daily_pnl ?? 0;

    // Loss percentages (negative = loss, positive = gain)
    const dailyLossPct = balance > 0 ? (dailyPnl / balance) * 100 : 0;
    const monthlyLossPct = balance > 0 ? (monthlyPnl / balance) * 100 : 0;

    // Risk parameters from environment — the Python bot populates these at
    // startup via config/settings.py (env-driven). The dashboard reads them
    // here so they stay in sync without a separate config API.
    const maxRiskPerTrade = parseFloat(process.env.MAX_RISK_PER_TRADE ?? "0.01");
    const maxOpenTrades = parseInt(process.env.MAX_OPEN_TRADES ?? "5", 10);
    const positionSizeMode = process.env.POSITION_SIZE_MODE ?? "equity_pct";
    const kellyHalf = (process.env.KELLY_HALF ?? "true").toLowerCase() === "true";
    const kellyMinTrades = parseInt(process.env.KELLY_MIN_TRADES ?? "30", 10);
    const kellyLookbackDays = parseInt(process.env.KELLY_LOOKBACK_DAYS ?? "90", 10);
    const maxMonthlyLoss = parseFloat(process.env.MAX_MONTHLY_LOSS ?? "0.08");
    const maxDailyLoss = parseFloat(process.env.MAX_DAILY_LOSS ?? "0.03");
    const councilMinConf = parseFloat(process.env.COUNCIL_MIN_CONFIDENCE ?? "0.55");

    // Guard pipeline status — written by Python HeartbeatManager each loop
    const rawGuards = (
      status != null && "guard_status" in status
        ? (status as unknown as { guard_status?: unknown }).guard_status
        : undefined
    ) as
      | Array<{ name: string; status: string; threshold: string; current: string }>
      | undefined;
    const guards = (rawGuards ?? []).map((g) => ({
      name: g.name,
      status:
        g.status === "pass" || g.status === "warn" || g.status === "fail"
          ? g.status
          : "pass",
      threshold: g.threshold ?? "—",
      current: g.current ?? "—",
    }));

    return NextResponse.json({
      // ── Equity snapshot
      equity,
      balance,
      daily_pnl: dailyPnl,
      monthly_pnl: monthlyPnl,
      daily_loss_pct: dailyLossPct,
      monthly_loss_pct: monthlyLossPct,

      // ── Configured limits
      max_daily_loss_pct: maxDailyLoss * 100,
      max_monthly_loss_pct: maxMonthlyLoss * 100,
      max_open_trades: maxOpenTrades,

      // ── Bot state
      open_trades: status?.open_trades ?? 0,
      bot_state: status?.state ?? "offline",

      // ── Position sizing params
      position_size_mode: positionSizeMode,
      max_risk_per_trade: maxRiskPerTrade,
      kelly_half: kellyHalf,
      kelly_min_trades: kellyMinTrades,
      kelly_lookback_days: kellyLookbackDays,
      council_min_confidence: councilMinConf,

      // ── Guard pipeline status
      guards,

      // ── WFO assessment (last alert event from learning agent)
      wfo_overfitting: (wfoEvent?.data?.overfitting as number) ?? null,
      wfo_stability: (wfoEvent?.data?.stability as number) ?? null,
      wfo_num_windows: (wfoEvent?.data?.num_windows as number) ?? null,
      wfo_last_run: wfoEvent?.created_at ?? null,
      wfo_strategy: (wfoEvent?.data?.strategy as string) ?? null,

      // ── Emergency caps
      emergency_caps_active: emergencyEvent != null,
      emergency_event_at: emergencyEvent?.created_at ?? null,
    });
  } catch (err) {
    console.error("[api/risk] error:", err);
    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: "Failed to load risk data" } },
      { status: 500 }
    );
  }
}
