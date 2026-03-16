"""Lightweight HTTP server that serves candle data from the broker connector.

Runs as a daemon thread inside the bot process.  The Next.js dashboard
proxies through ``/api/candles`` to this server to display live
candlestick charts.

Endpoints
---------
GET /candles?symbol=EURUSD&timeframe=H1&count=500
GET /fibonacci?symbol=EURUSD
GET /api/agent-events?limit=20
GET /health
"""

from __future__ import annotations

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from typing import Any, Optional

import psycopg2.extras
from database.db import Database

from broker.connector import BrokerConnector
from config import settings

logger = logging.getLogger(__name__)

# ── Globals set by start() ───────────────────────────────────────────────
_broker: BrokerConnector | None = None
_server: ThreadingHTTPServer | None = None
_ict_contexts: dict[str, Any] = {}  # symbol → latest ICTContext
_ict_lock = threading.Lock()
_db: Optional["Database"] = None  # set by start() — shared with bot

# Supported timeframes (validated against incoming requests)
_VALID_TFS = {"M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"}


class _CandleHandler(BaseHTTPRequestHandler):

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)

        if parsed.path == "/health":
            self._json_response(200, {"status": "ok"})
            return

        if parsed.path == "/api/agent-events":
            self._handle_agent_events(parsed.query)
            return

        if parsed.path == "/fibonacci":
            self._handle_fibonacci(parsed.query)
            return

        if parsed.path != "/candles":
            self._json_response(404, {"error": "Not found"})
            return

        # ── /candles ────────────────────────────────────────────────────
        params = parse_qs(parsed.query)
        symbol = (params.get("symbol") or ["EURUSD"])[0].upper()
        timeframe = (params.get("timeframe") or ["H1"])[0].upper()
        try:
            count = int((params.get("count") or ["500"])[0])
            count = max(10, min(count, 5000))  # clamp
        except ValueError:
            count = 500

        if timeframe not in _VALID_TFS:
            self._json_response(400, {"error": f"Invalid timeframe: {timeframe}"})
            return

        if _broker is None:
            self._json_response(503, {"error": "Broker not connected"})
            return

        try:
            candles = _broker.get_candles(symbol, timeframe, count)
        except Exception as exc:
            logger.warning("Candle server: failed to fetch %s %s: %s", symbol, timeframe, exc)
            self._json_response(500, {"error": str(exc)})
            return

        # Serialize to lightweight-charts format
        data = []
        for c in candles:
            ts = c.timestamp
            epoch = int(ts.timestamp()) if hasattr(ts, "timestamp") else 0
            data.append({
                "time": epoch,
                "open": round(c.open, 6),
                "high": round(c.high, 6),
                "low": round(c.low, 6),
                "close": round(c.close, 6),
                "volume": round(c.volume, 2),
            })

        self._json_response(200, data)

    def do_OPTIONS(self) -> None:  # noqa: N802
        """Handle CORS preflight."""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    # ── Route handlers ───────────────────────────────────────────────────

    def _handle_agent_events(self, query: str) -> None:
        """Serve the latest agent events as JSON."""
        params = parse_qs(query)
        try:
            limit = max(1, min(100, int((params.get("limit") or ["20"])[0])))
        except (ValueError, IndexError):
            limit = 20

        if _db is None:
            self._json_response(503, {"error": "Database not initialised"})
            return

        conn = _db._get_conn()
        try:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT agent, level, message, data, created_at
                    FROM agent_events
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
            conn.commit()
            events = [
                {
                    "agent": row["agent"],
                    "level": row["level"],
                    "msg": row["message"],
                    "data": row["data"],
                    "ts": row["created_at"].isoformat() if row["created_at"] else None,
                }
                for row in rows
            ]
        except Exception as exc:
            logger.warning("agent-events query failed: %s", exc)
            try:
                conn.rollback()
            except Exception:
                pass
            self._json_response(500, {"error": str(exc)})
            return
        finally:
            _db._put_conn(conn)

        self._json_response(200, {"events": events})

    def _handle_fibonacci(self, query: str) -> None:
        """Serve Fibonacci levels from the latest ICT context."""
        params = parse_qs(query)
        symbol = (params.get("symbol") or ["EURUSD"])[0].upper()

        with _ict_lock:
            ctx = _ict_contexts.get(symbol)
        if ctx is None or not hasattr(ctx, "fibonacci") or ctx.fibonacci is None:
            self._json_response(200, {"levels": [], "golden_zone": None})
            return

        fib = ctx.fibonacci
        levels = [
            {"ratio": lvl.ratio, "price": lvl.price, "label": lvl.label}
            for lvl in fib.levels
        ]

        data = {
            "direction": fib.direction.value,
            "anchor_low": fib.anchor_low,
            "anchor_high": fib.anchor_high,
            "levels": levels,
            "golden_zone": {
                "top": fib.golden_zone_top,
                "bottom": fib.golden_zone_bottom,
            },
            "confluence": {
                "gz_fvg": fib.gz_fvg_confluence,
                "gz_ob": fib.gz_ob_confluence,
                "gz_ce": fib.gz_ce_confluence,
                "has_target": fib.has_liquidity_target,
            },
            "retracement_depth": fib.retracement_depth,
        }

        self._json_response(200, data)

    # ── Helpers ──────────────────────────────────────────────────────────

    def _json_response(self, code: int, body: object) -> None:
        payload = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        """Suppress per-request access logs — errors are logged explicitly."""
        pass


# ── Public API ───────────────────────────────────────────────────────────

def start(broker: BrokerConnector, db: "Database", port: int | None = None) -> None:
    """Start the candle HTTP server as a daemon thread."""
    global _broker, _server, _db
    _broker = broker
    _db = db  # share the bot's existing connection pool — no second pool
    _port = port or int(getattr(settings, "CANDLE_SERVER_PORT", 5555))

    _server = ThreadingHTTPServer(("0.0.0.0", _port), _CandleHandler)
    _server.daemon_threads = True

    thread = threading.Thread(target=_server.serve_forever, daemon=True)
    thread.start()
    logger.info("Candle server started on http://0.0.0.0:%d", _port)


def stop() -> None:
    """Shutdown the candle server."""
    global _server
    if _server:
        _server.shutdown()
        _server = None
        logger.info("Candle server stopped")


def set_ict_context(symbol: str, ctx: object) -> None:
    """Store the latest ICT context for a symbol (called by main loop)."""
    with _ict_lock:
        _ict_contexts[symbol] = ctx
