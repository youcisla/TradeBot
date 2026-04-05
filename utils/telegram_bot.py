"""Telegram bot for alerts and remote commands.

Runs a background polling thread that listens for:
  /kill    – close all positions + stop the main loop
  /status  – report open positions and equity
  /pause   – stop opening new trades
  /resume  – resume normal operation

Outbound helpers:
  send_message(text) – push a message to the configured chat
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Callable
from urllib.request import Request, urlopen
from urllib.error import URLError
import json
from collections import deque

from config import settings

logger = logging.getLogger(__name__)

# ── Callbacks set by main.py ────────────────────────────────────────────
_kill_callback: Callable[[], None] | None = None
_status_callback: Callable[[], str] | None = None
_graph_callback: Callable[[], tuple[str, bytes] | None] | None = None
_pause_flag = threading.Event()  # set = paused
_kill_flag = threading.Event()   # set = kill requested (processed by main thread)
_stop_polling = threading.Event()
_send_lock = threading.Lock()
_last_sent_ts_by_key: dict[str, float] = {}
_recent_sent_ts: deque[float] = deque()
_suppressed_count: int = 0


def is_paused() -> bool:
    return _pause_flag.is_set()


def pause() -> None:
    _pause_flag.set()


def resume() -> None:
    _pause_flag.clear()


def is_kill_requested() -> bool:
    return _kill_flag.is_set()


def request_kill() -> None:
    _kill_flag.set()


def register_callbacks(
    kill_cb: Callable[[], None] | None = None,
    status_cb: Callable[[], str] | None = None,
    graph_cb: Callable[[], tuple[str, bytes] | None] | None = None,
) -> None:
    global _kill_callback, _status_callback, _graph_callback
    _kill_callback = kill_cb  # kept for backward compat; kill now uses _kill_flag
    _status_callback = status_cb
    _graph_callback = graph_cb


# ── Outbound ─────────────────────────────────────────────────────────────

def _should_suppress_message(message_key: str, *, priority: str, force: bool) -> bool:
    global _suppressed_count
    if force:
        return False
    if not settings.TELEGRAM_NOISE_FILTER_ENABLED:
        return False
    if priority in ("high", "critical"):
        return False

    now = time.monotonic()
    with _send_lock:
        while _recent_sent_ts and now - _recent_sent_ts[0] > 60.0:
            _recent_sent_ts.popleft()

        last_sent = _last_sent_ts_by_key.get(message_key, 0.0)
        if now - last_sent < settings.TELEGRAM_DEDUPE_WINDOW_SECONDS:
            _suppressed_count += 1
            return True

        if len(_recent_sent_ts) >= settings.TELEGRAM_RATE_LIMIT_PER_MINUTE:
            _suppressed_count += 1
            return True

        _last_sent_ts_by_key[message_key] = now
        _recent_sent_ts.append(now)
        return False


def send_message(
    text: str,
    *,
    priority: str = "normal",
    dedupe_key: str | None = None,
    force: bool = False,
) -> bool:
    """Send a Telegram message.

    Returns True when sent, False when suppressed or unavailable.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        logger.debug("Telegram not configured — skipping message")
        return False

    key = dedupe_key or text.strip()
    if _should_suppress_message(key, priority=priority, force=force):
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text[:4096]}).encode()
    req = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=10):
            pass
        _maybe_emit_suppression_notice()
        return True
    except Exception:
        logger.warning("Failed to send Telegram message", exc_info=True)
        return False


