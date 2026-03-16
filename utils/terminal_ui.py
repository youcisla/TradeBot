"""Rich-based live terminal dashboard for the trading bot.

Usage
-----
    from utils.terminal_ui import TerminalUI
    ui = TerminalUI()
    ui.start()                        # begin rendering in background thread
    ui.set_agent_status("market", "scanning EURUSD…")
    ui.add_event("execution", "info", "LONG EURUSD opened @ 1.08542")
    ui.set_trade(trade_obj)
    ui.stop()                         # call on shutdown

The dashboard shows four panels:

  ┌─ Bot Status ──────────────────────────────┐
  │ state / equity / balance / open trades    │
  └───────────────────────────────────────────┘
  ┌─ Agents ──────────────────────────────────┐
  │ spinner  agent name   last message        │
  └───────────────────────────────────────────┘
  ┌─ Open Trades ─────────────────────────────┐
  │ symbol  direction  lots  entry  pnl  TP   │
  └───────────────────────────────────────────┘
  ┌─ Recent Events ───────────────────────────┐
  │ ts  agent  level  message                 │
  └───────────────────────────────────────────┘
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, UTC
from typing import TYPE_CHECKING

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text
from rich import box

if TYPE_CHECKING:
    from models.trade import Trade

# ── Colour palette ──────────────────────────────────────────────────────────
_LEVEL_COLOUR = {
    "info":  "bright_white",
    "warn":  "yellow",
    "error": "red",
    "debug": "dim white",
}

_AGENT_COLOUR = {
    "market":    "cyan",
    "analysis":  "blue",
    "strategy":  "magenta",
    "risk":      "yellow",
    "execution": "green",
    "trade_mgr": "bright_green",
    "learning":  "bright_blue",
    "logging":   "dim white",
}

_AGENT_NAMES = [
    "market", "analysis", "strategy", "risk",
    "execution", "trade_mgr", "learning", "logging",
]

_SPINNER_STYLES = ["dots", "dots2", "line", "bouncingBar", "arc", "aesthetic"]


class TerminalUI:
    """Thread-safe live terminal dashboard."""

    def __init__(self, refresh_per_second: int = 4, max_events: int = 20) -> None:
        self._refresh = refresh_per_second
        self._lock = threading.Lock()
        self._console = Console()
        self._live: Live | None = None
        self._thread: threading.Thread | None = None
        self._running = False

        # State
        self._bot_state = "STARTING"
        self._equity: float = 0.0
        self._balance: float = 0.0
        self._daily_pnl: float = 0.0
        self._open_trade_count: int = 0

        # Per-agent: (status_msg, is_active, spinner_style_idx)
        self._agent_status: dict[str, tuple[str, bool]] = {
            name: ("idle", False) for name in _AGENT_NAMES
        }
        self._agent_spinner_frame: dict[str, int] = {name: 0 for name in _AGENT_NAMES}

        # Open trades: dict keyed by trade_id
        self._trades: dict[str, "Trade"] = {}

        # Recent events ring-buffer
        self._events: deque[dict] = deque(maxlen=max_events)

    # ── Public API ───────────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the Live render in a daemon background thread."""
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="TerminalUI")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

    def set_bot_status(
        self,
        state: str,
        equity: float = 0.0,
        balance: float = 0.0,
        daily_pnl: float = 0.0,
        open_trades: int = 0,
    ) -> None:
        with self._lock:
            self._bot_state = state
            self._equity = equity
            self._balance = balance
            self._daily_pnl = daily_pnl
            self._open_trade_count = open_trades

    def set_agent_status(self, agent: str, message: str, active: bool = True) -> None:
        """Update a single agent's status line."""
        with self._lock:
            self._agent_status[agent] = (message, active)

    def set_agent_idle(self, agent: str) -> None:
        with self._lock:
            self._agent_status[agent] = ("idle", False)

    def add_event(self, agent: str, level: str, message: str) -> None:
        with self._lock:
            self._events.appendleft({
                "ts": datetime.now(UTC).strftime("%H:%M:%S"),
                "agent": agent,
                "level": level,
                "msg": message,
            })

    def set_trade(self, trade: "Trade") -> None:
        with self._lock:
            if trade.is_open():
                self._trades[trade.id] = trade
            else:
                self._trades.pop(trade.id, None)

    def remove_trade(self, trade_id: str) -> None:
        with self._lock:
            self._trades.pop(trade_id, None)

    # ── Rendering ────────────────────────────────────────────────────────────

    def _run(self) -> None:
        with Live(
            self._build_layout(),
            console=self._console,
            refresh_per_second=self._refresh,
            screen=True,
        ) as live:
            self._live = live
            while self._running:
                live.update(self._build_layout())
                threading.Event().wait(1 / self._refresh)

    def _build_layout(self) -> Layout:
        with self._lock:
            bot_panel   = self._bot_status_panel()
            agent_panel = self._agent_panel()
            trade_panel = self._trade_panel()
            event_panel = self._event_panel()

        layout = Layout()
        layout.split_column(
            Layout(bot_panel,   name="status", size=5),
            Layout(name="mid"),
            Layout(event_panel, name="events", size=min(len(self._events) + 4, 14)),
        )
        layout["mid"].split_row(
            Layout(agent_panel, name="agents"),
            Layout(trade_panel, name="trades"),
        )
        return layout

    # ── Panels ───────────────────────────────────────────────────────────────

    def _bot_status_panel(self) -> Panel:
        state_colour = {
            "RUNNING": "bright_green",
            "STARTING": "yellow",
            "COOLDOWN": "yellow",
            "STOPPED": "red",
            "ERROR": "red",
        }.get(self._bot_state, "white")

        pnl_colour = "green" if self._daily_pnl >= 0 else "red"
        pnl_sign   = "+" if self._daily_pnl >= 0 else ""

        row = Text()
        row.append("  State: ")
        row.append(self._bot_state, style=f"bold {state_colour}")
        row.append("   │   Equity: ")
        row.append(f"${self._equity:,.2f}", style="bold cyan")
        row.append("   Balance: ")
        row.append(f"${self._balance:,.2f}", style="cyan")
        row.append("   Daily P&L: ")
        row.append(f"{pnl_sign}${self._daily_pnl:,.2f}", style=f"bold {pnl_colour}")
        row.append("   Open Trades: ")
        row.append(str(self._open_trade_count), style="bold magenta")

        return Panel(row, title="[bold]Trading Bot[/bold]", border_style="bright_blue")

    def _agent_panel(self) -> Panel:
        table = Table(box=box.SIMPLE, show_header=False, expand=True, padding=(0, 1))
        table.add_column("icon",  width=3)
        table.add_column("name",  width=10)
        table.add_column("msg",   overflow="fold")

        for name in _AGENT_NAMES:
            msg, active = self._agent_status[name]
            colour = _AGENT_COLOUR.get(name, "white")

            if active:
                # rotating Braille spinner character
                frame = self._agent_spinner_frame[name]
                braille = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
                icon = Text(braille[frame % len(braille)], style=f"bold {colour}")
                self._agent_spinner_frame[name] = (frame + 1) % len(braille)
            else:
                icon = Text("·", style="dim")

            table.add_row(
                icon,
                Text(name, style=colour),
                Text(msg, style="dim" if not active else "white", overflow="fold"),
            )

        return Panel(table, title="[bold]Agents[/bold]", border_style="blue")

    def _trade_panel(self) -> Panel:
        table = Table(box=box.SIMPLE_HEAD, expand=True)
        table.add_column("Symbol",    style="cyan",         no_wrap=True)
        table.add_column("Dir",       style="white",        no_wrap=True)
        table.add_column("Lots",      style="white",        justify="right")
        table.add_column("Entry",     style="dim white",    justify="right")
        table.add_column("P&L",       justify="right")
        table.add_column("Stage",     style="dim white")

        trades = list(self._trades.values())
        if not trades:
            table.add_row("—", "", "", "", "", "no open trades")
        else:
            for t in trades:
                pnl = getattr(t, "pnl", 0.0) or 0.0
                pnl_style = "green" if pnl >= 0 else "red"
                pnl_sign  = "+" if pnl >= 0 else ""

                stage = "entry"
                if getattr(t, "tp1_hit", False) and getattr(t, "tp2_hit", False):
                    stage = "TP2 → trailing"
                elif getattr(t, "tp1_hit", False):
                    stage = "TP1 → BE SL"

                dir_style = "bright_green" if t.direction == "BUY" else "red"
                table.add_row(
                    t.symbol,
                    Text(t.direction, style=dir_style),
                    f"{t.lot_size:.2f}",
                    f"{t.entry_price:.5f}",
                    Text(f"{pnl_sign}${pnl:.2f}", style=pnl_style),
                    stage,
                )

        return Panel(table, title="[bold]Open Trades[/bold]", border_style="green")

    def _event_panel(self) -> Panel:
        table = Table(box=box.SIMPLE, show_header=False, expand=True, padding=(0, 1))
        table.add_column("ts",    width=8,  style="dim")
        table.add_column("agent", width=10)
        table.add_column("msg",   overflow="fold")

        for ev in list(self._events):
            colour  = _AGENT_COLOUR.get(ev["agent"], "white")
            lvl_col = _LEVEL_COLOUR.get(ev["level"], "white")
            agent_t = Text(ev["agent"], style=colour)
            msg_t   = Text(ev["msg"],   style=lvl_col)
            table.add_row(ev["ts"], agent_t, msg_t)

        return Panel(table, title="[bold]Recent Events[/bold]", border_style="dim blue")


# ── Module-level singleton (optional convenience) ────────────────────────────
_ui: TerminalUI | None = None


def get_ui() -> TerminalUI | None:
    return _ui


def init(refresh_per_second: int = 4) -> TerminalUI:
    """Create and start the module-level singleton."""
    global _ui
    _ui = TerminalUI(refresh_per_second=refresh_per_second)
    _ui.start()
    return _ui
