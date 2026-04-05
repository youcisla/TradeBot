"""heartbeat.py — periodic liveness signal writer.

Writes a small JSON file ``state/heartbeat.json`` every ``interval_seconds``
seconds. The dashboard and external monitoring tools can check this file to
detect bot crashes or freezes.

Usage::

    from state.heartbeat import Heartbeat

    hb = Heartbeat()
    hb.start()          # launches background thread
    hb.ping()           # call from hot path to update activity timestamp
    hb.stop()
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

_STATE_DIR = Path(__file__).resolve().parent.parent / "state"
_HB_FILE = _STATE_DIR / "heartbeat.json"


class Heartbeat:
    """Writes a heartbeat JSON file on a fixed interval.

    Also exposes ``ping()`` which updates a ``last_activity`` field —
    call this from the main bot loop tick so monitoring tools can detect
    logic freezes even if the process is still alive.
    """

    def __init__(self, interval_seconds: int = 30) -> None:
        self._interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_activity: datetime = datetime.now(timezone.utc)
        self._extra: dict = {}
        _STATE_DIR.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background heartbeat writer thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="heartbeat"
        )
        self._thread.start()
        logger.info("Heartbeat started (interval=%ds)", self._interval)

    def stop(self) -> None:
        """Signal the background thread to stop."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Heartbeat stopped")

    def ping(self, **extra: object) -> None:
        """Update the last-activity timestamp and optional extra fields.

        Call this at the start of each main loop tick.
        """
        self._last_activity = datetime.now(timezone.utc)
        if extra:
            self._extra.update({k: str(v) for k, v in extra.items()})

    def write_once(self) -> None:
        """Force an immediate heartbeat write (useful for shutdown hooks)."""
        self._write()

    # ── Internal ──────────────────────────────────────────────────────────

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._write()
            self._stop_event.wait(self._interval)

    def _write(self) -> None:
        now = datetime.now(timezone.utc)
        delta_seconds = (now - self._last_activity).total_seconds()
        payload = {
            "alive_at": now.isoformat(),
            "last_activity": self._last_activity.isoformat(),
            "idle_seconds": round(delta_seconds, 1),
            "status": "ok" if delta_seconds < self._interval * 3 else "stale",
            **self._extra,
        }
        try:
            _HB_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.debug("Heartbeat write failed: %s", exc)
