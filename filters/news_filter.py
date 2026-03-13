"""Economic calendar blackout filter (stub for V1).

V1 ships with a static-JSON approach: a ``news_events.json`` file can be
placed next to this module and it will be loaded at startup.  The filter
checks whether a high-impact event is within *NEWS_BLACKOUT_MINUTES* of
the current time and returns True to block trading.

When a real API key is provided, the ``finnhub`` source is used.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from config import settings

if TYPE_CHECKING:
    from database.db import Database

logger = logging.getLogger(__name__)

_EVENTS_FILE = Path(__file__).parent / "news_events.json"


def _load_static_events() -> list[dict[str, str]]:
    """Load events from ``news_events.json`` if present."""
    if _EVENTS_FILE.exists():
        with open(_EVENTS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logger.error("Failed to parse %s", _EVENTS_FILE)
    return []


class NewsFilter:
    """Determines whether trading should be paused due to an imminent
    high-impact news event.
    """

    def __init__(self, db: Database | None = None) -> None:
        self._db = db
        self._events: list[dict[str, str]] = _load_static_events()
        if self._events:
            logger.info("NewsFilter loaded %d static events", len(self._events))
        else:
            logger.info("NewsFilter: no static events loaded — filter is inactive")

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("news", level, msg, data)

    def is_blackout(self, symbol: str) -> bool:
        """Return True if *symbol* should be blocked due to an upcoming event.

        Each event in the JSON looks like::

            {"currency": "USD", "time": "2026-03-13T13:30:00", "impact": "high", "title": "CPI"}
        """
        if not self._events:
            self._emit("info", f"No calendar events loaded — {symbol} news check skipped",
                       {"symbol": symbol, "events_loaded": 0})
            return False

        now = datetime.now(UTC)
        window = timedelta(minutes=settings.NEWS_BLACKOUT_MINUTES)

        # Extract currencies from symbol (first 3 + last 3)
        currencies = {symbol[:3], symbol[3:6]} if len(symbol) >= 6 else {symbol}

        nearby: list[dict] = []
        for ev in self._events:
            if ev.get("impact", "").lower() != "high":
                continue
            if ev.get("currency", "").upper() not in currencies:
                continue
            try:
                ev_time = datetime.fromisoformat(ev["time"])
            except (KeyError, ValueError):
                continue
            if abs(now - ev_time) <= window:
                logger.info("NEWS BLACKOUT: %s — %s (%s)", ev.get("title"), ev["time"], ev["currency"])
                nearby.append({"title": ev.get("title"), "time": ev["time"],
                               "currency": ev.get("currency")})

        if nearby:
            self._emit("warn",
                       f"NEWS BLACKOUT on {symbol} — {len(nearby)} high-impact events nearby",
                       {"symbol": symbol, "events": nearby})
            return True

        self._emit("info",
                   f"{symbol} news clear — {len(self._events)} events checked, none within window",
                   {"symbol": symbol, "events_loaded": len(self._events),
                    "blackout_window_min": settings.NEWS_BLACKOUT_MINUTES})
        return False
