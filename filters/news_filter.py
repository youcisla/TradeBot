"""Economic calendar blackout filter.

Fetches high-impact economic events from Finnhub's free Economic Calendar
endpoint and caches them locally.  Falls back to a static ``news_events.json``
file if the API key is missing or the fetch fails.

Events are refreshed automatically every 6 hours.
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING

from config import settings

if TYPE_CHECKING:
    from database.db import Database

logger = logging.getLogger(__name__)

_EVENTS_FILE = Path(__file__).parent / "news_events.json"
_CACHE_FILE = Path(__file__).parent / "news_cache.json"
_REFRESH_INTERVAL = timedelta(hours=6)
_FETCH_RETRY_COOLDOWN = timedelta(hours=1)


def _load_static_events() -> list[dict[str, str]]:
    """Load events from ``news_events.json`` if present."""
    if _EVENTS_FILE.exists():
        with open(_EVENTS_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logger.error("Failed to parse %s", _EVENTS_FILE)
    return []


def _load_cache() -> tuple[list[dict[str, str]], datetime | None]:
    """Load cached Finnhub events and their fetch timestamp."""
    if _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE, "r") as f:
                data = json.load(f)
            fetched_at = datetime.fromisoformat(data["fetched_at"])
            return data.get("events", []), fetched_at
        except (json.JSONDecodeError, KeyError, ValueError):
            logger.warning("Corrupted news cache — will re-fetch")
    return [], None


def _save_cache(events: list[dict[str, str]]) -> None:
    with open(_CACHE_FILE, "w") as f:
        json.dump({"fetched_at": datetime.now(UTC).isoformat(), "events": events}, f)


def _fetch_finnhub_calendar() -> list[dict[str, str]]:
    """Fetch the next 7 days of economic events from Finnhub."""
    key = settings.FINNHUB_API_KEY
    if not key:
        return []

    today = datetime.now(UTC).date()
    from_date = today.isoformat()
    to_date = (today + timedelta(days=7)).isoformat()
    url = (
        f"https://finnhub.io/api/v1/calendar/economic"
        f"?from={from_date}&to={to_date}&token={key}"
    )

    try:
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = json.loads(resp.read().decode())
    except (urllib.error.URLError, json.JSONDecodeError, OSError) as exc:
        logger.warning("Finnhub calendar fetch failed: %s", exc)
        return []

    parsed: list[dict[str, str]] = []
    for ev in raw.get("economicCalendar", []):
        impact = ev.get("impact", 0)
        # Finnhub uses 1=low, 2=medium, 3=high
        if impact < 3:
            continue
        country = ev.get("country") or ""
        # Map country to currency (common ones)
        currency = {
            "US": "USD", "EU": "EUR", "GB": "GBP", "JP": "JPY",
            "AU": "AUD", "CA": "CAD", "NZ": "NZD", "CH": "CHF",
        }.get(country, country) or country
        time_str = ev.get("time") or "00:00:00"
        date_str = ev.get("date") or ""
        if not date_str:
            continue
        parsed.append({
            "currency": currency,
            "time": f"{date_str}T{time_str}",
            "impact": "high",
            "title": ev.get("event", "Unknown") or "Unknown",
        })

    logger.info("Finnhub: fetched %d high-impact events for next 7 days", len(parsed))
    return parsed


class NewsFilter:
    """Determines whether trading should be paused due to an imminent
    high-impact news event.
    """

    def __init__(self, db: Database | None = None) -> None:
        self._db = db
        self._last_fetch: datetime | None = None
        self._last_fetch_failed: datetime | None = None
        self._events: list[dict[str, str]] = []
        self._load_events()

    def _load_events(self) -> None:
        """Load events from cache/Finnhub, falling back to static file."""
        # Try cache first
        cached, fetched_at = _load_cache()
        if cached and fetched_at and (datetime.now(UTC) - fetched_at < _REFRESH_INTERVAL):
            self._events = cached
            self._last_fetch = fetched_at
            logger.info("NewsFilter loaded %d events from cache", len(cached))
            return

        # Finnhub disabled — skip to static file fallback
        # finnhub_events = _fetch_finnhub_calendar()
        # if finnhub_events:
        #     self._events = finnhub_events
        #     self._last_fetch = datetime.now(UTC)
        #     self._last_fetch_failed = None
        #     _save_cache(finnhub_events)
        #     return

        # Fallback to static file
        self._events = _load_static_events()
        if self._events:
            logger.info("NewsFilter loaded %d static events", len(self._events))
        else:
            logger.info("NewsFilter: no static events available — news filter inactive")

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("news", level, msg, data)

    def is_blackout(self, symbol: str) -> bool:
        """Return True if *symbol* should be blocked due to an upcoming event.

        Each event in the JSON looks like::

            {"currency": "USD", "time": "2026-03-13T13:30:00", "impact": "high", "title": "CPI"}
        """
        # Check Crucix FLASH alerts first (highest priority blackout)
        try:
            from filters.crucix_client import get_macro_context
            macro = get_macro_context()
            if macro.is_blackout and not macro.is_stale:
                logger.info(
                    "CRUCIX FLASH BLACKOUT on %s — %s",
                    symbol,
                    ", ".join(macro.active_flash_alerts[:2]) or "unspecified alerts",
                )
                self._emit("warn",
                           f"CRUCIX FLASH blackout: {symbol} blocked by macro alert",
                           {"symbol": symbol, "alerts": macro.active_flash_alerts})
                return True
        except Exception:
            pass  # Crucix unavailable — fall through to calendar check

        # Auto-refresh every 6 hours (respects failure cooldown internally)
        if (
            self._last_fetch is None
            or (datetime.now(UTC) - self._last_fetch) >= _REFRESH_INTERVAL
        ):
            self._load_events()

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
