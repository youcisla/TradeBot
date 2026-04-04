"""Shared utility functions."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from config.symbols import CRYPTO, SYMBOL_CLASS


def _local_tz() -> ZoneInfo:
    """Return the configured local timezone (lazy import avoids circular dep)."""
    from config import settings
    return ZoneInfo(settings.TIMEZONE)


def local_now() -> datetime:
    """Return the current time in the configured local timezone (e.g. Europe/Paris).

    Use this for **display purposes only** — logs, day labels, summary scheduling.
    All internal trading logic (sessions, market hours, candle timestamps) must
    keep using ``datetime.now(UTC)`` so DST never affects trade decisions.
    """
    return datetime.now(_local_tz())


def current_session(dt: datetime | None = None) -> str:
    """Return the forex session name based on UTC hour.

    Returns one of: "asian", "london", "overlap", "newyork"
    London   07:00 – 11:59 UTC  → "london"
    Overlap  12:00 – 15:59 UTC  → "overlap"  (London + NY)
    New York 16:00 – 20:59 UTC  → "newyork"
    Asian    00:00 – 06:59 + 21:00 – 23:59 UTC  → "asian"

    Parameters
    ----------
    dt : datetime, optional
        Override the timestamp (useful for backtesting).  Must be UTC-aware.
    """
    hour = (dt if dt is not None else datetime.now(UTC)).hour
    if 12 <= hour < 16:
        return "overlap"
    if 7 <= hour < 16:
        return "london"
    if 12 <= hour < 21:
        return "newyork"
    return "asian"


def day_of_week() -> str:
    """Return the current day name in the configured local timezone."""
    return local_now().strftime("%A")


# ── Market hours ─────────────────────────────────────────────────────────

def is_market_open(symbol: str, now: datetime | None = None) -> bool:
    """Return True if the market for *symbol* is currently open.

    Forex / Commodities / Exotics:
        Open  : Sunday  22:00 UTC  →  Friday 22:00 UTC
        Closed: Friday  22:00 UTC  →  Sunday 22:00 UTC

    Crypto:
        Open  : 24/7/365

    Parameters
    ----------
    symbol : str
        The instrument symbol (e.g. "EURUSD", "BTCUSD").
    now : datetime, optional
        Override the current time (useful for testing).  Must be UTC.
    """
    # Crypto never closes
    if symbol in CRYPTO or SYMBOL_CLASS.get(symbol) == "crypto":
        return True

    if now is None:
        now = datetime.now(UTC)

    weekday = now.weekday()   # Mon=0 … Sun=6
    hour = now.hour

    # Friday after 22:00 UTC → closed
    if weekday == 4 and hour >= 22:
        return False

    # Saturday → always closed
    if weekday == 5:
        return False

    # Sunday before 22:00 UTC → closed
    if weekday == 6 and hour < 22:
        return False

    return True


def is_any_market_open(symbols: list[str], now: datetime | None = None) -> bool:
    """Return True if at least one symbol's market is open."""
    return any(is_market_open(s, now) for s in symbols)


def is_weekend(now: datetime | None = None) -> bool:
    """Return True during the forex weekend (Friday 22:00 UTC – Sunday 22:00 UTC).

    During this window only crypto markets are open.  The bot switches to
    weekend mode: crypto-only symbols, multi-timeframe ICT analysis.
    """
    if now is None:
        now = datetime.now(UTC)
    weekday = now.weekday()   # Mon=0 … Sun=6
    hour = now.hour

    if weekday == 5:           # All of Saturday
        return True
    if weekday == 4 and hour >= 22:   # Friday from 22:00
        return True
    if weekday == 6 and hour < 22:    # Sunday before 22:00
        return True
    return False
