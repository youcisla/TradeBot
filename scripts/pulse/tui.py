"""Textual TUI — full-screen dashboard for pulse run."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime
from typing import Callable

from rich.text import Text
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.dom import DOMNode
from textual.reactive import reactive
from textual.widgets import Header, Static

logger = logging.getLogger(__name__)

# ── Agent colors ────────────────────────────────────────────────────────
AGENT_COLORS: dict[str, str] = {
    "crucix":        "#64D2FF",
    "market":        "#32ADE6",
    "analysis":      "#636366",
    "strategy":      "#16A34A",
    "neural":        "#9333EA",
    "council":       "#D97706",
    "risk":          "#DC2626",
    "execution":     "#6B7280",
    "trade_manager": "#0EA5E9",
    "learning":      "#8B5CF6",
    "logging":       "#9CA3AF",
    "model_manager": "#6366F1",
    "debate":        "#F59E0B",
    "exposure":      "#10B981",
    "memory":        "#14B8A6",
}

_LEVEL_STYLES: dict[str, str] = {
    "DEBUG":   "dim",
    "INFO":    "",
    "WARNING": "yellow",
    "WARN":    "yellow",
    "ERROR":   "bold red",
    "CRITICAL":"bold red reverse",
}


def _agent_color(key: str) -> str:
    return AGENT_COLORS.get(key.lower(), "#9CA3AF")


def _level_style(level: str) -> str:
    return _LEVEL_STYLES.get(level.upper(), "")


# ── Widgets ─────────────────────────────────────────────────────────────

class LogLine(Static):
    def __init__(self, source: str, text: str) -> None:
        super().__init__()
        self.source = source
        self.text = text

    def render(self) -> Text:
        level_match = re.search(r"\[(DEBUG|INFO|WARNING|WARN|ERROR|CRITICAL)\]", self.text)
        level = level_match.group(1) if level_match else "INFO"
        style = _level_style(level)
        src_color = {"BOT": "cyan", "WEB": "green", "ERR": "red"}.get(self.source, "white")
        return Text(f"[{src_color}]{self.source:<4}[/{src_color}] {self.text}", style=style)


class AgentFeedEvent(Static):
    def __init__(self, agent: str, level: str, msg: str, ts: str | None) -> None:
        super().__init__()
        self.agent = agent
        self.level = level
        self.msg = msg
        self.ts = ts

    def render(self) -> Text:
        a_color = _agent_color(self.agent)
        ts_str = ""
        if self.ts:
            try:
                dt = datetime.fromisoformat(self.ts.replace("Z", "+00:00"))
                ts_str = dt.strftime("%H:%M:%S")
            except Exception:
                ts_str = self.ts[:8] if len(self.ts) > 8 else self.ts

        lvl_color = {
            "error": "red",
            "critical": "red",
            "warn": "yellow",
        }.get(self.level.lower(), "#374151")

        agent_label = Text(f"{self.agent:<14}", style=f"bold {a_color}")
        level_label = Text(f" {self.level:<8}", style=lvl_color)
        message = Text(self.msg[:60], style="#374151")
        time_label = Text(f" {ts_str}", style="#9CA3AF")
        return agent_label + level_label + message + time_label


# ── Main TUI ─────────────────────────────────────────────────────────────

class PulseTUI(App):
    CSS = """
    Screen {
        background: #0D1117;
    }
    #header {
        height: 3;
        background: #161B22;
        dock: top;
    }
    #main-area {
        layout: horizontal;
        height: 1fr;
    }
    #log-panel {
        width: 1fr;
        border: solid #30363D;
    }
    #log-scroll {
        height: 1fr;
        padding: 0 1;
    }
    #feed-panel {
        width: 38;
        border: solid #30363D;
    }
    #feed-scroll {
        height: 1fr;
        padding: 0 1;
    }
    #footer {
        height: 2;
        background: #161B22;
        dock: bottom;
        layout: horizontal;
    }
    #footer-hint {
        color: #484F58;
    }
    """

    bot_status = reactive("stopped")
    web_status = reactive("stopped")
    _log_lines: list[tuple[str, str]] = []
    _feed_events: list[tuple[str, str, str, str | None]] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="main-area"):
            with ScrollableContainer(id="log-scroll"):
                yield Vertical(id="log-lines")
            with ScrollableContainer(id="feed-scroll"):
                yield Vertical(id="feed-lines")
        yield Horizontal(
            Static("", id="status-bar"),
            Static("Ctrl+C to stop", id="footer-hint"),
            id="footer",
        )

    def on_mount(self) -> None:
        self.title = "PulseTrade CLI"

    def add_log_line(self, source: str, text: str) -> None:
        # Direct call since _stream runs in the same asyncio event loop
        self._append_log(source, text)

    def set_bot_status(self, status: str) -> None:
        self._update_status("bot", status)

    def set_web_status(self, status: str) -> None:
        self._update_status("web", status)

    def set_feed_events(self, events: list) -> None:
        # Direct call since feed polling runs in the same asyncio event loop
        self._update_feed(events)

    def _append_log(self, source: str, text: str) -> None:
        self._log_lines.append((source, text))
        if len(self._log_lines) > 1000:
            self._log_lines.pop(0)
        try:
            log_vert = self.query_one("#log-lines", Vertical)
            if log_vert:
                log_vert.mount(LogLine(source, text))
                if len(log_vert.children) > 1000:
                    list(log_vert.children)[0].remove()
        except Exception:
            pass

    def _update_status(self, which: str, status: str) -> None:
        if which == "bot":
            self.bot_status = status
        else:
            self.web_status = status
        try:
            sb = self.query_one("#status-bar", Static)
            if sb:
                sb.update(f"BOT: {self.bot_status.upper()}   WEB: {self.web_status.upper()}")
        except Exception:
            pass

    def _update_feed(self, events: list) -> None:
        self._feed_events = []
        try:
            feed_vert = self.query_one("#feed-lines", Vertical)
            if feed_vert:
                feed_vert.remove()
                feed_vert = Vertical(id="feed-lines")
        except Exception:
            feed_vert = None
        for ev in events[:15]:
            if hasattr(ev, "agent"):
                agent, level, msg, ts = ev.agent, ev.level, ev.msg, ev.ts
            else:
                agent, level, msg, ts = ev.get("agent",""), ev.get("level",""), ev.get("msg",""), ev.get("ts")
            self._feed_events.append((agent, level, msg, ts))
            if feed_vert:
                feed_vert.mount(AgentFeedEvent(agent, level, msg, ts))
        try:
            sb = self.query_one("#status-bar", Static)
            if sb:
                sb.update(f"BOT: {self.bot_status.upper()}   WEB: {self.web_status.upper()}")
        except Exception:
            pass

    def on_key(self, event: DOMNode) -> None:
        if event.key == "ctrl_c":
            self.exit(code=0)
