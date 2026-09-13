"""Always-on supervisor for the trading bot.

Runs the bot as a child process and keeps it running:

* restarts on crash, with exponential backoff, so a fast crash-loop cannot
  hammer the broker or burn the API budget;
* watches the heartbeat file the bot writes and restarts it when the process is
  alive but has stopped iterating — a hang is worse than a crash, because the
  process looks healthy while no stop is being managed;
* stops for good when the kill-switch file appears;
* gives up after too many restarts inside a window, because a bot that cannot
  stay up for minutes is not a bot, it is a bug with a loop around it.

The bot runs as a **subprocess**, never in-process: a crash, a segfault or a
memory blow-up inside the bot must not be able to take the supervisor with it.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class SupervisorConfig:
    command: list[str] = field(default_factory=lambda: [sys.executable, "main.py"])
    cwd: Path = field(default_factory=Path.cwd)
    heartbeat_path: Path = field(default_factory=lambda: Path("state") / "heartbeat.json")
    kill_switch_path: Path = field(default_factory=lambda: Path("state") / "STOP")
    stale_after_s: float = 300.0        # heartbeat older than this = hung
    min_uptime_s: float = 30.0          # restarts faster than this count as a loop
    max_restarts_per_hour: int = 6
    base_backoff_s: float = 5.0
    max_backoff_s: float = 300.0
    poll_interval_s: float = 5.0


class Supervisor:
    """Keeps one bot process alive."""

    def __init__(self, config: SupervisorConfig | None = None) -> None:
        self.cfg = config or SupervisorConfig()
        self._proc: subprocess.Popen | None = None
        self._restarts: list[float] = []       # monotonic timestamps
        self._started_at: float = 0.0

    # ── signals from the outside world ───────────────────────────────────────

    def kill_requested(self) -> bool:
        """True once the kill-switch file exists.  Presence is the whole signal."""
        return self.cfg.kill_switch_path.exists()

    def heartbeat_age(self) -> float | None:
        """Seconds since the bot last wrote its heartbeat, or None if never."""
        path = self.cfg.heartbeat_path
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            ts = data.get("ts")
            if not ts:
                return None
            written = datetime.fromisoformat(str(ts))
            if written.tzinfo is None:
                written = written.replace(tzinfo=UTC)
            return (datetime.now(UTC) - written).total_seconds()
        except Exception as exc:                           # noqa: BLE001
            logger.warning("Supervisor: heartbeat unreadable (%s)", exc)
            return None

    def is_hung(self) -> bool:
        age = self.heartbeat_age()
        return age is not None and age > self.cfg.stale_after_s

    # ── restarts ─────────────────────────────────────────────────────────────

    def _record_restart(self) -> None:
        now = time.monotonic()
        self._restarts.append(now)
        self._restarts = [t for t in self._restarts if now - t <= 3600.0]

    def restart_budget_exhausted(self) -> bool:
        return len(self._restarts) >= self.cfg.max_restarts_per_hour

    def backoff_seconds(self) -> float:
        """Exponential backoff, reset by a healthy run."""
        streak = len(self._restarts)
        if streak == 0:
            return 0.0
        return min(self.cfg.base_backoff_s * (2 ** (streak - 1)), self.cfg.max_backoff_s)

    # ── process control ──────────────────────────────────────────────────────

    def start(self) -> None:
        self._proc = subprocess.Popen(  # noqa: S603
            self.cfg.command,
            cwd=str(self.cfg.cwd),
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        self._started_at = time.monotonic()
        logger.info("Supervisor: started pid=%s", self._proc.pid)

    def stop(self, *, graceful: bool = True) -> None:
        if self._proc is None or self._proc.poll() is not None:
            self._proc = None
            return
        logger.info("Supervisor: stopping pid=%s", self._proc.pid)
        try:
            if graceful:
                self._proc.terminate()
                try:
                    self._proc.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    logger.warning("Supervisor: graceful stop timed out — killing")
                    self._proc.kill()
                    self._proc.wait(timeout=10)
            else:
                self._proc.kill()
                self._proc.wait(timeout=10)
        except Exception as exc:                           # noqa: BLE001
            logger.error("Supervisor: error stopping child (%s)", exc)
        finally:
            self._proc = None

    def uptime(self) -> float:
        return time.monotonic() - self._started_at if self._proc else 0.0

    # ── main loop ────────────────────────────────────────────────────────────

    def run(self) -> int:
        """Supervise until the kill switch appears or the restart budget runs out."""
        from autonomy.edge_gate import live_trading_allowed

        allowed, reason = live_trading_allowed()
        if not allowed:
            logger.error("Supervisor: live trading refused by edge gate — %s", reason)
            return 3

        while True:
            if self.kill_requested():
                logger.warning("Supervisor: kill switch present — shutting down")
                self.stop(graceful=True)
                return 0

            self.start()

            # ── monitor this run ────────────────────────────────────────────
            while True:
                if self.kill_requested():
                    logger.warning("Supervisor: kill switch present — shutting down")
                    self.stop(graceful=True)
                    return 0

                code = self._proc.poll() if self._proc else 0
                if code is not None:
                    logger.error("Supervisor: child exited with code %s", code)
                    break

                if self.is_hung():
                    age = self.heartbeat_age()
                    logger.error(
                        "Supervisor: heartbeat stale (%.0fs > %.0fs) — child is hung, "
                        "restarting it",
                        age if age is not None else -1.0,
                        self.cfg.stale_after_s,
                    )
                    self.stop(graceful=False)
                    break

                time.sleep(self.cfg.poll_interval_s)

            ran_for = self.uptime()
            if ran_for >= self.cfg.min_uptime_s:
                # A genuinely healthy run clears the crash streak, so a bot that
                # crashes after an hour is not treated like one crashing in a loop.
                self._restarts.clear()

            self._record_restart()
            if self.restart_budget_exhausted():
                logger.critical(
                    "Supervisor: %d restarts within an hour — giving up rather than "
                    "crash-looping. Inspect logs, then remove state/STOP to resume.",
                    self.cfg.max_restarts_per_hour,
                )
                return 4

            wait = self.backoff_seconds()
            if wait:
                logger.info("Supervisor: backoff %.1fs before restart", wait)
                deadline = time.monotonic() + wait
                while time.monotonic() < deadline:
                    if self.kill_requested():
                        logger.warning("Supervisor: kill switch present — shutting down")
                        return 0
                    time.sleep(min(1.0, max(0.0, deadline - time.monotonic())))


def _self_check() -> None:
    """Runnable check for the two decisions that matter: hung, and backoff."""
    cfg = SupervisorConfig(
        heartbeat_path=Path("nonexistent-heartbeat.json"),
        kill_switch_path=Path("nonexistent-stop-flag"),
        stale_after_s=10.0,
        base_backoff_s=5.0,
        max_backoff_s=60.0,
        max_restarts_per_hour=3,
    )
    sup = Supervisor(cfg)

    # No heartbeat file yet — not hung (the bot may simply not have started).
    assert sup.heartbeat_age() is None
    assert sup.is_hung() is False
    assert sup.kill_requested() is False

    # Backoff: none before any restart, then exponential, capped.
    assert sup.backoff_seconds() == 0.0
    sup._record_restart()
    assert sup.backoff_seconds() == 5.0
    sup._record_restart()
    assert sup.backoff_seconds() == 10.0
    sup._record_restart()
    assert sup.backoff_seconds() == 20.0
    assert sup.restart_budget_exhausted() is True, "3 restarts should hit a budget of 3"

    # The streak is cleared by a healthy run, so a late crash is not a loop.
    sup._restarts.clear()
    assert sup.restart_budget_exhausted() is False
    assert sup.backoff_seconds() == 0.0

    print("supervisor.py self-check: OK")


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-7s %(message)s",
        datefmt="%H:%M:%S",
    )
    _self_check()
