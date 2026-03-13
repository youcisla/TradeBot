"""Shared utility functions."""

from __future__ import annotations

from datetime import UTC, datetime

from config.symbols import CRYPTO, SYMBOL_CLASS


def current_session() -> str:
    """Return the forex session name based on current UTC hour.

    London   07:00 – 16:00 UTC
    New York 12:00 – 21:00 UTC
    Asian    00:00 – 09:00 UTC
    Overlap  12:00 – 16:00 UTC (London + NY)
    """
    hour = datetime.now(UTC).hour
    if 12 <= hour < 16:
        return "overlap"
    if 7 <= hour < 16:
        return "london"
    if 12 <= hour < 21:
        return "newyork"
    return "asian"


def day_of_week() -> str:
    return datetime.now(UTC).strftime("%A")


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
