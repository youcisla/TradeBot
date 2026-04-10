"""Non-interactive CLI commands for pulse (logs, clear, doctor, test, status)."""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

logger = logging.getLogger(__name__)

ROOT = Path(__file__).parent.parent.parent.resolve()
STATE_DIR = ROOT / "state"
LOGS_DIR = ROOT / "logs"
DATA_DIR = ROOT / "data"
WEB_DIR = ROOT / "web"

import sys
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

console = Console()


# ── Status ──────────────────────────────────────────────────────────────

def show_status() -> int:
    """Show bot state, uptime, KPIs from heartbeat.json."""
    hb_path = STATE_DIR / "heartbeat.json"
    if not hb_path.exists():
        console.print("[yellow]No heartbeat file — bot may not be running[/yellow]")
        return 1

    try:
        with open(hb_path, "r") as f:
            hb = json.load(f)
    except Exception as e:
        console.print(f"[red]Failed to read heartbeat: {e}[/red]")
        return 1

    table = Table(title="Bot Status", show_header=False, box=None)
    table.add_column("Key", style="bold dim")
    table.add_column("Value")

    state = hb.get("state", "—")
    state_color = "green" if state == "running" else "yellow" if state == "warning" else "red"
    table.add_row("State", f"[{state_color}]{state}[/{state_color}]")
    table.add_row("Equity", f"${hb.get('equity', 0):,.2f}")
    table.add_row("Balance", f"${hb.get('balance', 0):,.2f}")
    table.add_row("Daily P&L", f"${hb.get('daily_pnl', 0):,.2f}")
    table.add_row("Open Trades", str(hb.get("open_trades", 0)))

    # Uptime
    start_iso = hb.get("start_time")
    if start_iso:
        try:
            start = datetime.fromisoformat(start_iso)
            uptime_s = (datetime.now(timezone.utc) - start).total_seconds()
            h = int(uptime_s // 3600)
            m = int((uptime_s % 3600) // 60)
            s = int(uptime_s % 60)
            table.add_row("Uptime", f"{h:02d}:{m:02d}:{s:02d}")
        except Exception:
            pass
    else:
        table.add_row("Uptime", "—")

    table.add_row("Last Tick", hb.get("last_tick", "—"))
    console.print(table)

    # Log file check
    log_files = sorted(LOGS_DIR.glob("bot_*.log"), key=lambda p: p.stat().st_mtime)
    if log_files:
        latest = log_files[-1]
        age_m = (datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)).total_seconds() / 60
        console.print(f"\n[dim]Latest log: {latest.name} ({age_m:.1f}m ago)[/dim]")

    return 0


# ── Log tailing ──────────────────────────────────────────────────────────

def tail_logs(
    source: str = "all",
    lines: int = 100,
    follow: bool = False,
    log_dir: Path | str | None = None,
) -> int:
    """Tail bot (and optionally web) logs to console."""
    _log_dir = Path(log_dir) if log_dir else LOGS_DIR

    if not _log_dir.exists():
        console.print(f"[red]Log directory not found: {_log_dir}[/red]")
        return 1

    if follow:
        console.print("[cyan]Following logs... Ctrl+C to stop[/cyan]\n")
        try:
            asyncio.run(_tail_follow(source, lines, _log_dir))
        except KeyboardInterrupt:
            console.print("\n[dim]Stopped.[/dim]")
        return 0

    # Batch mode: show last N lines and exit
    from scripts.pulse.log_watcher import LOG_SOURCE_COLORS

    paths_by_source = {}
    if source in ("all", "bot"):
        bot_files = sorted(_log_dir.glob("bot_*.log"), key=lambda p: p.stat().st_mtime)
        if bot_files:
            paths_by_source["BOT"] = bot_files[-1]

    for label, path in paths_by_source.items():
        color = LOG_SOURCE_COLORS.get(label, "white")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
            console.print(f"[bold {color}]{label}[/bold {color}]: {path.name}\n")
            for line in recent:
                console.print(f"[{color}]{line.rstrip()}[/{color}]")
        except OSError as e:
            console.print(f"[red]Error reading {path}: {e}[/red]")
    return 0


async def _tail_follow(source: str, lines: int, log_dir: Path) -> None:
    """Async follow mode using watchfiles."""
    import watchfiles

    async def on_change(changes: list[tuple[str, str, int]]) -> None:
        for op, path_str, _ in changes:
            if op != "modified":
                continue
            path = Path(path_str)
            if source == "web" and "npm" not in path.name:
                continue
            if source == "bot" and "bot_" not in path.name:
                continue
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(max(0, path.stat().st_size - 4096))
                    new_lines = f.readlines()
                for line in new_lines[-lines:]:
                    label = "WEB" if "npm" in path.name else "BOT"
                    color = LOG_SOURCE_COLORS.get(label, "white")
                    console.print(f"[{color}]{line.rstrip()}[/{color}]")
            except OSError:
                pass

    async for changes in watchfiles.awatch(str(log_dir), stop_asyncio=True):
        await on_change(changes)


# ── Clear cache ─────────────────────────────────────────────────────────

def clear_cache() -> int:
    """Clear all caches: web/.next, __pycache__, .pytest_cache, logs/, data/history/."""
    targets = [
        (WEB_DIR / ".next", ".next/"),
        (ROOT / "__pycache__", "__pycache__/"),
        (ROOT / ".pytest_cache", ".pytest_cache/"),
        (LOGS_DIR, "logs/"),
        (DATA_DIR / "history", "data/history/"),
    ]

    table = Table(title="Clear Cache", show_header=False, box=None)
    table.add_column("Target", style="dim")
    table.add_column("Status", style="bold")

    all_ok = True
    for path, label in targets:
        if path.is_dir():
            shutil.rmtree(path)
            table.add_row(label, "[green]removed[/green]")
        elif path.is_file():
            path.unlink()
            table.add_row(label, "[green]removed[/green]")
        else:
            table.add_row(label, "[dim]not found — skipped[/dim]")

    console.print(table)
    console.print("\n[green]Cache cleared successfully.[/green]")
    return 0


# ── Doctor ──────────────────────────────────────────────────────────────

def run_doctor() -> int:
    """Run ops_doctor checks and display results as a rich table."""
    sys.path.insert(0, str(ROOT))
    from utils.ops_doctor import run_doctor as _run_doctor, DoctorReport

    report: DoctorReport = _run_doctor(ROOT)

    table = Table(title="Ops Doctor", show_header=True)
    table.add_column("Check", style="bold")
    table.add_column("Status")
    table.add_column("Detail", style="dim")

    all_pass = True
    for check in report.checks:
        status = check.status  # "ok" | "warn" | "fail"
        detail = check.detail
        name = check.name
        if status == "ok":
            table.add_row(name, "[green]PASS[/green]", detail)
        elif status == "fail":
            table.add_row(name, "[red]FAIL[/red]", detail)
            all_pass = False
        else:
            table.add_row(name, f"[yellow]WARN[/yellow]", detail)

    console.print(table)
    if report.recommendations:
        console.print("\n[bold]Recommendations[/bold]")
        for rec in report.recommendations:
            console.print(f"  • {rec}")
    return 0 if all_pass else 1


# ── Test ───────────────────────────────────────────────────────────────

def run_tests(
    suite: str | None = None,
    verbose: bool = False,
) -> int:
    """Run pytest with rich output."""
    console.print("[cyan]Running tests...[/cyan]\n")

    if suite == "web":
        console.print("[yellow]Web TypeScript check not yet implemented[/yellow]")
        return 0

    args = ["-m", "pytest"]
    if not verbose:
        args.extend(["--tb=no", "-q"])
    else:
        args.extend(["-v", "--tb=short"])
    args.append(f"tests/{suite}" if suite else "tests/")

    result = subprocess.run(
        args,
        cwd=str(ROOT),
        env={**subprocess.os.environ, "PYTHONUNBUFFERED": "1"},
    )
    return result.returncode


# ── Status helper ───────────────────────────────────────────────────────

LOG_SOURCE_COLORS = {
    "BOT": "cyan",
    "WEB": "green",
    "ERR": "red",
}
