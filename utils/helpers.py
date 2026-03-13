"""Shared utility functions."""

from __future__ import annotations

from datetime import datetime


def current_session() -> str:
    """Return the forex session name based on current UTC hour.

    London   07:00 – 16:00 UTC
    New York 12:00 – 21:00 UTC
    Asian    00:00 – 09:00 UTC
    Overlap  12:00 – 16:00 UTC (London + NY)
    """
    hour = datetime.utcnow().hour
    if 12 <= hour < 16:
        return "overlap"
    if 7 <= hour < 16:
        return "london"
    if 12 <= hour < 21:
        return "newyork"
    return "asian"


def day_of_week() -> str:
    return datetime.utcnow().strftime("%A")
