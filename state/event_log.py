"""event_log.py — append-only structured event log for bot lifecycle events.

Each event is a single JSON line (NDJSON) written to ``logs/events.ndjson``.

Usage::

    from state.event_log import EventLog

    log = EventLog()
    log.emit("trade_opened", {"symbol": "EURUSD", "lots": 0.02})
    log.emit("guard_blocked", {"guard": "DailyDrawdownGuard", "reason": "..."})
    log.emit("model_inferred", {"model": "lgbm", "signal": "BUY", "conf": 0.73})

The log rotates daily — each day gets its own file ``logs/events_YYYY-MM-DD.ndjson``.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_LOG_DIR = Path(__file__).resolve().parent.parent / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)


class EventLog:
    """Thread-safe append-only NDJSON event log."""

    def __init__(self, log_dir: Path | None = None) -> None:
        self._dir = Path(log_dir) if log_dir else _LOG_DIR
        self._lock = threading.Lock()

    # ── Public API ────────────────────────────────────────────────────────

    def emit(self, event_type: str, payload: dict | None = None) -> None:
        """Append a structured event record to today's log file.

        Never raises — logging failures must not affect trading.
        """
        try:
            record = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "type": event_type,
                **(payload or {}),
            }
            line = json.dumps(record, default=str) + "\n"
            path = self._today_path()
            with self._lock:
                with path.open("a", encoding="utf-8") as fh:
                    fh.write(line)
        except Exception as exc:  # noqa: BLE001
            logger.debug("EventLog.emit failed silently: %s", exc)

    def tail(self, n: int = 50) -> list[dict]:
        """Return the last *n* records from today's log (for diagnostics)."""
        path = self._today_path()
        if not path.exists():
            return []
        lines: list[str] = []
        try:
            with path.open("r", encoding="utf-8") as fh:
                lines = fh.readlines()
        except Exception:  # noqa: BLE001
            return []
        records = []
        for line in lines[-n:]:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return records

    def count_today(self, event_type: str | None = None) -> int:
        """Count events recorded today, optionally filtered by type."""
        records = self.tail(n=10_000)
        if event_type is None:
            return len(records)
        return sum(1 for r in records if r.get("type") == event_type)

    # ── Internal helpers ──────────────────────────────────────────────────

    def _today_path(self) -> Path:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        return self._dir / f"events_{today}.ndjson"
