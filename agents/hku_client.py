"""HKU Marketplace API client.

Wraps the HKU AI-Trader agent protocol:
  - Agent registration (one-time, stored in bot_memory)
  - Fetching external signals from the marketplace feed
  - Publishing our signals (DISCUSSION / STRATEGY intent only — never EXECUTION)
  - Reporting trade outcomes back to update agent reputation

Rate limited via token bucket (1 req/sec) and protected by a circuit breaker
(3 consecutive failures → 5-minute skip).  All operations fail open so HKU
outages never stall the trading loop.
"""

from __future__ import annotations

import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

import requests
import websocket

from config import settings
from database.db import Database

if TYPE_CHECKING:
    from models.signal import Signal

# Type alias for heartbeat/copy-trade callbacks
HKUNotificationCallback = Callable[[dict], None]

logger = logging.getLogger(__name__)

# ── Token bucket rate limiter ────────────────────────────────────────────

class TokenBucketRateLimiter:
    """Thread-safe token bucket.  One token refills per second."""

    def __init__(self, rate: float, capacity: float) -> None:
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = __import__("threading").Lock()

    def acquire(self, timeout: float = 10.0) -> bool:
        """Block until a token is available, or timeout expires."""
        deadline = time.monotonic() + timeout
        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(0.05)

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
        self._last_refill = now


# ── HKU API client ─────────────────────────────────────────────────────────

