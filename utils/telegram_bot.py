"""Telegram bot for alerts and remote commands.

Runs a background polling thread that listens for:

Read commands:
  /status        — account + bot status
  /graph         — performance chart
  /doctor        — MT5/DB/model diagnostics
  /stats         — learning repo strategy stats
  /confidence    — get/set strategy confidence
  /perf [period] — performance summary (day|week|month)
  /signals       — active signals from last scan
  /log N         — tail last N log lines
  /agents N      — last N agent events
  /macro         — latest macro snapshot

Write commands (require /confirm for destructive actions):
  /pause         — block new entries
  /resume        — resume entries
  /kill          — close all + shutdown
  /setparam KEY VALUE — hot-swap a runtime setting
  /reset_learning — wipe all learning state
  /trainlgbm     — train LGBM ensemble from closed trades
  /trainprice [SYM ...] — train per-symbol price model(s)
  /backtest SYM  — run backtest on a symbol

  /confirm       — confirm a pending write action

Natural language free-text is forwarded to the DeepSeek CLAUDE agent.

Outbound helpers:
  send_message(text) – push a message to the configured chat
  send_photo(image_bytes, caption) – push a chart image
"""

from __future__ import annotations

import io
import json
import logging
import re
import subprocess
import threading
import time
import uuid
from collections import deque
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Callable
from urllib.request import Request, urlopen
from urllib.error import URLError

from config import settings
from utils.telegram_reports import build_pnl_curve_png

logger = logging.getLogger(__name__)

# ── Global state ──────────────────────────────────────────────────────────
_kill_callback: Callable[[], None] | None = None
_status_callback: Callable[[], str] | None = None
_graph_callback: Callable[[], tuple[str, bytes] | None] | None = None
_pause_flag = threading.Event()   # set = paused
_kill_flag = threading.Event()    # set = kill requested (processed by main thread)
_stop_polling = threading.Event()
_send_lock = threading.Lock()
_last_sent_ts_by_key: dict[str, float] = {}
_recent_sent_ts: deque[float] = deque()
_suppressed_count: int = 0

# Pending write actions awaiting /confirm — keyed by (from_user_id, action_name)
_pending_actions: dict[tuple[int, str], str] = {}

# Runtime parameter overrides (volatile — not persisted)
_runtime_params: dict[str, str] = {}

# ── Priority / style helpers ────────────────────────────────────────────────

_PRIORITY_MARKER = {
    "critical": "🔴",
    "high": "🟠",
    "normal": "🔵",
    "low": "⚪",
}

