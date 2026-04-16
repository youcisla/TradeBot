import { NextResponse } from "next/server";
import {
  getBotStatus,
  getAgentEvents,
  getClosedTrades,
  getKpis,
} from "@/lib/db";
import { swrCache } from "@/lib/api-cache";

export const dynamic = "force-dynamic";

// ── Session metadata ────────────────────────────────────────────────────────

const SESSION_META: Record<string, { label: string; next: string; minutes: number }> = {
  asian:    { label: "Asian Session",    next: "London",    minutes: 60  },
  london:   { label: "London Session",   next: "Overlap",   minutes: 300 },
  overlap:  { label: "London + NY",      next: "New York",  minutes: 240 },
  newyork:  { label: "New York Session", next: "Asian",    minutes: 180 },
};

function minutes_to_next_session(session: string): { next: string; in_minutes: number } {
  const meta = SESSION_META[session] ?? { label: session, next: "—", minutes: 0 };
  // Approximate minutes until next session (refreshed each call — 30s polling)
  const offset = new Date().getTimezoneOffset();
  const now = new Date();
  const utc_hour = (now.getUTCHours() * 60 + now.getUTCMinutes() - offset) % 1440;
  return { next: meta.next, in_minutes: Math.max(1, meta.minutes - (utc_hour % 60)) };
}

// ── AI insight generation ──────────────────────────────────────────────────

function generate_insight(
  session: string,
  spreadCond: string,
  regime: string,
  vix: number,
  dailyPnl: number,
  equityDrawdownPct: number,
  errorCount: number,
  warnCount: number,
): string {
  const parts: string[] = [];

  if (errorCount > 0) {
    parts.push(`${errorCount} error${errorCount > 1 ? "s" : ""} detected — review agent feed.`);
  }
  if (warnCount > 3) {
    parts.push(`${warnCount} warnings active.`);
  }

  if (spreadCond === "extreme") {
    parts.push("Spread is extreme — new entries rejected.");
  } else if (spreadCond === "high") {
    parts.push("Spread is elevated — caution advised.");
  } else if (spreadCond === "low" && session === "overlap") {
    parts.push("Optimal conditions — tight spreads during high-volume overlap.");
  }

  if (regime === "high_volume" && spreadCond !== "high" && spreadCond !== "extreme") {
    parts.push("High-volume session active — momentum strategies favored.");
  } else if (regime === "volatile") {
    parts.push("Volatile market — consider reducing position size.");
  } else if (regime === "quiet" && session === "asian") {
    parts.push("Asian quiet session — mean-reversion strategies favored.");
  }

  if (vix > 30) {
    parts.push(`VIX elevated (${vix.toFixed(1)}) — risk-off environment.`);
  } else if (vix > 0 && vix <= 20) {
    parts.push(`VIX low (${vix.toFixed(1)}) — complacency signal.`);
  }

  if (equityDrawdownPct > 0.15) {
    parts.push("Equity drawdown > 15% — sizing reduced automatically.");
  }

  if (dailyPnl > 0) {
    parts.push(`+$${dailyPnl.toFixed(2)} today — ${session} session performing well.`);
  } else if (dailyPnl < -50) {
    parts.push(`$${Math.abs(dailyPnl).toFixed(2)} in the red today — stay disciplined.`);
  }

  if (parts.length === 0) {
    const sess = SESSION_META[session];
    return `${sess?.label ?? session} — all systems nominal.`;
  }

  return parts.join(" ");
}

// ── Handler ─────────────────────────────────────────────────────────────

export async function GET() {
  try {
    const [status, events, closedTrades, kpis] = await Promise.all([
      swrCache("bot_status", 3_000, getBotStatus),
      swrCache("agent_events_200", 5_000, () => getAgentEvents(200)),
      swrCache("closed_trades", 15_000, () => getClosedTrades()),
      swrCache("kpis", 15_000, getKpis),
    ]);

    const spreadCond = (status as unknown as Record<string, unknown>)?.spread_condition as string ?? "unknown";
    const session    = (status as unknown as Record<string, unknown>)?.current_session as string ?? "unknown";
    const regime     = (status as unknown as Record<string, unknown>)?.market_regime as string ?? "normal";
    const spreadPips = (status as unknown as Record<string, unknown>)?.spread_pips as number ?? 0;
    const vix        = (status as unknown as Record<string, unknown>)?.vix as number ?? 0;
    const eqDdPct    = (status as unknown as Record<string, unknown>)?.equity_drawdown_pct as number ?? 0;

    const sessionMeta = SESSION_META[session] ?? { label: session, next: "—", minutes: 0 };
    const { next: nextSession, in_minutes: nextSessionIn } = minutes_to_next_session(session);

    // Recent errors/warns from critical agents
    const criticalAgents = new Set(["risk", "execution", "council", "trade_manager", "learning"]);
    const recentAlerts = events
      .filter((e) => criticalAgents.has(e.agent) && (e.level === "error" || e.level === "warn" || e.level === "critical"))
      .slice(0, 8);

    const errorCount = recentAlerts.filter((e) => e.level === "error" || e.level === "critical").length;
    const warnCount  = recentAlerts.filter((e) => e.level === "warn").length;

    // Performance from closed trades today
    const today = new Date().toISOString().slice(0, 10);
    function closeTimeIso(t: { close_time: unknown }): string {
      const v = t.close_time;
      if (typeof v === "string") return v;
      if (v instanceof Date) return v.toISOString();
      return "";
    }
    const todayTrades = closedTrades.filter(
      (t) => closeTimeIso(t).startsWith(today)
    );
    const todayPnl = todayTrades.reduce((s, t) => s + (Number(t.pnl) || 0), 0);
    const wins = todayTrades.filter((t) => Number(t.pnl) > 0);
    const winRate = todayTrades.length > 0
      ? (wins.length / todayTrades.length) * 100 : 0;

    const intelligence = generate_insight(
      session, spreadCond, regime, vix,
      todayPnl, eqDdPct, errorCount, warnCount,
    );

    return NextResponse.json({
      // Session
      session,
      sessionLabel: sessionMeta.label,
      nextSession,
      nextSessionIn,
      // Spread
      spreadCondition: spreadCond,
      spreadPips,
      // Regime
      marketRegime: regime,
      // Risk
      vix,
      dailyLossPct: (status as unknown as Record<string, unknown>)?.daily_loss_pct as number ?? 0,
      equityDrawdownPct: eqDdPct,
      // Performance
      todayPnl,
      winRate,
      tradesToday: todayTrades.length,
      openTrades: (status as unknown as Record<string, unknown>)?.open_trades ?? 0,
      totalTrades: Number(kpis.total_trades) || 0,
      // Alerts
      recentAlerts: recentAlerts.map((e) => ({
        id: e.id,
        agent: e.agent,
        level: e.level,
        message: e.message,
        created_at: e.created_at,
      })),
      alertCount: errorCount + warnCount,
      // AI summary
      intelligence,
    });
  } catch (err) {
    console.error("[api/intelligence]", err);
    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: "Failed to load intelligence data" } },
      { status: 500 },
    );
  }
}
