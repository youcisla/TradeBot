"""Logging Agent — structured logging, event recording, and daily digest.

Answers: *What happened?*

Responsibilities:
- Python logging setup (file + console, rotating)
- Record structured events to DB events table
- Build and send daily summary via Telegram
"""

from __future__ import annotations

import logging
import logging.handlers
import os
from datetime import date, datetime
from pathlib import Path

from config import settings
from database.db import Database
from utils import telegram_bot

logger = logging.getLogger(__name__)


class LoggingAgent:
    """Central logging hub for the bot."""

    def __init__(self, db: Database, log_dir: str = "logs") -> None:
        self._db = db
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)
        self._configure_logging()

    # ── public API ───────────────────────────────────────────────────────

    def record(self, event_type: str, data: str, level: str = "INFO") -> None:
        """Write an event to DB + Python logger."""
        self._db.log_event(event_type, data, datetime.utcnow().isoformat())
        log_fn = getattr(logger, level.lower(), logger.info)
        log_fn("[%s] %s", event_type, data)

    def log_trade(self, trade_id: str, action: str, details: str) -> None:
        self.record("TRADE", f"{trade_id} | {action} | {details}")

    def send_daily_summary(self, report: dict) -> None:
        """Format and send the learning report via Telegram."""
        if report.get("trades_today", 0) == 0:
            msg = f"📊 Daily summary ({date.today()}): No trades today."
        else:
            msg = (
                f"📊 Daily summary ({date.today()})\n"
                f"Trades: {report['trades_today']} "
                f"(W {report['wins']} / L {report['losses']})\n"
                f"Win rate: {report['win_rate']:.0%}\n"
                f"Total PnL: {report['total_pnl']:.2f}\n"
                f"Avg PnL: {report['avg_pnl']:.2f}"
            )
        telegram_bot.send_message(msg)
        self.record("DAILY_SUMMARY", msg)

    # ── setup ────────────────────────────────────────────────────────────

    def _configure_logging(self) -> None:
        root = logging.getLogger()
        if root.handlers:
            return  # already configured

        root.setLevel(logging.DEBUG)

        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(fmt)
        root.addHandler(ch)

        # Rotating file handler
        log_file = self._log_dir / f"bot_{date.today().isoformat()}.log"
        fh = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=5_000_000, backupCount=5, encoding="utf-8",
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        root.addHandler(fh)

        logger.info("Logging configured → %s", log_file)
