#!/usr/bin/env python
"""pulse — Unified TradingBot CLI entry point.

Usage:
    python scripts/pulse.py                 # Interactive TUI (default)
    python scripts/pulse.py run            # Start bot + web, show TUI
    python scripts/pulse.py stop           # Stop all child processes
    python scripts/pulse.py status        # Quick status table
    python scripts/pulse.py logs [bot|web] # Tail logs (batch; --follow for live)
    python scripts/pulse.py clear          # Clear all caches
    python scripts/pulse.py doctor         # Run ops_doctor checks
    python scripts/pulse.py test [suite]   # Run pytest
    python scripts/pulse.py restart        # Stop + run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(ROOT))

from scripts.pulse.commands import (
    clear_cache,
    run_doctor,
    run_tests,
    show_status,
    tail_logs,
)

logger = logging.getLogger(__name__)


def _setup_logging(level: int = logging.WARNING) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def _run_tui() -> None:
    from scripts.pulse.supervisor import BotSupervisor
    from scripts.pulse.tui import PulseTUI
    from scripts.pulse.agent_feed import AgentFeed

    async def main() -> None:
        if BotSupervisor.is_running():
            print("Error: another pulse instance is already running.")
            print("Stop it first with: python scripts/pulse.py stop")
            raise SystemExit(1)

        app = PulseTUI()
        supervisor = BotSupervisor(
            bot_cwd=ROOT,
            web_cwd=ROOT / "web",
            on_output=lambda source, line: app.add_log_line(source, line),
        )

        feed = AgentFeed(
            url="http://127.0.0.1:5555/api/agent-events",
            limit=30,
            poll_interval=3.0,
        )
        feed.on_events = lambda events: app.set_feed_events(events)

        loop = asyncio.get_event_loop()

        def shutdown_handler(sig: int, frame) -> None:
            loop.call_soon(lambda: _shutdown(supervisor, feed))

        old_sigint = signal.signal(signal.SIGINT, shutdown_handler)
        old_sigterm = signal.signal(signal.SIGTERM, shutdown_handler)

        try:
            await feed.start()
            await supervisor.start()
            app.set_bot_status("running")
            app.set_web_status("running")
            await app.run_async()
        finally:
            signal.signal(signal.SIGINT, old_sigint)
            signal.signal(signal.SIGTERM, old_sigterm)
            await _shutdown(supervisor, feed)

    async def _shutdown(sup: BotSupervisor, feed: AgentFeed) -> None:
        feed.stop()
        await sup.stop()

    asyncio.run(main())


def _cmd_run() -> int:
    _setup_logging(logging.WARNING)
    _run_tui()
    return 0


def _cmd_stop() -> int:
    from scripts.pulse.supervisor import BotSupervisor, PID_FILE

    if not PID_FILE.exists():
        print("No pulse instance appears to be running.")
        return 1
    try:
        with open(PID_FILE, "r") as f:
            pid = int(f.read().strip())
        import subprocess
        result = subprocess.run(
            ["taskkill", "/F", "/PID", str(pid)],
            capture_output=True, text=True,
        )
        print(f"Sent termination to pid={pid}" + (" (not found — stale pid)" if result.returncode != 0 else ""))
        if result.returncode == 0:
            PID_FILE.unlink()
    except Exception as e:
        print(f"Error stopping pulse: {e}")
        return 1
    return 0


def _cmd_restart() -> int:
    if BotSupervisor.is_running():
        _cmd_stop()
        import time; time.sleep(1)
    return _cmd_run()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="pulse — Unified TradingBot CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="command", required=False)

    sub.add_parser("run", help="Start bot + web, show TUI")
    sub.add_parser("stop", help="Stop running pulse instance")
    sub.add_parser("status", help="Show bot status from heartbeat")
    sub.add_parser("doctor", help="Run ops_doctor checks")
    sub.add_parser("clear", help="Clear all caches")
    sub.add_parser("restart", help="Stop and restart bot + web")

    logs_parser = sub.add_parser("logs", help="Tail bot logs")
    logs_parser.add_argument("source", nargs="?", default="all", choices=["all", "bot", "web"])
    logs_parser.add_argument("--lines", "-n", type=int, default=100)
    logs_parser.add_argument("--follow", "-f", action="store_true")

    test_parser = sub.add_parser("test", help="Run tests")
    test_parser.add_argument("suite", nargs="?", default=None)
    test_parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()

    match args.command or "run":
        case "run":
            return _cmd_run()
        case "stop":
            return _cmd_stop()
        case "status":
            return show_status()
        case "logs":
            return tail_logs(source=args.source, lines=args.lines, follow=args.follow)
        case "clear":
            return clear_cache()
        case "doctor":
            return run_doctor()
        case "test":
            return run_tests(suite=args.suite, verbose=args.verbose)
        case "restart":
            return _cmd_restart()
        case _:
            return _cmd_run()


if __name__ == "__main__":
    raise SystemExit(main())
