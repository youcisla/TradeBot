"""Logging Agent — structured logging, event recording, and daily digest.

Answers: *What happened?*

Responsibilities:
- Python logging setup (file + console, rotating)
- Record structured events to DB events table
- CSV trade journal for offline analysis
- Build and send daily summary via Telegram
"""

from __future__ import annotations

import csv
import logging
import logging.handlers
import os
from datetime import date, datetime
from pathlib import Path

from config import settings
from database.db import Database
from models.trade import Trade
from utils import telegram_bot

logger = logging.getLogger(__name__)

_TRADE_CSV_HEADERS = [
    "id", "symbol", "strategy", "direction", "entry_price", "lot_size",
    "stop_loss", "take_profit_1", "take_profit_2", "take_profit_3",
    "tp1_hit", "tp2_hit", "tp3_hit", "status", "open_time", "close_time",
    "pnl", "close_reason", "broker_ticket", "spread_at_entry",
    "snap_rsi_aligned", "snap_trend_aligned", "snap_volume_sufficient",
    "snap_near_news_event", "snap_market_condition", "snap_session",
    "snap_day_of_week",
]


class LoggingAgent:
    """Central logging hub for the bot."""

    def __init__(self, db: Database, log_dir: str = "logs") -> None:
        self._db = db
        self._log_dir = Path(log_dir)
        self._log_dir.mkdir(exist_ok=True)
        self._trade_csv = self._log_dir / "trade_journal.csv"
        self._configure_logging()
        self._ensure_csv_header()

    # ── public API ───────────────────────────────────────────────────────

    def record(self, event_type: str, data: str, level: str = "INFO") -> None:
        """Write an event to DB + Python logger."""
        self._db.log_event(
            level=level,
            source=event_type,
            message=data,
        )
        self._db.log_agent_event("logging", level.lower(),
                                 f"[{event_type}] {data}")
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

    def log_trade_to_csv(self, trade: Trade) -> None:
        """Append a trade row to the CSV journal for offline analysis."""
        with open(self._trade_csv, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                trade.id, trade.symbol, trade.strategy, trade.direction,
                trade.entry_price, trade.lot_size, trade.stop_loss,
                trade.take_profit_1, trade.take_profit_2, trade.take_profit_3,
                trade.tp1_hit, trade.tp2_hit, trade.tp3_hit,
                trade.status, trade.open_time.isoformat(),
                trade.close_time.isoformat() if trade.close_time else "",
                trade.pnl, trade.close_reason, trade.broker_ticket,
                trade.spread_at_entry, trade.snap_rsi_aligned,
                trade.snap_trend_aligned, trade.snap_volume_sufficient,
                trade.snap_near_news_event, trade.snap_market_condition,
                trade.snap_session, trade.snap_day_of_week,
            ])

    def log_risk_rejection(self, symbol: str, direction: str,
                           strategy: str, reason: str) -> None:
        """Record a risk rejection to DB + log for analysis."""
        self.record("RISK_REJECT",
                     f"{symbol} {direction} {strategy} — {reason}",
                     level="WARNING")

    # ── internal ─────────────────────────────────────────────────────────

    def _ensure_csv_header(self) -> None:
        if not self._trade_csv.exists() or self._trade_csv.stat().st_size == 0:
            with open(self._trade_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(_TRADE_CSV_HEADERS)

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