def send_photo(
    image_bytes: bytes,
    caption: str = "",
    *,
    filename: str = "chart.png",
    priority: str = "normal",
    dedupe_key: str | None = None,
    force: bool = False,
) -> bool:
    """Send an image to Telegram using multipart/form-data."""
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        logger.debug("Telegram not configured — skipping photo")
        return False

    key = dedupe_key or f"photo:{caption[:120]}"
    if _should_suppress_message(key, priority=priority, force=force):
        return False

    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = b""
    body += f"--{boundary}\r\n".encode()
    body += b'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
    body += f"{chat_id}\r\n".encode()

    if caption:
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="caption"\r\n\r\n'
        body += caption[:1024].encode("utf-8", errors="ignore") + b"\r\n"

    body += f"--{boundary}\r\n".encode()
    body += (
        f'Content-Disposition: form-data; name="photo"; filename="{filename}"\r\n'.encode()
    )
    body += b"Content-Type: image/png\r\n\r\n"
    body += image_bytes + b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    url = f"https://api.telegram.org/bot{token}/sendPhoto"
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    req = Request(url, data=body, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=20):
            pass
        _maybe_emit_suppression_notice()
        return True
    except Exception:
        logger.warning("Failed to send Telegram photo", exc_info=True)
        return False


def _maybe_emit_suppression_notice() -> None:
    global _suppressed_count
    if _suppressed_count <= 0:
        return
    threshold = max(1, settings.TELEGRAM_SUPPRESSION_REPORT_EVERY)
    if _suppressed_count < threshold:
        return

    suppressed_now = _suppressed_count
    _suppressed_count = 0
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        return

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps(
            {
                "chat_id": chat_id,
                "text": (
                    f"🔕 Noise filter active: suppressed {suppressed_now} repetitive/low-priority alerts."
                ),
            }
        ).encode()
        req = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(req, timeout=10):
            pass
    except Exception:
        logger.debug("Failed to send suppression notice", exc_info=True)


# ── Inbound polling ─────────────────────────────────────────────────────

def _poll_updates() -> None:
    """Long-poll the Telegram getUpdates endpoint in a background thread."""
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        logger.info("Telegram polling skipped — not configured")
        return

    base = f"https://api.telegram.org/bot{token}"
    offset = 0
    logger.info("Telegram polling thread started")

    while not _stop_polling.is_set():
        try:
            url = f"{base}/getUpdates?offset={offset}&timeout=10"
            req = Request(url, method="GET")
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "").strip()
                from_chat = str(msg.get("chat", {}).get("id", ""))
                if from_chat != chat_id:
                    continue
                _handle_command(text)
        except URLError:
            time.sleep(5)
        except Exception:
            logger.warning("Telegram poll error", exc_info=True)
            time.sleep(5)


def _handle_command(text: str) -> None:
    cmd = text.lower().split()[0] if text else ""
    if cmd == "/kill":
        send_message(
            "🛑 KILL received — will close all positions and stop bot…",
            priority="critical",
            force=True,
        )
        _pause_flag.set()   # immediately block new trades
        _kill_flag.set()    # main thread will execute close_all + shutdown
    elif cmd == "/status":
        if _status_callback:
            report = _status_callback()
            send_message(report, priority="high", force=True)
        else:
            send_message("Status callback not registered.", priority="high", force=True)
    elif cmd == "/graph":
        if _graph_callback:
            result = _graph_callback()
            if result is None:
                send_message("📉 No closed-trade data available for chart yet.", priority="high", force=True)
            else:
                caption, image_bytes = result
                sent = send_photo(
                    image_bytes,
                    caption,
                    filename="performance.png",
                    priority="high",
                    dedupe_key="command:graph",
                    force=True,
                )
                if not sent:
                    send_message("⚠️ Could not send chart image right now.", priority="high", force=True)
        else:
            send_message("Graph callback not registered.", priority="high", force=True)
    elif cmd == "/pause":
        _pause_flag.set()
        send_message("⏸️ Bot PAUSED — no new trades will be opened.", priority="high", force=True)
        logger.info("Bot paused via Telegram")
    elif cmd == "/resume":
        _pause_flag.clear()
        send_message("▶️ Bot RESUMED — normal operation.", priority="high", force=True)
        logger.info("Bot resumed via Telegram")


def start_polling() -> threading.Thread:
    """Start the background polling thread.  Returns the thread handle."""
    t = threading.Thread(target=_poll_updates, daemon=True, name="telegram-poll")
    t.start()
    return t


def stop_polling() -> None:
    _stop_polling.set()
