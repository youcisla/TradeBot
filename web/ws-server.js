/**
 * ws-server.js — Standalone WebSocket server for real-time dashboard events.
 *
 * Runs alongside Next.js (e.g. on port 3001). Clients connect via:
 *   ws://localhost:3001/ws/events
 *
 * Receives PostgreSQL NOTIFY events from the bot (see bot/utils/websocket_server.py)
 * and broadcasts them to all connected dashboard clients.
 *
 * Fallback: when NOTIFY is unavailable (e.g. cloud DB), polls agent_events
 * table every 2 seconds for new rows since last poll.
 *
 * Usage:
 *   node ws-server.js
 *
 * Environment:
 *   DATABASE_URL       – PostgreSQL connection string
 *   WS_PORT           – WebSocket server port (default 3001)
 *   POLL_INTERVAL_MS  – Fallback poll interval in ms (default 2000)
 */

"use strict";

const { WebSocketServer, WebSocket } = require("ws");
const { Pool } = require("pg");

// ── Config ────────────────────────────────────────────────────────────────────
const WS_PORT = Number(process.env.WS_PORT || "3001");
const POLL_INTERVAL_MS = Number(process.env.POLL_INTERVAL_MS || "2000");
const DATABASE_URL = process.env.DATABASE_URL || "";

// ── DB pool ──────────────────────────────────────────────────────────────────
let pgPool;
if (DATABASE_URL) {
  pgPool = new Pool({
    connectionString: DATABASE_URL.replace(/[?&]sslmode=[^&]*/g, ""),
    ssl: process.env.NODE_ENV === "production"
      ? true
      : { rejectUnauthorized: false },
    max: 5,
    idleTimeoutMillis: 20_000,
    connectionTimeoutMillis: 10_000,
  });
  pgPool.on("error", (err) => console.error("[pg-pool]", err.message));
}

// ── WebSocket server ─────────────────────────────────────────────────────────
const wss = new WebSocketServer({ port: WS_PORT });
console.log(`[ws-server] WebSocket server listening on ws://0.0.0.0:${WS_PORT}`);

// Track connected clients
const clients = new Set();

wss.on("connection", (ws, req) => {
  const clientId = `${req.socket.remoteAddress}:${req.socket.remotePort}`;
  clients.add(ws);
  console.log(`[ws-server] Client connected: ${clientId} (total: ${clients.size})`);

  // Send a welcome ping so the client knows the connection is alive
  ws.send(JSON.stringify({ type: "connected", clientId }));

  ws.on("close", () => {
    clients.delete(ws);
    console.log(`[ws-server] Client disconnected: ${clientId} (total: ${clients.size})`);
  });

  ws.on("error", (err) => {
    console.error(`[ws-server] Client error [${clientId}]:`, err.message);
    clients.delete(ws);
  });
});

// ── Broadcast helper ─────────────────────────────────────────────────────────
function broadcast(data) {
  const payload = JSON.stringify(data);
  for (const client of clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(payload);
    }
  }
}

// ── Method 1: PostgreSQL LISTEN / NOTIFY ────────────────────────────────────
/**
 * The bot calls `SELECT pg_notify('dashboard_events', json_payload)` to push
 * events directly. This avoids polling.
 */
if (pgPool) {
  let notifyConn;
  (async () => {
    try {
      notifyConn = await pgPool.connect();
      await notifyConn.query("LISTEN dashboard_events");
      console.log("[ws-server] Listening on PostgreSQL channel 'dashboard_events'");
      notifyConn.on("notification", (msg) => {
        try {
          const payload = JSON.parse(msg.payload);
          broadcast({ type: "pg_notify", ...payload });
        } catch {
          broadcast({ type: "pg_notify", raw: msg.payload });
        }
      });
    } catch (err) {
      console.warn("[ws-server] LISTEN unavailable, falling back to polling:", err.message);
      notifyConn?.release();
      startPolling();
    }
  })();
}

// ── Method 2: Polling fallback ───────────────────────────────────────────────
/**
 * Polls agent_events for new rows since last check.
 * Used when LISTEN is unavailable (cloud DBs, connection interruption).
 */

let lastEventId = 0;
let pollTimer;

function startPolling() {
  console.log(`[ws-server] Polling fallback active (interval=${POLL_INTERVAL_MS}ms)`);
  pollTimer = setInterval(pollForEvents, POLL_INTERVAL_MS);
}

if (!pgPool) {
  startPolling();
}

async function pollForEvents() {
  if (!pgPool) return;
  if (clients.size === 0) return; // skip if no clients connected

  try {
    const rows = await pgPool.query(
      `SELECT id, agent, level, message, data, created_at
       FROM agent_events
       WHERE id > $1
       ORDER BY id ASC
       LIMIT 50`,
      [lastEventId]
    );

    if (rows.rows.length > 0) {
      lastEventId = rows.rows[rows.rows.length - 1].id;
      broadcast({ type: "events", events: rows.rows });
    }
  } catch (err) {
    console.error("[ws-server] poll error:", err.message);
  }
}

// ── Graceful shutdown ────────────────────────────────────────────────────────
function shutdown() {
  console.log("[ws-server] Shutting down...");
  if (pollTimer) clearInterval(pollTimer);
  if (pgPool) pgPool.end().catch(() => {});
  wss.close(() => {
    console.log("[ws-server] WebSocket server closed");
    process.exit(0);
  });
  // Force exit after 3s
  setTimeout(() => process.exit(1), 3000);
}

process.on("SIGINT",  shutdown);
process.on("SIGTERM", shutdown);
