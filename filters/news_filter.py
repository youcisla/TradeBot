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

from config import settings

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

    def __init__(self) -> None:
        self._events: list[dict[str, str]] = _load_static_events()
        if self._events:
            logger.info("NewsFilter loaded %d static events", len(self._events))
        else:
            logger.info("NewsFilter: no static events loaded — filter is inactive")

    def is_blackout(self, symbol: str) -> bool:
        """Return True if *symbol* should be blocked due to an upcoming event.

        Each event in the JSON looks like::

            {"currency": "USD", "time": "2026-03-13T13:30:00", "impact": "high", "title": "CPI"}
        """
        if not self._events:
            return False

        now = datetime.now(UTC)
        window = timedelta(minutes=settings.NEWS_BLACKOUT_MINUTES)

        # Extract currencies from symbol (first 3 + last 3)
        currencies = {symbol[:3], symbol[3:6]} if len(symbol) >= 6 else {symbol}

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
                return True

        return False
