"""Lightweight HTTP server that serves candle data from the broker connector.

Runs as a daemon thread inside the bot process.  The Next.js dashboard
proxies through ``/api/candles`` to this server to display live
candlestick charts.

Endpoints
---------
GET /candles?symbol=EURUSD&timeframe=H1&count=500
GET /fibonacci?symbol=EURUSD
GET /api/agent-events?limit=20
GET /trades?days=7          — open + closed trades directly from MT5
GET /health
"""

from __future__ import annotations

import json
import logging
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from typing import Any, Optional

import MetaTrader5 as mt5
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
_backtest_jobs: dict[str, dict] = {}   # jobId → {status, started_at, result, error}
_backtest_lock = threading.Lock()
# Lazily populated when first backtest endpoint is hit
_bt_mod = None  # module handle for scripts.backtest once imported

# Allowed CORS origin for browser clients (defaults to Next.js dev server).
# Override via DASHBOARD_ORIGIN env var for production Vercel deployments.
import os as _os
_CORS_ORIGIN: str = _os.getenv("DASHBOARD_ORIGIN", "http://localhost:3000")

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

        if parsed.path == "/trades":
            self._handle_trades(parsed.query)
            return

        if parsed.path != "/candles":
            self._json_response(404, {"error": "Not found"})
            return

        # ── Backtest status (GET) ──────────────────────────────────────
        if parsed.path == "/api/backtest/status":
            self._handle_backtest_status()
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
            self._json_response(500, {"error": "Internal server error"})
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
        self.send_header("Access-Control-Allow-Origin", _CORS_ORIGIN)
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
            self._json_response(500, {"error": "Internal server error"})
            return
        finally:
            _db._put_conn(conn)

        self._json_response(200, {"events": events})

    def _handle_trades(self, query: str) -> None:
        """Serve open positions + recent closed trades directly from MT5."""
        params = parse_qs(query)
        days = 7
        try:
            days = max(1, int((params.get("days") or ["7"])[0]))
        except ValueError:
            pass

        if _broker is None:
            self._json_response(503, {"error": "Broker not connected"})
            return

        try:
            # ── Open positions (raw MT5 — has `time` for open timestamp) ───
            raw_positions = mt5.positions_get() or []
            open_trades = []
            for pos in raw_positions:
                open_time_ts = getattr(pos, "time", 0) or 0
                open_trades.append({
                    "id": str(getattr(pos, "ticket", 0) or 0),
                    "symbol": str(getattr(pos, "symbol", "") or ""),
                    "direction": "BUY" if getattr(pos, "type", 1) == 0 else "SELL",
                    "entry_price": float(getattr(pos, "price_open", 0) or 0),
                    "lot_size": float(getattr(pos, "volume", 0) or 0),
                    "stop_loss": float(getattr(pos, "sl", 0) or 0),
                    "take_profit_1": float(getattr(pos, "tp", 0) or 0),
                    "pnl": float(getattr(pos, "profit", 0) or 0),
                    "status": "OPEN",
                    "open_time": datetime.fromtimestamp(open_time_ts, tz=timezone.utc).isoformat()
                        if open_time_ts else None,
                })

            # ── Closed trades from deal history ────────────────────────────
            now = datetime.now(timezone.utc)
            start = now - timedelta(days=days)
            deals = mt5.history_deals_get(start, now)
            closed_trades: dict[int, dict] = {}

            if deals:
                for deal in deals:
                    # ticket is the position_id — groups all deals for the same trade
                    ticket = int(getattr(deal, "position_id", 0) or 0)
                    if not ticket:
                        continue
                    if ticket not in closed_trades:
                        closed_trades[ticket] = {
                            "id": str(ticket),
                            "symbol": str(getattr(deal, "symbol", "") or ""),
                            "direction": "BUY" if getattr(deal, "type", 1) == 0 else "SELL",
                            "entry_price": float(getattr(deal, "price", 0) or 0),
                            "lot_size": float(getattr(deal, "volume", 0) or 0),
                            "stop_loss": 0.0,
                            "take_profit_1": 0.0,
                            "pnl": 0.0,
                            "status": "CLOSED",
                            "open_time": datetime.fromtimestamp(
                                getattr(deal, "time", 0) or 0, tz=timezone.utc
                            ).isoformat(),
                            "close_time": None,
                        }
                    # Accumulate P&L across all deals in this position
                    closed_trades[ticket]["pnl"] += float(getattr(deal, "profit", 0) or 0)
                    closed_trades[ticket]["close_time"] = datetime.fromtimestamp(
                        getattr(deal, "time", 0) or 0, tz=timezone.utc
                    ).isoformat()

            # Merge, deduplicate
            all_trades = list(open_trades)
            for t in closed_trades.values():
                if not any(str(t["id"]) == str(x["id"]) for x in all_trades):
                    all_trades.append(t)

            self._json_response(200, all_trades)
        except Exception as exc:
            logger.warning("trades handler failed: %s", exc)
            self._json_response(500, {"error": str(exc)})

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
        self.send_header("Access-Control-Allow-Origin", _CORS_ORIGIN)
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(payload)

    # ── Backtest endpoints ─────────────────────────────────────────────────

    def do_POST(self) -> None:  # noqa: N802
        """Dispatch POST requests to the appropriate handler."""
        parsed = urlparse(self.path)
        if parsed.path == "/api/backtest/run":
            self._handle_backtest_run()
            return
        self._json_response(404, {"error": "Not found"})

    def _handle_backtest_run(self) -> None:
        """Start a backtest job in a daemon thread and return a job ID."""
        global _bt_mod
        try:
            content_len = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_len).decode("utf-8") if content_len > 0 else "{}"
            params = json.loads(body)
        except (ValueError, TypeError):
            self._json_response(400, {"error": "Invalid JSON body"})
            return

        symbol = params.get("symbol", "").upper()
        strategy = params.get("strategy", "")
        if not symbol:
            self._json_response(400, {"error": "symbol is required"})
            return

        job_id = f"bt_{uuid.uuid4().hex[:12]}"
        with _backtest_lock:
            _backtest_jobs[job_id] = {
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "result": None,
                "error": None,
            }

        # Lazy-import backtest module on first request
        global _bt_mod  # noqa: used in _run_backtest_job
        if _bt_mod is None:
            _repo = Path(__file__).resolve().parents[1]
            if str(_repo) not in sys.path:
                sys.path.insert(0, str(_repo))
            try:
                import scripts.backtest as _bt
                _bt_mod = _bt
            except Exception as exc:
                logger.error("Could not import scripts.backtest: %s", exc)
                with _backtest_lock:
                    _backtest_jobs[job_id].update(status="error", error=str(exc))
                self._json_response(500, {"error": f"Could not import backtest module: {exc}"})
                return

        # Spawn daemon thread to run the backtest
        thread = threading.Thread(
            target=self._run_backtest_job,
            args=(job_id, symbol, strategy),
            daemon=True,
        )
        thread.start()
        self._json_response(202, {"jobId": job_id, "status": "running"})

    def _run_backtest_job(self, job_id: str, symbol: str, strategy: str) -> None:
        """Execute the backtest in a thread and populate the job result."""
        global _bt_mod
        try:
            bt = _bt_mod
            # Fetch 2yr H1 candles for the symbol (uses MT5)
            logger.info("[backtest %s] Fetching candles for %s", job_id, symbol)
            candles = bt._fetch_candles(symbol, candle_count=17_520)
            if not candles:
                raise ValueError(f"No candles returned for {symbol}")
            strategies = bt._build_strategies(filter_name=strategy or None, broker=_broker)
            results = bt._backtest_symbol(symbol, candles, strategies, broker=_broker)
            stats = bt._aggregate(results)
            with _backtest_lock:
                _backtest_jobs[job_id].update(status="done", result=stats)
            logger.info("[backtest %s] Done — %d results", job_id, len(stats))
        except Exception as exc:
            logger.exception("[backtest %s] Error: %s", job_id, exc)
            with _backtest_lock:
                _backtest_jobs[job_id].update(status="error", error=str(exc))

    def _handle_backtest_status(self) -> None:
        """Return the current status/result for a backtest job."""
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        job_id = (params.get("jobId") or [""])[0]
        if not job_id:
            self._json_response(400, {"error": "jobId is required"})
            return
        with _backtest_lock:
            job = _backtest_jobs.get(job_id)
        if not job:
            self._json_response(404, {"error": "Job not found"})
            return
        # Return a clean dict (strip internal keys) then prune completed jobs
        payload = {
            "jobId": job_id,
            "status": job["status"],
            "started_at": job["started_at"],
            "result": job.get("result"),
            "error": job.get("error"),
        }
        # Clean up completed/error jobs to prevent unbounded memory growth
        if job["status"] in ("done", "error"):
            del _backtest_jobs[job_id]
        self._json_response(200, payload)

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

    _server = ThreadingHTTPServer(("127.0.0.1", _port), _CandleHandler)
    _server.daemon_threads = True

    thread = threading.Thread(target=_server.serve_forever, daemon=True)
    thread.start()
    logger.info("Candle server started on http://127.0.0.1:%d", _port)


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
