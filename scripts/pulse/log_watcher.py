"""Async log tailer for bot log files using watchfiles."""

from __future__ import annotations

import asyncio
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Awaitable

logger = logging.getLogger(__name__)

# ── Bot log level color/style mapping ────────────────────────────────────
_LEVEL_STYLES: dict[str, str] = {
    "DEBUG":    "dim white",
    "INFO":     "white",
    "WARNING":  "yellow",
    "WARN":     "yellow",
    "ERROR":    "red bold",
    "CRITICAL": "red bold reverse",
}

# Paris timezone for displaying timestamps
_PARIS_TZ = None  # filled lazily on first call


def _format_paris(ts: datetime) -> str:
    """Format datetime in Paris timezone."""
    return ts.strftime("%H:%M:%S")


class LogWatcher:
    """Async log file watcher that yields new lines as they appear."""

    def __init__(
        self,
        log_dir: Path | str = "logs",
        source_label: str = "BOT",
        color: str = "cyan",
        on_line: Callable[[str, str], None] | None = None,
    ) -> None:
        self.log_dir = Path(log_dir)
        self.source_label = source_label
        self.color = color
        self.on_line = on_line
        self._lines: list[str] = []
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._current_offset = 0

    @property
    def lines(self) -> list[str]:
        return self._lines

    async def _get_latest_log_path(self) -> Path | None:
        """Find the most recent backend log file (backend_YYYY-MM-DD.log)."""
        backend_dir = self.log_dir / "backend"
        if not backend_dir.exists():
            return None
        files = sorted(backend_dir.glob("backend_*.log"), key=lambda p: p.stat().st_mtime)
        if not files:
            return None
        return files[-1]

    async def _read_new_lines(self, path: Path) -> list[str]:
        """Read only the new lines since last read."""
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._current_offset)
                new_lines = f.readlines()
                self._current_offset = f.tell()
            return [line.rstrip("\n\r") for line in new_lines if line.strip()]
        except OSError:
            return []

    async def watch(self, latest_only: bool = False) -> None:
        """Watch the log file and accumulate lines."""
        self._running = True

        while self._running:
            try:
                if latest_only:
                    path = await self._get_latest_log_path()
                    if path:
                        self._current_offset = 0  # Reset to read from start
                        new_lines = await self._read_new_lines(path)
                        if new_lines:
                            for line in new_lines:
                                self._lines.append(line)
                                if len(self._lines) > 5000:
                                    self._lines.pop(0)
                        if not self._lines:
                            await asyncio.sleep(1)
                            continue
                        return
                    await asyncio.sleep(1)
                    continue

                path = await self._get_latest_log_path()
                if not path:
                    await asyncio.sleep(1)
                    continue

                new_lines = await self._read_new_lines(path)
                for line in new_lines:
                    self._lines.append(line)
                    if len(self._lines) > 5000:
                        self._lines.pop(0)

                await asyncio.sleep(0.5)
            except Exception:
                await asyncio.sleep(1)

    async def watch_follow(self, latest_only: bool = False) -> None:
        """Watch and call on_line for each new line (follow mode)."""
        self._running = True

        while self._running:
            try:
                path = await self._get_latest_log_path()
                if not path:
                    await asyncio.sleep(1)
                    continue

                if latest_only:
                    self._current_offset = 0

                while self._running:
                    new_lines = await self._read_new_lines(path)
                    for line in new_lines:
                        self._lines.append(line)
                        if len(self._lines) > 5000:
                            self._lines.pop(0)
                        if self.on_line:
                            self.on_line(self.source_label, line)
                    await asyncio.sleep(0.3)
            except Exception:
                await asyncio.sleep(1)

    def stop(self) -> None:
        self._running = False


async def tail_logs(
    source: str = "all",
    lines: int = 100,
    follow: bool = False,
    log_dir: Path | str = "logs",
    web_log: bool = False,
    console: Console | None = None,
) -> None:
    """Tail logs from bot (and optionally web)."""
    _console = console or Console()
    _log_dir = Path(log_dir)

    if not follow:
        # Batch mode: read last N lines and exit
        paths = []
        if source in ("all", "bot"):
            backend_files = sorted((_log_dir / "backend").glob("backend_*.log"), key=lambda p: p.stat().st_mtime)
            paths.extend(backend_files)
        if web_log and source in ("all", "web"):
            web_log_path = _log_dir / "frontend" / "dev_server.log"
            if web_log_path.exists():
                paths.append(web_log_path)

        for path in paths:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()
                recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
                label = "BACKEND" if "backend_" in path.name else "WEB"
                for line in recent:
                    _console.print(
                        f"[bold {LOG_SOURCE_COLORS.get(label, 'white')}]{label}[/bold {LOG_SOURCE_COLORS.get(label, 'white')}]  {line.rstrip()}"
                    )
            except OSError:
                pass
        return

    # Follow mode: start watchers and run forever
    watchers: list[LogWatcher] = []

    if source in ("all", "bot"):
        w = LogWatcher(log_dir=_log_dir, source_label="BOT", color="cyan")
        watchers.append(w)

    loop = asyncio.get_event_loop()
    for w in watchers:
        w._task = loop.create_task(w.watch_follow(latest_only=True))

    try:
        await asyncio.Event().wait()
    except asyncio.CancelledError:
        for w in watchers:
            w.stop()
        raise


# Source colors for CLI output
LOG_SOURCE_COLORS: dict[str, str] = {
    "BOT": "cyan",
    "WEB": "green",
    "ERR": "red",
}


def colorize_line(line: str, source: str = "BOT") -> Text:
    """Parse a bot log line and apply level-based colorizing."""
    # Bot log format: "2026-04-09 18:09:01 +02:00 [LEVEL] message"
    level_match = re.search(r"\[(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL)\]", line)
    level = level_match.group(1) if level_match else "INFO"
    style = _LEVEL_STYLES.get(level, "white")
    return Text(f"[{source}] {line}", style=style)


async def watch_bot_logs(
    log_dir: Path | str = "logs",
    on_line: Callable[[str, str], Awaitable[None]] | None = None,
) -> LogWatcher:
    """Start a log watcher and return it for use in a Textual app."""
    watcher = LogWatcher(
        log_dir=log_dir,
        source_label="BOT",
        color="cyan",
        on_line=None,  # We'll handle callbacks ourselves
    )
    loop = asyncio.get_event_loop()
    watcher._task = loop.create_task(watcher.watch_follow(latest_only=True))
    return watcher
