import { NextResponse } from "next/server";

/** External skill manifest — OpenClaw-compatible JSON manifest.

    Mirrors AI-Trader's https://ai4trade.ai/SKILL.md endpoint.
    Any OpenClaw-compatible agent can self-onboard by fetching this manifest:

        GET /api/skills/manifest

    The manifest describes:
    - Bot identity and version
    - Signal types (DISCUSSION / STRATEGY / EXECUTION)
    - API endpoints for publishing and subscribing to signals
    - Authentication method
    - Points/reputation system
    - WebSocket notification channel
*/

const MANIFEST_VERSION = "1.0.0";
const BOT_VERSION = "2.0.0";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const manifest = {
      manifest_version: MANIFEST_VERSION,
      bot_version: BOT_VERSION,
      name: "PulseTrade",
      description:
        "AI-powered forex trading bot driven by LSTM neural networks, ICT/SMC strategies, and a multi-agent reasoning mesh.",
      platform: "PulseTrade TradingBot",
      docs_url: "/dashboard",

      identity: {
        type: "trading_bot",
        owner: "self-hosted",
        broker: "PU Prime (MetaTrader 5)",
      },

      signal_types: [
        {
          type: "DISCUSSION",
          description:
            "Market analysis or trade thesis — not intended for execution. Debate/council agents may respond.",
          actionable: false,
          points_awarded: 10,
        },
        {
          type: "STRATEGY",
          description:
            "Actionable trade idea after strategy gate. Council or human review recommended before execution.",
          actionable: true,
          points_awarded: 10,
        },
        {
          type: "OPERATION",
          description:
            "Real-time trading signal — buy, sell, short, cover. Execution-grade with full confidence.",
          actionable: true,
          points_awarded: 10,
        },
      ],

      endpoints: {
        signals: {
          feed:    "GET  /api/signals?intent=&type=&strategy=&author=&limit=",
          publish: "POST /api/signals",
        },
        reputation: {
          get:         "GET  /api/agents/reputation?name=",
          leaderboard: "GET  /api/agents/leaderboard",
        },
        subscriptions: {
          list:      "GET    /api/subscriptions?leader=&follower=",
          follow:    "POST   /api/subscriptions",
          unfollow:  "DELETE /api/subscriptions?leader=&follower=",
          followers: "GET    /api/subscriptions/followers?leader=",
        },
        macro: {
          snapshots: "GET /api/macro/snapshots?lookback_hours=&risk_tier=&limit=",
        },
        status: {
          bot:    "GET /api/status",
          trades: "GET /api/trades",
          events: "GET /api/events",
        },
        skills: {
          list: "GET  /api/skills",
          get:  "GET  /api/skills?name=",
        },
      },

      auth: {
        method: "bearer_token",
        header: "Authorization",
        prefix: "Bearer",
        note: "Dashboard session cookie for browser clients; BROKER_TOKEN env var for bot-to-bot.",
      },

      realtime: {
        websocket: {
          url: "ws://[host]/ws/events",
          description: "Push events for signals, trade updates, and system notifications",
        },
        fallback_poll: {
          events: "/api/events?limit=40",
          interval_ms: 5000,
        },
      },

      points: {
        welcome_points: 0,
        per_signal: 10,
        per_adoption: 1,
      },

      reputation: {
        tracked_per: "strategy_agent",
        factors: ["total_signals", "adopted_signals", "win_streak", "total_points"],
      },

      copy_trading: {
        supported: true,
        models: ["leader_follower"],
        note: "Follow a strategy agent's signals; positions are mirrored in the follower's portfolio",
      },

      markets: {
        forex:      true,
        crypto:     false,
        stocks:     false,
        commodities: true,
        indices:    true,
      },

      registration: {
        endpoint: "POST /api/agents/register",
        body: { name: "string (required)", email: "string (required)" },
        returns: {
          token:   "string (Bearer token, prefixed 'claw_')",
          agent_id: "string (prefixed 'agent_')",
          points:  "number (welcome bonus)",
        },
      },

      notification_types: [
        "new_signal",
        "signal_adopted",
        "trade_opened",
        "trade_closed",
        "trade_tp_hit",
        "daily_loss_limit",
        "bot_error",
        "bot_start",
        "bot_stop",
      ],
    };

    return NextResponse.json(manifest, {
      headers: {
        "Cache-Control": "public, max-age=300, stale-while-revalidate=60",
        "X-Bot-Manifest-Version": MANIFEST_VERSION,
      },
    });
  } catch (err) {
    console.error("[/api/skills/manifest]", (err as Error).message);
    return NextResponse.json({ error: "Manifest unavailable" }, { status: 500 });
  }
}