_HELP_TEXT = (
    "🤖 Command Center\n"
    "┈┈┈┈┈┈┈┈┈┈┈┈\n"
    "📊 MONITORING\n"
    "  /status   — bot + account status\n"
    "  /doctor   — MT5 / DB / model diagnostics\n"
    "  /stats    — strategy learning stats\n"
    "  /confidence [strat] [val] — get/set strategy confidence\n"
    "  /perf [day|week|month] — performance summary\n"
    "  /signals  — active signals from last scan\n"
    "  /log N    — tail N log lines\n"
    "  /agents N — last N agent events\n"
    "  /macro    — latest macro snapshot\n"
    "\n🛡️ CONTROL\n"
    "  /pause    — block new entries\n"
    "  /resume   — resume entries\n"
    "  /kill     — close all + shutdown\n"
    "\n⚙️ OPERATIONS\n"
    "  /trainlgbm    — train LGBM ensemble\n"
    "  /trainprice [SYM...] — train price model(s)\n\n"
    "  /backtest SYM — run symbol backtest\n"
    "  /setparam KEY VAL — hot-swap setting\n"
    "  /reset_learning — wipe learning state (needs /confirm)\n"
    "  /confirm   — confirm a pending action\n"
    "  /graph     — performance chart\n"
    "  /hypothesis — run AI hypothesis test\n"
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
    _kill_callback = kill_cb
    _status_callback = status_cb
    _graph_callback = graph_cb


# ── Outbound helpers ────────────────────────────────────────────────────────

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


def _normalize_text(text: str) -> list[str]:
    clean = text.replace("\r\n", "\n").replace("**", "").strip()
    normalized: list[str] = []
    for raw_line in clean.split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        if " | " in line:
            for chunk in line.split(" | "):
                chunk = chunk.strip()
                if chunk:
                    normalized.append(chunk)
        else:
            normalized.append(line)
    return normalized


def _style_telegram_text(text: str, priority: str) -> str:
    lines = _normalize_text(text)
    if not lines:
        return text

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
        logger.info("Telegram photo sent successfully")
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


# ── Pending action execution ───────────────────────────────────────────────

def _execute_pending_action(from_user_id: int, send_fn: Callable[[str], None]) -> None:
    """Execute a previously confirmed write action."""
    found = False
    for (uid, action), warning in list(_pending_actions.items()):
        if uid == from_user_id:
            if action == "pause_bot":
                _pause_flag.set()
                send_fn("⏸️ Bot PAUSED — no new trades will be opened.", priority="high", force=True)
                logger.info("Bot paused via Telegram confirm")
            elif action == "resume_bot":
                _pause_flag.clear()
                send_fn("▶️ Bot RESUMED — normal operation.", priority="high", force=True)
                logger.info("Bot resumed via Telegram confirm")
            elif action == "reset_learning":
                _do_reset_learning(send_fn)
            else:
                send_fn(f"⚠️ Unknown pending action: {action}", priority="normal", force=True)
            del _pending_actions[(uid, action)]
            found = True
            break
    if not found:
        send_fn("⚠️ No pending action to confirm. Send a command first.", priority="normal", force=True)


# ── Command handlers ────────────────────────────────────────────────────────

# Type alias for a command handler callable
_Handler = Callable[[list[str], Callable[[str, ...], None]], None]


def _cmd_help(args: list[str], send: Callable[[str, ...], None]) -> None:
    send(_HELP_TEXT, priority="high", force=True)


def _cmd_status(args: list[str], send: Callable[[str, ...], None]) -> None:
    if _status_callback:
        report = _status_callback()
        send(report, priority="high", force=True)
    else:
        send("Status callback not registered.", priority="high", force=True)


def _cmd_graph(args: list[str], send: Callable[[str, ...], None]) -> None:
    logger.info("Command /graph received")
    if _graph_callback:
        result = _graph_callback()
        logger.info("Graph callback result: %s", "None" if result is None else f"caption={len(result[0])} chars, {len(result[1])} bytes")
        if result is None:
            send("📉 No closed-trade data available for chart yet.", priority="high", force=True)
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
                send("⚠️ Could not send chart image right now.", priority="high", force=True)
    else:
        send("Graph callback not registered.", priority="high", force=True)


def _cmd_pause(args: list[str], send: Callable[[str, ...], None]) -> None:
    _pause_flag.set()
    send("⏸️ Bot PAUSED — no new trades will be opened.", priority="high", force=True)
    logger.info("Bot paused via Telegram")


def _cmd_resume(args: list[str], send: Callable[[str, ...], None]) -> None:
    _pause_flag.clear()
    send("▶️ Bot RESUMED — normal operation.", priority="high", force=True)
    logger.info("Bot resumed via Telegram")


def _cmd_kill(args: list[str], send: Callable[[str, ...], None]) -> None:
    send(
        "🛑 KILL received — will close all positions and stop bot…",
        priority="critical",
        force=True,
    )
    _pause_flag.set()
    _kill_flag.set()


def _cmd_confirm(args: list[str], send: Callable[[str, ...], None], from_user_id: int = 0) -> None:
    _execute_pending_action(from_user_id, send)


def _cmd_doctor(args: list[str], send: Callable[[str, ...], None]) -> None:
    send("🔬 Running diagnostics (~20s)…", priority="normal")

    def _run():
        try:
            from pathlib import Path as P
            from utils.ops_doctor import format_text_report, run_doctor
            from config import settings as cfg
            root = P(cfg.REPO_ROOT) if hasattr(cfg, "REPO_ROOT") else P(__file__).resolve().parent.parent
            report = run_doctor(root)
            text = format_text_report(report)
            # Telegram message size limit
            for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
                send(chunk, priority="high", dedupe_key="doctor", force=True)
        except Exception as exc:
            logger.warning("Doctor run failed: %s", exc)
            send(f"⚠️ Doctor failed: {exc}", priority="normal")

    threading.Thread(target=_run, daemon=True).start()


def _cmd_trainlgbm(args: list[str], send: Callable[[str, ...], None]) -> None:
    send("🔧 Training LGBM ensemble from DB trades (~30–90s)…", priority="normal")

    def _run():
        try:
            import subprocess, sys
            from pathlib import Path
            root = Path(__file__).resolve().parents[2]
            result = subprocess.run(
                [sys.executable, str(root / "scripts" / "train_lgbm.py"), "--min-trades", "10"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=300,
            )
            out = (result.stdout + result.stderr).strip()[-1500:] or "completed"
            send(f"📊 LGBM train result:\n{out[-1500:]}", priority="high", dedupe_key="trainlgbm")
        except subprocess.TimeoutExpired:
            send("⚠️ Training timed out after 5 minutes.", priority="normal")
        except Exception as exc:
            logger.warning("train_lgbm failed: %s", exc)
            send(f"⚠️ LGBM training failed: {exc}", priority="normal")

    threading.Thread(target=_run, daemon=True).start()


def _cmd_trainprice(args: list[str], send: Callable[[str, ...], None]) -> None:
    symbols = args[0:] if args else []
    sym_str = " ".join(symbols) if symbols else "default universe"
    send(f"🔧 Training price-LGBM for: {sym_str} (~2–5 min per symbol)…", priority="normal")

    def _run():
        try:
            import subprocess, sys
            from pathlib import Path
            root = Path(__file__).resolve().parents[2]
            cmd = [sys.executable, str(root / "scripts" / "train_lgbm_price.py")]
            if symbols:
                cmd += ["--symbols"] + symbols
            result = subprocess.run(
                cmd,
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=600,
            )
            out = (result.stdout + result.stderr).strip()[-1500:] or "completed"
            send(f"📈 Price-LGBM train result:\n{out[-1500:]}", priority="high", dedupe_key="trainprice")
        except subprocess.TimeoutExpired:
            send("⚠️ Training timed out after 10 minutes.", priority="normal")
        except Exception as exc:
            logger.warning("train_lgbm_price failed: %s", exc)
            send(f"⚠️ Price-LGBM training failed: {exc}", priority="normal")

    threading.Thread(target=_run, daemon=True).start()


def _cmd_backtest(args: list[str], send: Callable[[str, ...], None]) -> None:
    if not args:
        send("Usage: /backtest SYMBOL  (e.g. /backtest EURUSD)", priority="normal")
        return
    symbol = args[0].upper()
    send(f"📉 Starting backtest for {symbol} (~30–120s)…", priority="normal")

    def _run():
        try:
            import subprocess, sys
            from pathlib import Path
            root = Path(__file__).resolve().parents[2]
            result = subprocess.run(
                [sys.executable, "scripts/backtest.py", "--symbols", symbol, "--candles", "2000"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=300,
            )
            out = (result.stdout + result.stderr).strip()[-2000:] or "completed"
            send(f"📊 Backtest for {symbol}:\n{out[-2000:]}", priority="high", dedupe_key=f"backtest:{symbol}")
        except subprocess.TimeoutExpired:
            send("⚠️ Backtest timed out after 5 minutes.", priority="normal")
        except Exception as exc:
            logger.warning("Backtest failed for %s: %s", symbol, exc)
            send(f"⚠️ Backtest failed for {symbol}: {exc}", priority="normal")

    threading.Thread(target=_run, daemon=True).start()


def _cmd_stats(args: list[str], send: Callable[[str, ...], None]) -> None:
    def _run():
        try:
            from adapters.db.db import Database
            from adapters.db.learning_repo import LearningRepo

            db = Database()
            repo = LearningRepo(db._pool)

            # Overall stats
            now = datetime.now(UTC)
            day_stats = repo.get_period_stats(now - timedelta(days=1), now)
            week_stats = repo.get_period_stats(now - timedelta(days=7), now)

            lines = ["📊 Learning Stats", "┈┈┈┈┈┈┈┈┈┈┈┈", "Last 24h:"]
            for k, v in day_stats.items():
                lines.append(f"  {k}: {v}")

            lines.append("\nLast 7 days:")
            for k, v in week_stats.items():
                lines.append(f"  {k}: {v}")

            # Strategy streaks
            from config import settings as cfg
            if hasattr(cfg, "STRATEGY_PLUGINS"):
                for plugin in cfg.STRATEGY_PLUGINS:
                    strat = plugin.split(".")[-1]
                    streak = repo.get_strategy_streak(strat)
                    conf = repo.get_confidence(strat)
                    avg = repo.get_rolling_avg_score(strat) or 0.0
                    lines.append(f"\n  {strat}: conf={conf:.3f} streak={streak} avg_score={avg:.2f}")

            send("\n".join(lines[:60]), priority="high", dedupe_key="stats")
        except Exception as exc:
            logger.warning("stats command failed: %s", exc)
            send(f"⚠️ /stats failed: {exc}", priority="normal")

    threading.Thread(target=_run, daemon=True).start()


def _cmd_confidence(args: list[str], send: Callable[[str, ...], None]) -> None:
    if not args:
        send("Usage: /confidence [strategy] [value]\n  Getter: /confidence ICTStrategy\n  Setter: /confidence ICTStrategy 0.72", priority="normal")
        return

    strategy = args[0]
    if len(args) >= 2:
        try:
            value = float(args[1])
            from adapters.db.db import Database
            from adapters.db.learning_repo import LearningRepo
            db = Database()
            repo = LearningRepo(db._pool)
            repo.upsert_confidence(strategy, value, 0, 0)
            send(f"✅ {strategy} confidence → {value:.3f}", priority="high", force=True, dedupe_key=f"conf:set:{strategy}")
            logger.info("Confidence updated via Telegram: %s -> %.3f", strategy, value)
        except Exception as exc:
            send(f"⚠️ Failed to set confidence: {exc}", priority="normal")
    else:
        try:
            from adapters.db.db import Database
            from adapters.db.learning_repo import LearningRepo
            db = Database()
            repo = LearningRepo(db._pool)
            conf = repo.get_confidence(strategy)
            streak = repo.get_strategy_streak(strategy)
            avg = repo.get_rolling_avg_score(strategy)
            send(
                f"📈 {strategy}\n  confidence: {conf:.3f}\n  streak: {streak}\n  avg_score: {avg if avg is not None else '?'}",
                priority="high",
                dedupe_key=f"conf:get:{strategy}",
            )
        except Exception as exc:
            send(f"⚠️ Failed to get confidence: {exc}", priority="normal")


def _cmd_reset_learning(args: list[str], send: Callable[[str, ...], None], from_user_id: int = 0) -> None:
    """Register a pending action — actual reset happens on /confirm."""
    action_key = (from_user_id, "reset_learning")
    _pending_actions[action_key] = "This will DELETE all trade scores, strategy confidence, and performance snapshots. This cannot be undone."
    send(
        "⚠️ /reset_learning will wipe ALL learning data (scores, confidence, snapshots).\n"
        "Reply /confirm to proceed, or just ignore to cancel.",
        priority="high",
        force=True,
    )


def _do_reset_learning(send: Callable[[str, ...], None]) -> None:
    try:
        from adapters.db.db import Database
        from adapters.db.learning_repo import LearningRepo
        db = Database()
        repo = LearningRepo(db._pool)
        result = repo.reset_learning_state()
        lines = ["🧹 Learning state reset", "┈┈┈┈┈┈┈┈┈┈┈┈"]
        for table, count in result.items():
            lines.append(f"  {table}: {count} rows removed")
        send("\n".join(lines), priority="high", force=True)
        logger.info("Learning state reset via Telegram: %s", result)
    except Exception as exc:
        logger.warning("reset_learning failed: %s", exc)
        send(f"⚠️ Reset failed: {exc}", priority="normal")


def _cmd_setparam(args: list[str], send: Callable[[str, ...], None]) -> None:
    if len(args) < 2:
        send("Usage: /setparam KEY VALUE  (e.g. /setparam SNIPER_CONF_THRESHOLD 0.50)", priority="normal")
        return

    key, value = args[0].upper(), args[1]
    _runtime_params[key] = value

    # Try to apply to settings in-memory
    try:
        import config.settings as cfg
        if hasattr(cfg, key):
            old = getattr(cfg, key)
            # Type coerce — bool, int, float, str
            try:
                if isinstance(old, bool):
                    coerced = value.lower() in ("true", "1", "yes")
                elif isinstance(old, int):
                    coerced = int(value)
                elif isinstance(old, float):
                    coerced = float(value)
                else:
                    coerced = value
                setattr(cfg, key, coerced)
                send(f"✅ {key} → {coerced} (was {old})", priority="high", force=True, dedupe_key=f"setparam:{key}")
            except Exception:
                send(f"✅ {key} = {value} (stored, type mismatch — restart to apply)", priority="high", force=True)
        else:
            send(f"✅ {key} = {value} (volatile override set)", priority="high", force=True)
        logger.info("Runtime param set via Telegram: %s = %s", key, value)
    except Exception as exc:
        send(f"✅ {key} = {value} (volatile override set)", priority="high", force=True)
        logger.info("Runtime param set (fallback): %s = %s [%s]", key, value, exc)


def _cmd_perf(args: list[str], send: Callable[[str, ...], None]) -> None:
    period = (args[0] or "day").lower()
    if period not in ("day", "week", "month"):
        period = "day"

    offset_map = {"day": 1, "week": 7, "month": 30}
    days = offset_map[period]

    def _run():
        try:
            from adapters.db.db import Database
            from adapters.db.learning_repo import LearningRepo
            from datetime import timedelta as td

            db = Database()
            repo = LearningRepo(db._pool)
            now = datetime.now(UTC)
            stats = repo.get_period_stats(now - td(days=days), now)

            wr = stats.get("win_rate", 0.0) * 100
            pnl = stats.get("total_pnl", 0.0)
            trades = stats.get("trades", 0)
            avg = stats.get("avg_score", 0.0)

            emoji = "📈" if pnl >= 0 else "📉"
            send(
                f"{emoji} Performance — last {period}\n"
                f"┈┈┈┈┈┈┈┈┈┈┈┈\n"
                f"  Trades:    {trades}\n"
                f"  Win rate:  {wr:.1f}%\n"
                f"  Total P&L: ${pnl:+.2f}\n"
                f"  Avg score: {avg:.2f}",
                priority="high",
                dedupe_key=f"perf:{period}",
            )
        except Exception as exc:
            logger.warning("perf command failed: %s", exc)
            send(f"⚠️ /perf failed: {exc}", priority="normal")

    threading.Thread(target=_run, daemon=True).start()


def _cmd_signals(args: list[str], send: Callable[[str, ...], None]) -> None:
    def _run():
        try:
            from adapters.db.db import Database

            db = Database()
            conn = db._pool.get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT symbol, direction, confidence, created_at
                           FROM signals
                           WHERE created_at >= NOW() - INTERVAL '1 hour'
                           ORDER BY created_at DESC
                           LIMIT 20"""
                    )
                    rows = cur.fetchall()
            finally:
                db._pool.put_conn(conn)

            if not rows:
                send("🔍 No signals in the last scan cycle.", priority="normal")
                return

            lines = ["📡 Active Signals (last scan)", "┈┈┈┈┈┈┈┈┈┈┈┈"]
            for sym, direction, conf, created in rows:
                arrow = "🟢" if direction.upper() == "BUY" else "🔴"
                lines.append(f"  {arrow} {sym:<10} {direction:<4} conf={conf:.2f} {created}")
            send("\n".join(lines[:50]), priority="high", dedupe_key="signals")
        except Exception as exc:
            logger.warning("signals command failed: %s", exc)
            send(f"⚠️ /signals failed: {exc}", priority="normal")

    threading.Thread(target=_run, daemon=True).start()


def _cmd_log(args: list[str], send: Callable[[str, ...], None]) -> None:
    try:
        n = int(args[0]) if args else 20
        n = min(max(n, 1), 200)
    except Exception:
        n = 20

    try:
        from config import settings as cfg
        log_dir = Path(cfg.LOG_DIR) if hasattr(cfg, "LOG_DIR") else Path("logs/backend")
        log_files = sorted(log_dir.glob("backend_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not log_files:
            send("📋 No backend log files found.", priority="normal")
            return

        content = log_files[0].read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        tail = "\n".join(lines[-n:])
        send(f"📋 Last {n} lines ({log_files[0].name}):\n{tail[-3500:]}", priority="high", dedupe_key="log")
    except Exception as exc:
        send(f"⚠️ /log failed: {exc}", priority="normal")


def _cmd_agents(args: list[str], send: Callable[[str, ...], None]) -> None:
    try:
        n = int(args[0]) if args else 10
        n = min(max(n, 1), 50)
    except Exception:
        n = 10

    def _run():
        try:
            from adapters.db.db import Database
            db = Database()
            conn = db._pool.get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """SELECT agent, level, message, created_at
                           FROM agent_events
                           ORDER BY created_at DESC
                           LIMIT %s""",
                        (n,),
                    )
                    rows = cur.fetchall()
            finally:
                db._pool.put_conn(conn)

            if not rows:
                send("🔍 No agent events found.", priority="normal")
                return

            lines = ["🤖 Agent Events", "┈┈┈┈┈┈┈┈┈┈┈┈"]
            for agent, level, message, created in rows:
                short = (message or "")[:60]
                lines.append(f"  {created}  {agent}/{level}: {short}")
            send("\n".join(lines[:50]), priority="high", dedupe_key="agents")
        except Exception as exc:
            logger.warning("agents command failed: %s", exc)
            send(f"⚠️ /agents failed: {exc}", priority="normal")

    threading.Thread(target=_run, daemon=True).start()


def _cmd_macro(args: list[str], send: Callable[[str, ...], None]) -> None:
    def _run():
        try:
            from filters.intelligence_sweep import IntelligenceSweep
            from datetime import timedelta as td

            sweep = IntelligenceSweep()
            snapshot = sweep.get_latest()  # returns MacroSnapshot (synchronous, non-blocking)

            if not snapshot:
                send("📊 Macro snapshot unavailable right now.", priority="normal")
                return

            lines = ["🌐 Macro Snapshot", "┈┈┈┈┈┈┈┈┈┈┈┈"]
            for key, label in [
                ("vixcls", "VIX"),
                ("dxy_prev_close", "DXY"),
                ("dgs10", "10Y Treasury"),
                ("dgs2", "2Y Treasury"),
                ("dcoilwtico", "WTI Crude"),
                ("fedfunds", "Fed Funds"),
                ("cpiaucsl", "CPI"),
                ("gdelt_risk_tone", "GDELT tone"),
                ("yield_curve_inverted", "Curve inverted"),
                ("usd_strength", "USD"),
                ("risk_tier", "Risk tier"),
            ]:
                val = getattr(snapshot, key, None)
                if val is not None:
                    lines.append(f"  {label}: {val}")

            if snapshot.sources_failed:
                lines.append(f"  ⚠️ Failed sources: {', '.join(snapshot.sources_failed)}")

            send("\n".join(lines[:60]), priority="high", dedupe_key="macro")
        except Exception as exc:
            logger.warning("macro command failed: %s", exc)
            send(f"⚠️ /macro failed: {exc}", priority="normal")

    threading.Thread(target=_run, daemon=True).start()


def _cmd_hypothesis(args: list[str], send: Callable[[str, ...], None]) -> None:
    send("🔬 Running hypothesis cycle (~60s)…", priority="normal")

    def _run():
        try:
            from agents.hypothesis_agent import HypothesisAgent
            from adapters.db.db import Database
            db = Database()
            agent = HypothesisAgent(db)
            result = agent.run_cycle()
            send(result or "✅ Hypothesis cycle completed.", priority="normal", dedupe_key="hypothesis")
        except Exception as exc:
            logger.warning("HypothesisAgent failed: %s", exc)
            send("⚠️ Hypothesis agent failed.", priority="normal")

    threading.Thread(target=_run, daemon=True).start()


# ── Command registry ────────────────────────────────────────────────────────

"""
Command signatures:
  _cmd_*(args: list[str], send: Callable[[str, ...], None], *, from_user_id: int = 0) -> None

Handler signature: (args, send_fn [, from_user_id])
"""
_COMMANDS: dict[str, tuple[str, _Handler, bool]] = {
    # (description, handler, requires_user_id)
    "help":          ("Show this help text",                          _cmd_help,          False),
    "status":        ("Bot + account status",                         _cmd_status,        False),
    "graph":         ("Send performance chart",                       _cmd_graph,         False),
    "pause":         ("Block new entries",                             _cmd_pause,         False),
    "resume":        ("Resume normal operation",                       _cmd_resume,        False),
    "kill":          ("Close all positions and stop",                  _cmd_kill,          False),
    "confirm":       ("Confirm a pending action",                      _cmd_confirm,       True),
    "doctor":        ("Run MT5/DB/model diagnostics",                  _cmd_doctor,        False),
    "trainlgbm":     ("Train LGBM ensemble from closed trades",        _cmd_trainlgbm,     False),
    "trainprice":    ("Train per-symbol price model(s)",               _cmd_trainprice,    False),
    "backtest":      ("Run backtest on a symbol",                      _cmd_backtest,      False),
    "stats":         ("Strategy learning stats",                       _cmd_stats,         False),
    "confidence":    ("Get/set strategy confidence",                   _cmd_confidence,    False),
    "reset_learning":("Wipe all learning data (needs /confirm)",       _cmd_reset_learning, True),
    "setparam":      ("Hot-swap a runtime parameter",                  _cmd_setparam,      False),
    "perf":          ("Performance summary (day|week|month)",           _cmd_perf,          False),
    "signals":       ("Active signals from last scan",                 _cmd_signals,       False),
    "log":           ("Tail N log lines",                              _cmd_log,           False),
    "agents":        ("Last N agent events",                           _cmd_agents,        False),
    "macro":         ("Latest macro snapshot",                         _cmd_macro,         False),
    "hypothesis":    ("Run AI hypothesis test",                       _cmd_hypothesis,   False),
}


# ── Inbound polling ─────────────────────────────────────────────────────────

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

    # Send welcome menu on first successful poll
    welcome_sent = False

    while not _stop_polling.is_set():
        try:
            url = f"{base}/getUpdates?offset={offset}&timeout=10"
            req = Request(url, method="GET")
            with urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())

            # Send welcome menu once on first successful poll
            if not welcome_sent:
                send_welcome()
                welcome_sent = True

            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "").strip()
                from_chat = str(msg.get("chat", {}).get("id", ""))
                logger.debug("Telegram poll: update_id=%s text=%r from_chat=%s expecting=%s", update["update_id"], text, from_chat, chat_id)
                if from_chat != chat_id:
                    logger.debug("Telegram: chat_id mismatch — skipping (from=%s, expected=%s)", from_chat, chat_id)
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
    logger.debug("Telegram _handle_command: text=%r cmd=%r", text, cmd)
    if not cmd:
        return

    # Strip leading slash if present
    if cmd.startswith("/"):
        cmd = cmd[1:]

    if not _is_authorized_user(from_user_id, from_username):
        logger.warning(
            "Blocked unauthorized Telegram command '%s' from user_id=%s username='%s'",
            cmd,
            from_user_id,
            from_username,
        )
        return

    logger.info("Telegram command passed auth: cmd=%s user_id=%s username=%s", cmd, from_user_id, from_username)

    args = text.split()[1:] if len(text.split()) > 1 else []

    def send(text: str, **kwargs) -> None:
        send_message(text, **kwargs)

    # Route through command registry
    logger.info("Telegram: cmd=%r passed auth for user_id=%s username=%r", cmd, from_user_id, from_username)
    if cmd in _COMMANDS:
        desc, handler, needs_uid = _COMMANDS[cmd]
        try:
            if needs_uid:
                handler(args, send, from_user_id=from_user_id)
            else:
                handler(args, send)
        except Exception as exc:
            logger.warning("Command %s failed: %s", cmd, exc)
            send(f"⚠️ Command /{cmd} failed: {exc}", priority="normal")
    elif cmd in ("help", "start"):
        _cmd_help(args, send)
    else:
        # Free-text -> CLAUDE agent
        try:
            from agents.claude_agent import answer as claude_answer
            result = claude_answer(text)
            if isinstance(result, tuple):
                reply, pending = result
                if pending:
                    action_key = (from_user_id, pending["action"])
                    _pending_actions[action_key] = pending.get("warning", "")
                    send(reply, priority="high", force=True, dedupe_key=f"claude:{text[:40]}")
                else:
                    send(reply, priority="normal", dedupe_key=f"claude:{text[:40]}")
            else:
                send(result, priority="normal", dedupe_key=f"claude:{text[:40]}")
        except Exception as exc:
            logger.warning("ClaudeAgent failed: %s", exc)
            send("⚠️ Claude agent unavailable.", priority="normal")


def start_polling() -> threading.Thread:
    """Start the background polling thread.  Returns the thread handle.

    On first successful poll, sends the welcome/command menu to Telegram.
    """
    t = threading.Thread(target=_poll_updates, daemon=True, name="telegram-poll")
    t.start()
    return t


def send_welcome() -> None:
    """Send the command menu to Telegram — called once on first poll."""
    send_message(
        _WELCOME_TEXT,
        priority="high",
        force=True,
        dedupe_key="welcome",
    )


_WELCOME_TEXT = (
    "🤖 PulseTrade TradingBot — Online\n"
    "┈┈┈┈┈┈┈┈┈┈┈┈\n"
    "📊 MONITORING\n"
    "  /status   — bot + account status\n"
    "  /doctor   — MT5 / DB / model diagnostics\n"
    "  /stats    — strategy learning stats\n"
    "  /confidence [strat] [val] — get/set strategy confidence\n"
    "  /perf [day|week|month] — performance summary\n"
    "  /signals  — active signals from last scan\n"
    "  /log N    — tail N log lines\n"
    "  /agents N — last N agent events\n"
    "  /macro    — latest macro snapshot\n"
    "\n🛡️ CONTROL\n"
    "  /pause    — block new entries\n"
    "  /resume   — resume entries\n"
    "  /kill     — close all + shutdown\n"
    "\n⚙️ OPERATIONS\n"
    "  /trainlgbm     — train LGBM ensemble\n"
    "  /trainprice [SYM...] — train price model(s)\n\n"
    "  /backtest SYM  — run symbol backtest\n"
    "  /setparam KEY VAL — hot-swap setting\n"
    "  /reset_learning — wipe learning state (needs /confirm)\n"
    "  /confirm   — confirm a pending action\n"
    "  /graph     — performance chart\n"
    "  /hypothesis — run AI hypothesis test\n"
)


def stop_polling() -> None:
    _stop_polling.set()