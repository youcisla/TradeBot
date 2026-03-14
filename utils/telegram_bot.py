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
from typing import Callable
from urllib.parse import quote as urlquote
from urllib.request import Request, urlopen
from urllib.error import URLError
import json

from config import settings

logger = logging.getLogger(__name__)

# ── Callbacks set by main.py ────────────────────────────────────────────
_kill_callback: Callable[[], None] | None = None
_status_callback: Callable[[], str] | None = None
_pause_flag = threading.Event()  # set = paused
_kill_flag = threading.Event()   # set = kill requested (processed by main thread)
_stop_polling = threading.Event()


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
) -> None:
    global _kill_callback, _status_callback
    _kill_callback = kill_cb  # kept for backward compat; kill now uses _kill_flag
    _status_callback = status_cb


# ── Outbound ─────────────────────────────────────────────────────────────

def send_message(text: str) -> None:
    """Send a Telegram message.  Fails silently if not configured."""
    token = settings.TELEGRAM_BOT_TOKEN
    chat_id = settings.TELEGRAM_CHAT_ID
    if not token or not chat_id:
        logger.debug("Telegram not configured — skipping message")
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text[:4096]}).encode()
    req = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=10):
            pass
    except Exception:
        logger.warning("Failed to send Telegram message", exc_info=True)


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
        send_message("🛑 KILL received — will close all positions and stop bot…")
        _pause_flag.set()   # immediately block new trades
        _kill_flag.set()    # main thread will execute close_all + shutdown
    elif cmd == "/status":
        if _status_callback:
            report = _status_callback()
            send_message(report)
        else:
            send_message("Status callback not registered.")
    elif cmd == "/pause":
        _pause_flag.set()
        send_message("⏸️ Bot PAUSED — no new trades will be opened.")
        logger.info("Bot paused via Telegram")
    elif cmd == "/resume":
        _pause_flag.clear()
        send_message("▶️ Bot RESUMED — normal operation.")
        logger.info("Bot resumed via Telegram")


def start_polling() -> threading.Thread:
    """Start the background polling thread.  Returns the thread handle."""
    t = threading.Thread(target=_poll_updates, daemon=True, name="telegram-poll")
    t.start()
    return t


def stop_polling() -> None:
    _stop_polling.set()
