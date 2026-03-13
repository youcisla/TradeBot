"""Session Engine — session detection, killzones, ICT macro windows.

All times are UTC.  The broker (MetaTrader) provides UTC candle timestamps.

Sessions (UTC):
  Asian     : 00:00 – 08:00
  London    : 07:00 – 16:00
  New York  : 12:00 – 21:00
  Overlap   : 12:00 – 16:00  (London ∩ NY)

Killzones (UTC):
  Asian KZ  : 00:00 – 04:00
  London KZ : 07:00 – 10:00
  NY KZ     : 12:00 – 15:00

ICT Macro Windows (UTC):
  London Open  : 07:33 – 08:03
  NY AM        : 13:50 – 14:10
  NY Lunch     : 16:10 – 16:40
  NY PM        : 19:15 – 19:45
"""

from __future__ import annotations

from datetime import datetime, timezone
from models.market_data import Candle
from models.ict_models import SessionName, SessionInfo


# ── Session boundaries (hour, minute) in UTC ─────────────────────────────

_SESSIONS = {
    SessionName.ASIAN:    ((0, 0), (8, 0)),
    SessionName.LONDON:   ((7, 0), (16, 0)),
    SessionName.NEW_YORK: ((12, 0), (21, 0)),
    SessionName.OVERLAP:  ((12, 0), (16, 0)),
}

_KILLZONES = {
    SessionName.ASIAN:    ((0, 0), (4, 0)),
    SessionName.LONDON:   ((7, 0), (10, 0)),
    SessionName.NEW_YORK: ((12, 0), (15, 0)),
}

_MACROS = {
    "london_open": ((7, 33), (8, 3)),
    "ny_am":       ((13, 50), (14, 10)),
    "ny_lunch":    ((16, 10), (16, 40)),
    "ny_pm":       ((19, 15), (19, 45)),
}


def _hm(ts: datetime) -> int:
    """Convert a timestamp to minutes since midnight UTC."""
    return ts.hour * 60 + ts.minute


def _in_window(ts: datetime, start: tuple[int, int], end: tuple[int, int]) -> bool:
    m = _hm(ts)
    s = start[0] * 60 + start[1]
    e = end[0] * 60 + end[1]
    if s <= e:
        return s <= m < e
    # Wraps midnight (not currently needed but safe)
    return m >= s or m < e


def detect_session(ts: datetime) -> SessionName:
    """Return the current session for a UTC timestamp."""
    # Check overlap first (it's a subset of both London and NY)
    if _in_window(ts, *_SESSIONS[SessionName.OVERLAP]):
        return SessionName.OVERLAP
    if _in_window(ts, *_SESSIONS[SessionName.LONDON]):
        return SessionName.LONDON
    if _in_window(ts, *_SESSIONS[SessionName.NEW_YORK]):
        return SessionName.NEW_YORK
    if _in_window(ts, *_SESSIONS[SessionName.ASIAN]):
        return SessionName.ASIAN
    return SessionName.OFF_HOURS


def detect_killzone(ts: datetime) -> bool:
    """Return True if the timestamp falls inside any killzone."""
    for start, end in _KILLZONES.values():
        if _in_window(ts, start, end):
            return True
    return False


def detect_macro(ts: datetime) -> tuple[bool, str]:
    """Return (in_macro, macro_name) for a UTC timestamp."""
    for name, (start, end) in _MACROS.items():
        if _in_window(ts, start, end):
            return True, name
    return False, ""


def compute_session_levels(
    candles: list[Candle],
    current_ts: datetime,
) -> dict:
    """Compute PDH, PDL, PWH, PWL, Asian range from candle history.

    Returns a dict with keys: pdh, pdl, pwh, pwl, asian_high, asian_low,
    session_high, session_low.
    """
    result = {
        "pdh": 0.0, "pdl": 0.0,
        "pwh": 0.0, "pwl": 0.0,
        "asian_high": 0.0, "asian_low": 0.0,
        "session_high": 0.0, "session_low": 0.0,
    }
    if not candles:
        return result

    today = current_ts.date()

    # Separate candles by date
    prev_day: list[Candle] = []
    curr_day: list[Candle] = []
    asian_today: list[Candle] = []
    session_candles: list[Candle] = []

    current_session = detect_session(current_ts)
    if current_session != SessionName.OFF_HOURS:
        sess_start, _ = _SESSIONS.get(current_session, ((0, 0), (24, 0)))

    for c in candles:
        ts = c.timestamp
        d = ts.date()
        if d == today:
            curr_day.append(c)
            # Asian range today (00:00 – 08:00 UTC)
            if 0 <= ts.hour < 8:
                asian_today.append(c)
            # Current session candles
            if current_session != SessionName.OFF_HOURS:
                if _in_window(ts, sess_start, _SESSIONS[current_session][1]):
                    session_candles.append(c)
        elif d.toordinal() == today.toordinal() - 1:
            prev_day.append(c)

    # PDH / PDL
    if prev_day:
        result["pdh"] = max(c.high for c in prev_day)
        result["pdl"] = min(c.low for c in prev_day)

    # PWH / PWL — look back up to 7 days
    week_candles = [c for c in candles
                    if (today - c.timestamp.date()).days <= 7
                    and c.timestamp.date() < today]
    if week_candles:
        result["pwh"] = max(c.high for c in week_candles)
        result["pwl"] = min(c.low for c in week_candles)

    # Asian range
    if asian_today:
        result["asian_high"] = max(c.high for c in asian_today)
        result["asian_low"] = min(c.low for c in asian_today)

    # Current session high/low
    if session_candles:
        result["session_high"] = max(c.high for c in session_candles)
        result["session_low"] = min(c.low for c in session_candles)

    return result


def build_session_info(
    candles: list[Candle],
    current_ts: datetime | None = None,
) -> SessionInfo:
    """Build a complete SessionInfo for the current point in time."""
    if current_ts is None:
        current_ts = datetime.now(timezone.utc)

    session = detect_session(current_ts)
    in_kz = detect_killzone(current_ts)
    in_macro, macro_name = detect_macro(current_ts)
    levels = compute_session_levels(candles, current_ts)

    # Quality score: killzone = 0.5 base, macro = +0.3, overlap = +0.2
    quality = 0.0
    if in_kz:
        quality += 0.5
    if in_macro:
        quality += 0.3
    if session == SessionName.OVERLAP:
        quality += 0.2
    # Off-hours penalty
    if session == SessionName.OFF_HOURS:
        quality = 0.0

    return SessionInfo(
        session=session,
        in_killzone=in_kz,
        in_macro=in_macro,
        macro_name=macro_name,
        session_high=levels["session_high"],
        session_low=levels["session_low"],
        prev_day_high=levels["pdh"],
        prev_day_low=levels["pdl"],
        prev_week_high=levels["pwh"],
        prev_week_low=levels["pwl"],
        asian_high=levels["asian_high"],
        asian_low=levels["asian_low"],
        quality_score=min(quality, 1.0),
    )
