"""WebSocket notifier — sends PostgreSQL NOTIFY events to ws-server.js.

The ws-server.js (Node.js) listens on channel 'dashboard_events' and broadcasts
to all connected dashboard clients in real-time.

Usage (in any agent or at key pipeline events):
    from utils.websocket_notifier import notify

    notify("new_signal", {
        "agent": "strategy_agent",
        "level": "info",
        "message": "BUY signal on EURUSD confidence=0.82",
        "data": {"symbol": "EURUSD", "direction": "BUY", "confidence": 0.82},
    })

Environment:
    DATABASE_URL  – PostgreSQL connection string (same as bot)
    WS_NOTIFY_ENABLED – set to "false" to disable notifications
"""

from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any

from config import settings

logger = logging.getLogger(__name__)

_NOTIFY_ENABLED = os.getenv("WS_NOTIFY_ENABLED", "true").lower() != "false"

# Thread-local connection pool for NOTIFY (lightweight, fire-and-forget)
_notify_lock = threading.Lock()
_notify_conn: "psycopg2.connection | None" = None


def _get_notify_conn() -> "psycopg2.connection | None":
    """Get or create a dedicated connection for NOTIFY (no pool needed)."""
    global _notify_conn
    if not _NOTIFY_ENABLED:
        return None
    if _notify_conn is not None:
        try:
            _notify_conn.isolation_level  # check alive
            return _notify_conn
        except Exception:
            _notify_conn = None

    try:
        import psycopg2
        dsn = getattr(settings, "DATABASE_URL", "") or os.getenv("DATABASE_URL", "")
        if not dsn:
            return None
        _notify_conn = psycopg2.connect(dsn, connection_factory=psycopg2.connection)
        _notify_conn.autocommit = True  # NOTIFY requires autocommit
        logger.info("WebSocket notifier connected to PostgreSQL")
        return _notify_conn
    except Exception as exc:
        logger.warning("WebSocket notifier: could not connect — %s", exc)
        return None


def notify(event_type: str, payload: dict[str, Any]) -> None:
    """Fire a PostgreSQL NOTIFY to channel 'dashboard_events'.

    This is non-blocking — failures are logged but never raise.
    """
    if not _NOTIFY_ENABLED:
        return

    def _send() -> None:
        conn = _get_notify_conn()
        if conn is None:
            return
        try:
            # Include a type tag so ws-server.js can route the event
            envelope = json.dumps({"event_type": event_type, **payload})
            with _notify_lock:
                # Each NOTIFY call reuses the same connection with autocommit
                cursor = conn.cursor()
                cursor.execute(f"SELECT pg_notify('dashboard_events', %s)", (envelope,))
                cursor.close()
        except Exception as exc:
            logger.debug("pg_notify failed (non-fatal): %s", exc)

    # Spawn in background thread so we never block the trading loop
    t = threading.Thread(target=_send, daemon=True)
    t.start()


# ── Convenience helpers ───────────────────────────────────────────────────────

def notify_signal(signal_intent: str, strategy: str, symbol: str,
                   direction: str, confidence: float, reason: str) -> None:
    """Called when a new signal is published (DISCUSSION / STRATEGY / EXECUTION)."""
    notify("new_signal", {
        "agent":     strategy,
        "level":     "info",
        "message":   f"[{signal_intent}] {direction} {symbol} @ {confidence:.0%} confidence",
        "data": {
            "signal_intent": signal_intent,
            "strategy":      strategy,
            "symbol":        symbol,
            "direction":     direction,
            "confidence":    confidence,
            "reason":        reason,
        },
    })


def notify_trade_opened(trade_id: str, symbol: str, direction: str,
                        lot_size: float, entry_price: float) -> None:
    notify("trade_opened", {
        "agent":   "execution_agent",
        "level":   "info",
        "message": f"Trade opened {direction} {symbol} {lot_size:.2f} lots @ {entry_price}",
        "data":    {"trade_id": trade_id, "symbol": symbol,
                    "direction": direction, "lot_size": lot_size,
                    "entry_price": entry_price},
    })


def notify_trade_closed(trade_id: str, symbol: str, pnl: float,
                         close_reason: str) -> None:
    level = "info" if pnl >= 0 else "warn"
    notify("trade_closed", {
        "agent":   "trade_manager",
        "level":   level,
        "message": f"Trade closed {symbol} pnl={pnl:.2f} ({close_reason})",
        "data":    {"trade_id": trade_id, "symbol": symbol,
                    "pnl": pnl, "close_reason": close_reason},
    })


def notify_tp_hit(trade_id: str, symbol: str, tp_level: int) -> None:
    notify("trade_tp_hit", {
        "agent":   "trade_manager",
        "level":   "info",
        "message": f"TP{tp_level} hit on {symbol}",
        "data":    {"trade_id": trade_id, "symbol": symbol, "tp_level": tp_level},
    })


def notify_daily_loss_limit(equity: float, daily_pnl: float) -> None:
    notify("daily_loss_limit", {
        "agent":   "risk_agent",
        "level":   "critical",
        "message": f"Daily loss limit hit — equity={equity:.2f} pnl={daily_pnl:.2f}",
        "data":    {"equity": equity, "daily_pnl": daily_pnl},
    })


def notify_bot_start(session_id: int) -> None:
    notify("bot_start", {
        "agent":   "logging_agent",
        "level":   "info",
        "message": f"Bot started (session={session_id})",
        "data":    {"session_id": session_id},
    })


def notify_bot_stop(session_id: int, exit_reason: str) -> None:
    notify("bot_stop", {
        "agent":   "logging_agent",
        "level":   "info",
        "message": f"Bot stopped (session={session_id}) reason={exit_reason}",
        "data":    {"session_id": session_id, "exit_reason": exit_reason},
    })


def notify_error(agent: str, error_message: str) -> None:
    notify("bot_error", {
        "agent":   agent,
        "level":   "error",
        "message": error_message,
        "data":    {"agent": agent},
    })
