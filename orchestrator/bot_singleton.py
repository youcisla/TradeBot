"""Global bot singleton — allows FastAPI routes to access the running TradingBot."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from orchestrator.bot import TradingBot

_bot: "TradingBot | None" = None


def set_bot(bot: "TradingBot") -> None:
    global _bot
    _bot = bot


def get_bot() -> "TradingBot | None":
    return _bot