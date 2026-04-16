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

_PRIORITY_MARKER = {
    "critical": "🔴",
    "high": "🟠",
    "normal": "🔵",
    "low": "⚪",
}

_HELP_TEXT = (
    "🤖 Command Center\n"
    "┈┈┈┈┈┈┈┈┈┈┈┈\n"
    "• /status — account + bot status\n"
    "• /graph — performance chart\n"
    "• /pause — block new entries\n"
    "• /resume — resume entries\n"
    "• /kill — close all + shutdown\n"
    "• /help — show this command list"
)


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


def _semantic_bullet(line: str) -> str:
    text = line.lower()
    if any(token in text for token in ("error", "failed", "reject", "sl hit", "halted")):
        return "❌"
    if any(token in text for token in ("tp4", "runner")):
        return "🚀"
    if any(token in text for token in ("tp3", "target 3")):
        return "🎯"
    if any(token in text for token in ("tp2", "tp1", "breakeven", "trailing")):
        return "✅"
    if any(token in text for token in ("paused", "resume", "kill", "shutdown")):
        return "🛡️"
    if any(token in text for token in ("balance", "equity", "pnl", "win rate", "trades")):
        return "📊"
    if any(token in text for token in ("spread", "risk", "drawdown", "confidence")):
        return "⚠️"
    return "•"


def _split_line_chunks(line: str) -> list[str]:
    if " | " not in line:
        return [line]
    return [chunk.strip() for chunk in line.split(" | ") if chunk.strip()]


def _normalize_text(text: str) -> list[str]:
    clean = text.replace("\r\n", "\n").replace("**", "").strip()
    normalized: list[str] = []
    for raw_line in clean.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        normalized.extend(_split_line_chunks(line))
    return normalized


def _style_telegram_text(text: str, priority: str) -> str:
    lines = _normalize_text(text)
    if not lines:
        return text

    # Convert one-liners with a title/value shape into a compact 2-line card.
    if len(lines) == 1 and ": " in lines[0]:
        head, tail = lines[0].split(": ", maxsplit=1)
        if head and tail:
            lines = [head, tail]

    marker = _PRIORITY_MARKER.get(priority, _PRIORITY_MARKER["normal"])
    if len(lines) == 1:
        return f"{marker} {lines[0]}"

    card_lines = [f"{marker} {lines[0]}", "┈┈┈┈┈┈┈┈┈┈┈┈"]
    for line in lines[1:]:
        bullet = _semantic_bullet(line)
        card_lines.append(f"{bullet} {line}")
    return "\n".join(card_lines)


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
        if priority == "critical":
            # Telegram alerts must never be silently dropped for critical priority —
            # escalate to the console so operators see mismatches immediately.
            logger.critical("[TELEGRAM UNAVAILABLE] %s", text)
        else:
            logger.debug("Telegram not configured — skipping message")
        return False

    key = dedupe_key or text.strip()
    if _should_suppress_message(key, priority=priority, force=force):
        return False

    styled_text = _style_telegram_text(text, priority)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": styled_text[:4096]}).encode()
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

    styled_caption = _style_telegram_text(caption, priority) if caption else ""

    boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
    body = b""
    body += f"--{boundary}\r\n".encode()
    body += b'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
    body += f"{chat_id}\r\n".encode()

    if styled_caption:
        body += f"--{boundary}\r\n".encode()
        body += b'Content-Disposition: form-data; name="caption"\r\n\r\n'
        body += styled_caption[:1024].encode("utf-8", errors="ignore") + b"\r\n"

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
                    "🔕 Noise filter summary\n"
                    "┈┈┈┈┈┈┈┈┈┈┈┈\n"
                    f"📦 Suppressed alerts: {suppressed_now}\n"
                    "✅ Repetitive low-priority spam was auto-muted."
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
                from_user_id = int(msg.get("from", {}).get("id", 0) or 0)
                from_username = str(msg.get("from", {}).get("username", "") or "")
                _handle_command(
                    text,
                    from_user_id=from_user_id,
                    from_username=from_username,
                )
        except URLError:
            time.sleep(5)
        except Exception:
            logger.warning("Telegram poll error", exc_info=True)
            time.sleep(5)


def _is_authorized_user(from_user_id: int, from_username: str) -> bool:
    allowed_user_ids = settings.TELEGRAM_ALLOWED_USER_IDS
    allowed_usernames = settings.TELEGRAM_ALLOWED_USERNAMES

    # If no allowlists are configured, keep current behavior (chat-id only).
    if not allowed_user_ids and not allowed_usernames:
        return True

    if allowed_user_ids and from_user_id in allowed_user_ids:
        return True

    if allowed_usernames and from_username:
        username = from_username.strip().lstrip("@").lower()
        if username in allowed_usernames:
            return True

    return False


def _handle_command(
    text: str,
    *,
    from_user_id: int = 0,
    from_username: str = "",
) -> None:
    cmd = text.lower().split()[0] if text else ""
    if not cmd:
        return

    if not _is_authorized_user(from_user_id, from_username):
        logger.warning(
            "Blocked unauthorized Telegram command '%s' from user_id=%s username='%s'",
            cmd,
            from_user_id,
            from_username,
        )
        return

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
    elif cmd in ("/help", "/start"):
        send_message(_HELP_TEXT, priority="high", force=True)


def start_polling() -> threading.Thread:
    """Start the background polling thread.  Returns the thread handle."""
    t = threading.Thread(target=_poll_updates, daemon=True, name="telegram-poll")
    t.start()
    return t


def stop_polling() -> None:
    _stop_polling.set()
