"""BotSupervisor — spawns and manages child processes (bot + web)."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

STATE_DIR = Path("state")
PID_FILE = STATE_DIR / "pulse.pid"


class BotSupervisor:
    """Manages bot and web child processes with real-time output capture."""

    def __init__(
        self,
        bot_cwd: Path | str = ".",
        web_cwd: Path | str = "web",
        on_output: Callable[[str, str], None] | None = None,
    ) -> None:
        self.bot_cwd = Path(bot_cwd)
        self.web_cwd = Path(web_cwd)
        self.on_output = on_output
        self._bot_proc: asyncio.subprocess.Process | None = None
        self._web_proc: asyncio.subprocess.Process | None = None
        self._running = False
        self._lock = asyncio.Lock()

    @property
    def running(self) -> bool:
        return self._running

    async def start(self) -> None:
        """Start both bot and web processes."""
        async with self._lock:
            self._bot_proc = await asyncio.create_subprocess_exec(
                sys.executable, "-u", "-c",
                (
                    f"import runpy, sys, os, signal;"
                    f"os.chdir({str(self.bot_cwd)!r});"
                    f"signal.signal(signal.SIGINT, signal.SIG_IGN);"
                    f"signal.signal(signal.SIGTERM, signal.SIG_IGN);"
                    f"runpy.run_module('main', run_name='__main__', alter_sys=True)"
                ),
                env={**os.environ, "PYTHONUNBUFFERED": "1"},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            self._web_proc = await asyncio.create_subprocess_exec(
                "cmd.exe", "/c", "npm", "run", "dev",
                cwd=str(self.web_cwd),
                env={**os.environ, "FORCE_COLOR": "1"},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            self._running = True
        self._write_pid()
        logger.info("BotSupervisor started (bot=%s, web=%s)", self._bot_proc.pid, self._web_proc.pid)

    async def stop(self) -> None:
        """Stop both child processes gracefully."""
        async with self._lock:
            self._running = False
            for proc in (self._bot_proc, self._web_proc):
                if proc and proc.returncode is None:
                    try:
                        proc.send_signal(signal.CTRL_C_EVENT)
                        await asyncio.wait_for(proc.wait(), timeout=5.0)
                    except asyncio.TimeoutError:
                        proc.kill()
                    except ProcessLookupError:
                        pass
            self._bot_proc = None
            self._web_proc = None
        self._remove_pid()
        logger.info("BotSupervisor stopped")

    async def stream_all(self) -> None:
        """Stream output from both processes concurrently until cancelled."""
        await asyncio.gather(
            self._stream(self._bot_proc, "BOT"),
            self._stream(self._web_proc, "WEB"),
        )

    async def _stream(self, proc: asyncio.subprocess.Process | None, source: str) -> None:
        """Read stdout from subprocess and emit through on_output callback."""
        if not proc:
            return
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                decoded = line.decode("utf-8", errors="replace").rstrip()
                if decoded.strip() and self.on_output:
                    self.on_output(source, decoded)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

    def _write_pid(self) -> None:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

    def _remove_pid(self) -> None:
        try:
            if PID_FILE.exists():
                PID_FILE.unlink()
        except OSError:
            pass

    @classmethod
    def is_running(cls) -> bool:
        """Check if a pulse instance is already running."""
        if not PID_FILE.exists():
            return False
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            import psutil
            return psutil.pid_exists(pid)
        except (ValueError, FileNotFoundError):
            cls._cleanup_stale_pid()
            return False

    @staticmethod
    def _cleanup_stale_pid() -> None:
        try:
            if PID_FILE.exists():
                PID_FILE.unlink()
        except OSError:
            pass