@dataclass
class HKUClient:
    """Client for the HKU AI-Trader marketplace API."""

    base_url: str
    api_key: str
    db: Database

    _token: str | None = None
    _agent_id: str | None = None
    _rate_limiter: TokenBucketRateLimiter = field(default_factory=lambda: TokenBucketRateLimiter(rate=1.0, capacity=1.0))
    _consecutive_failures: int = 0
    _circuit_open_until: float = 0.0
    # Heartbeat & WebSocket state
    _heartbeat_interval_secs: float = 30.0
    _heartbeat_thread: threading.Thread | None = None
    _heartbeat_stop: threading.Event = field(default_factory=threading.Event)
    _ws_client: websocket.WebSocketApp | None = None
    _ws_thread: threading.Thread | None = None
    _ws_reconnect_delay: float = 5.0
    _ws_max_reconnect_delay: float = 60.0
    _notification_callbacks: list[HKUNotificationCallback] = field(default_factory=list)
    _client_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        self._load_credentials()

    # ── Credentials persistence ─────────────────────────────────────────

    def _load_credentials(self) -> None:
        """Restore stored credentials from bot_memory if available."""
        try:
            block = self.db.read_memory_block("hku_agent_credentials")
            if block:
                data = json.loads(block)
                self._agent_id = data.get("agent_id")
                self._token = data.get("token")
                logger.debug("HKU credentials restored from bot_memory")
        except Exception as exc:
            logger.debug("No stored HKU credentials: %s", exc)

    def _save_credentials(self) -> None:
        """Persist agent_id + token to bot_memory."""
        try:
            data = json.dumps({"agent_id": self._agent_id, "token": self._token})
            self.db.write_memory_block("hku_agent_credentials", data)
        except Exception as exc:
            logger.warning("Failed to save HKU credentials: %s", exc)

    # ── Circuit breaker ─────────────────────────────────────────────────

    @property
    def _circuit_open(self) -> bool:
        return time.monotonic() < self._circuit_open_until

    def _trip_circuit(self) -> None:
        timeout = settings.HKU_CIRCUIT_BREAKER_TIMEOUT_SECS
        self._circuit_open_until = time.monotonic() + timeout
        self._consecutive_failures = 0
        logger.warning(
            "HKU circuit breaker OPEN — skipping API calls for %ds", timeout
        )

    def _record_success(self) -> None:
        self._consecutive_failures = 0

    def _record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= 3:
            self._trip_circuit()

    # ── Copy trading: follow / unfollow ───────────────────────────────

    def follow_agent(self, leader_id: str) -> bool:
        """Follow a leader agent to receive their signals for auto-copy.

        Returns True on success, False on failure.
        """
        if self._circuit_open:
            return False
        try:
            if not self._rate_limiter.acquire(timeout=2.0):
                return False
            self._post(
                "/api/signals/follow",
                json={"leader_id": leader_id},
            )
            self._record_success()
            logger.info("HKU following leader: %s", leader_id)
            return True
        except Exception as exc:
            self._record_failure()
            logger.warning("HKU follow_agent failed: %s", exc)
            return False

    def unfollow_agent(self, leader_id: str) -> bool:
        """Stop copying a leader agent.

        Returns True on success, False on failure.
        """
        if self._circuit_open:
            return False
        try:
            if not self._rate_limiter.acquire(timeout=2.0):
                return False
            self._post(
                "/api/signals/unfollow",
                json={"leader_id": leader_id},
            )
            self._record_success()
            logger.info("HKU unfollowed leader: %s", leader_id)
            return True
        except Exception as exc:
            self._record_failure()
            logger.warning("HKU unfollow_agent failed: %s", exc)
            return False

    def get_copied_positions(self) -> list[dict]:
        """Fetch current copied positions from HKU platform.

        Returns a list of dicts with keys: id, symbol, direction, entry_price,
        current_price, pnl, status.  Empty list on failure (fail-open).
        """
        if self._circuit_open:
            return []
        try:
            if not self._rate_limiter.acquire(timeout=2.0):
                return []
            resp = self._get("/api/positions")
            data = resp.json()
            positions = data if isinstance(data, list) else data.get("positions", [])
            self._record_success()
            return positions if isinstance(positions, list) else []
        except Exception as exc:
            self._record_failure()
            logger.warning("HKU get_copied_positions failed: %s", exc)
            return []

    # ── Registration ──────────────────────────────────────────────────

    def register_if_needed(self) -> bool:
        """Register bot as an HKU agent. Idempotent — safe to call each startup.

        Returns True if registration succeeded (or already registered), False on
        failure (in which case marketplace features are disabled for this session).
        """
        if self._agent_id and self._token:
            logger.debug("HKU agent already registered: %s", self._agent_id)
            return True

        try:
            resp = self._post(
                "/api/claw/agents/selfRegister",
                json={
                    "name": settings.BOT_PROFILE,
                    "type": "bot",
                },
            )
            data = resp.json()
            self._agent_id = data.get("agent_id") or data.get("id")
            self._token = data.get("token") or data.get("access_token")
            if not self._agent_id or not self._token:
                logger.warning("HKU registration response missing fields: %s", data)
                return False
            self._save_credentials()
            logger.info("HKU agent registered: agent_id=%s", self._agent_id)
            return True
        except Exception as exc:
            logger.warning("HKU registration failed: %s", exc)
            return False

    # ── External signal fetching ────────────────────────────────────────

    def get_external_signals(self, limit: int = 10) -> list[dict]:
        """Fetch latest signals from the HKU marketplace feed.

        Returns a list of raw HKU signal dicts.  On any error returns an empty
        list (fail-open design — bot continues without external signals).
        """
        if self._circuit_open:
            logger.debug("HKU circuit open — skipping get_external_signals")
            return []

        try:
            # Wait for rate limiter token (1 per second; our loop is 5s so this
            # should always succeed within timeout)
            if not self._rate_limiter.acquire(timeout=2.0):
                logger.warning("HKU rate limiter timeout")
                return []

            resp = self._get(
                "/api/signals/feed",
                params={"type": "realtime", "limit": min(limit, 50)},
            )
            signals = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else []
            if isinstance(signals, dict):
                signals = signals.get("signals", [signals])
            self._record_success()
            logger.debug("Fetched %d HKU signals", len(signals))
            return signals if isinstance(signals, list) else []
        except Exception as exc:
            self._record_failure()
            logger.warning("HKU get_external_signals failed (failing open): %s", exc)
            return []

    # ── Publishing signals ───────────────────────────────────────────────

    def publish_signal(self, signal: "Signal", action: str) -> bool:
        """Publish a signal to the HKU marketplace.

        action must be "discussion" or "signal" (never "execution").
        Returns True on success, False on failure.
        """
        if action not in ("discussion", "signal"):
            logger.warning("HKU publish_signal: invalid action %r", action)
            return False

        if self._circuit_open:
            logger.debug("HKU circuit open — skipping publish_signal")
            return False

        try:
            if not self._rate_limiter.acquire(timeout=2.0):
                logger.warning("HKU rate limiter timeout on publish_signal")
                return False

            payload = {
                "action": action,
                "symbol": signal.symbol,
                "direction": signal.direction,
                "price": signal.entry_price,
                "quantity": 1,
                "content": signal.reason or signal.strategy,
            }
            self._post("/api/signals/realtime", json=payload)
            self._record_success()
            logger.debug("HKU signal published: %s %s @ %.5f",
                         signal.symbol, signal.direction, signal.entry_price)
            return True
        except Exception as exc:
            self._record_failure()
            logger.warning("HKU publish_signal failed: %s", exc)
            return False

    # ── Outcome reporting ────────────────────────────────────────────────

    def report_outcome(self, hku_signal_id: str, won: bool) -> None:
        """Report a trade outcome back to HKU to update agent reputation.

        Fire-and-forget — failures are logged but never raised.
        """
        if not hku_signal_id or self._circuit_open:
            return

        try:
            if not self._rate_limiter.acquire(timeout=2.0):
                return
            self._post(
                "/api/signals/outcome",
                json={"signal_id": hku_signal_id, "outcome": "win" if won else "loss"},
            )
            self._record_success()
            logger.debug("HKU outcome reported: signal=%s won=%s", hku_signal_id, won)
        except Exception as exc:
            self._record_failure()
            logger.debug("HKU report_outcome failed: %s", exc)

    # ── HTTP helpers ─────────────────────────────────────────────────────

    def _auth_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._token}"} if self._token else {}

    def _get(self, path: str, params: dict | None = None) -> requests.Response:
        url = f"{self.base_url.rstrip('/')}{path}"
        resp = requests.get(url, params=params, timeout=10, headers=self._auth_headers())
        resp.raise_for_status()
        return resp

    def _post(self, path: str, json: dict) -> requests.Response:
        url = f"{self.base_url.rstrip('/')}{path}"
        resp = requests.post(url, json=json, timeout=10, headers=self._auth_headers())
        resp.raise_for_status()
        return resp

    # ── Heartbeat polling ───────────────────────────────────────────────

    def start_heartbeat(self) -> None:
        """Start background heartbeat thread (30s interval).

        Sends POST /api/claw/agents/heartbeat to keep agent registration alive.
        Also attempts WebSocket connection for real-time notifications.
        """
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            logger.debug("Heartbeat thread already running")
            return

        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="hku-heartbeat",
            daemon=True,
        )
        self._heartbeat_thread.start()
        logger.info("HKU heartbeat thread started (interval=%.1fs)", self._heartbeat_interval_secs)

    def stop_heartbeat(self) -> None:
        """Stop the heartbeat thread gracefully."""
        self._heartbeat_stop.set()
        if self._ws_client:
            self._ws_client.close()
        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5.0)
        logger.info("HKU heartbeat thread stopped")

    def _heartbeat_loop(self) -> None:
        """Background loop: send heartbeat + maintain WebSocket."""
        while not self._heartbeat_stop.wait(timeout=self._heartbeat_interval_secs):
            self._send_heartbeat()
            self._ensure_ws_connected()

    def _send_heartbeat(self) -> None:
        """Fire-and-forget heartbeat POST."""
        if not self._agent_id or self._circuit_open:
            return
        try:
            if not self._rate_limiter.acquire(timeout=1.0):
                return
            self._post(
                "/api/claw/agents/heartbeat",
                json={"agent_id": self._agent_id, "status": "active"},
            )
            self._record_success()
            logger.debug("HKU heartbeat sent")
        except Exception as exc:
            self._record_failure()
            logger.debug("HKU heartbeat failed: %s", exc)

    # ── WebSocket real-time notifications ──────────────────────────────

    def register_notification_callback(self, callback: HKUNotificationCallback) -> None:
        """Register a handler for HKU WebSocket notifications.

        Callback receives a dict with keys: type, data, timestamp
        Supported notification types:
          - 'signal_copied'  : another agent copied our published signal
          - 'position_update': copied position TP/SL hit or closed
          - 'points_update'  : points balance changed
          - 'new_follower'   : new agent started following us
        """
        self._notification_callbacks.append(callback)

    def _ensure_ws_connected(self) -> None:
        """Connect WebSocket if not connected or disconnected."""
        if self._ws_client is not None:
            return  # already connected
        try:
            self._ws_connect()
        except Exception as exc:
            logger.warning("HKU WebSocket connection failed: %s", exc)
            # Exponential backoff for next retry
            self._ws_reconnect_delay = min(
                self._ws_reconnect_delay * 1.5, self._ws_max_reconnect_delay
            )

    def _ws_connect(self) -> None:
        """Establish WebSocket connection to HKU notification channel."""
        ws_url = f"wss://ai4trade.ai/ws/notify/{self._client_id}"
        headers = {}
        if self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        self._ws_client = websocket.WebSocketApp(
            ws_url,
            header=headers,
            on_message=self._ws_on_message,
            on_error=self._ws_on_error,
            on_close=self._ws_on_close,
            on_open=self._ws_on_open,
        )
        self._ws_thread = threading.Thread(
            target=self._ws_client.run_forever,
            name="hku-ws",
            daemon=True,
        )
        self._ws_thread.start()
        logger.info("HKU WebSocket thread started: %s", ws_url)

    def _ws_on_open(self, ws: websocket.WebSocketApp) -> None:
        logger.info("HKU WebSocket connected")
        self._ws_reconnect_delay = 5.0  # reset backoff

    def _ws_on_message(self, ws: websocket.WebSocketApp, raw: str) -> None:
        """Dispatch incoming WebSocket notification to registered callbacks."""
        try:
            msg = json.loads(raw) if isinstance(raw, str) else json.loads(raw.decode())
            notification_type = msg.get("type", "unknown")
            data = msg.get("data", {})
            logger.debug("HKU WS notification: type=%s data=%s", notification_type, data)
            for callback in self._notification_callbacks:
                try:
                    callback({"type": notification_type, "data": data})
                except Exception as exc:
                    logger.warning("HKU notification callback error: %s", exc)
        except Exception as exc:
            logger.warning("HKU WS failed to parse message: %s", exc)

    def _ws_on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        logger.warning("HKU WebSocket error: %s", error)

    def _ws_on_close(self, ws: websocket.WebSocketApp, close_status_code: int, close_msg: str) -> None:
        logger.info("HKU WebSocket closed: code=%s msg=%s", close_status_code, close_msg)
        self._ws_client = None
        # Schedule reconnect if not stopping
        if not self._heartbeat_stop.is_set():
            threading.Timer(self._ws_reconnect_delay, self._ensure_ws_connected).start()
