"""Async poller for agent events from candle_server HTTP API."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Awaitable

import httpx

logger = logging.getLogger(__name__)

AGENT_COLORS: dict[str, str] = {
    "crucix":       "#64D2FF",
    "market":       "#32ADE6",
    "analysis":     "#636366",
    "strategy":     "#16A34A",
    "neural":       "#9333EA",
    "council":      "#D97706",
    "risk":         "#DC2626",
    "execution":    "#6B7280",
    "trade_manager":"#0EA5E9",
    "learning":     "#8B5CF6",
    "logging":      "#9CA3AF",
    "model_manager": "#6366F1",
    "debate":       "#F59E0B",
    "exposure":     "#10B981",
    "memory":       "#14B8A6",
}

LEVEL_COLORS: dict[str, str] = {
    "error":    "#DC2626",
    "critical": "#DC2626",
    "warn":     "#D97706",
    "info":     "#374151",
    "debug":    "#9CA3AF",
}


@dataclass
class AgentEvent:
    agent: str
    level: str
    msg: str
    ts: str | None

    @property
    def agent_color(self) -> str:
        return AGENT_COLORS.get(self.agent.lower(), "#9CA3AF")

    @property
    def level_color(self) -> str:
        return LEVEL_COLORS.get(self.level.lower(), "#374151")


def parse_events(raw: list[dict]) -> list[AgentEvent]:
    """Parse raw event dicts into AgentEvent dataclasses."""
    events = []
    for row in raw:
        agent = str(row.get("agent", ""))
        level = str(row.get("level", "info"))
        msg = str(row.get("msg") or row.get("message") or "")
        ts = None
        if row.get("ts"):
            ts = row["ts"]
        elif row.get("created_at"):
            ts = row["created_at"]
        events.append(AgentEvent(agent=agent, level=level, msg=msg, ts=ts))
    return events


class AgentFeed:
    """Async poller for the candle_server /api/agent-events endpoint."""

    def __init__(
        self,
        url: str = "http://127.0.0.1:5555/api/agent-events",
        limit: int = 30,
        poll_interval: float = 3.0,
        on_events: Callable[[list[AgentEvent]], Awaitable[None]] | None = None,
    ) -> None:
        self.url = url
        self.limit = limit
        self.poll_interval = poll_interval
        self.on_events = on_events
        self._events: list[AgentEvent] = []
        self._running = False
        self._task: asyncio.Task[None] | None = None
        self._connected = False

    @property
    def events(self) -> list[AgentEvent]:
        return self._events

    @property
    def connected(self) -> bool:
        return self._connected

    async def _fetch(self) -> list[AgentEvent]:
        """Fetch events from the API."""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.url}?limit={self.limit}")
                if resp.status_code == 200:
                    self._connected = True
                    data = resp.json()
                    raw = data.get("events", []) if isinstance(data, dict) else data
                    return parse_events(raw)
                else:
                    self._connected = False
                    return []
        except Exception:
            self._connected = False
            return []

    async def _poll(self) -> None:
        """Poll the API and call on_events callback."""
        while self._running:
            try:
                events = await self._fetch()
                if events:
                    self._events = events[:15]  # Keep last 15
                if self.on_events and events:
                    await self.on_events(self._events)
            except Exception:
                pass
            await asyncio.sleep(self.poll_interval)

    async def start(self) -> None:
        """Start polling in the background."""
        self._running = True
        loop = asyncio.get_event_loop()
        self._task = loop.create_task(self._poll())

    def stop(self) -> None:
        """Stop polling."""
        self._running = False
        if self._task:
            self._task.cancel()


async def fetch_agent_events(
    url: str = "http://127.0.0.1:5555/api/agent-events",
    limit: int = 20,
) -> list[AgentEvent]:
    """One-shot fetch of agent events (non-polling)."""
    feed = AgentFeed(url=url, limit=limit)
    return await feed._fetch()
