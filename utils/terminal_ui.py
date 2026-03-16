"""Terminal UI — disabled. Normal stdout/stderr logging is used instead."""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.trade import Trade


class _NoOpUI:
    """Accepts all UI calls silently so call-sites need no changes."""

    def start(self) -> None: pass
    def stop(self) -> None: pass
    def set_bot_status(self, *a, **kw) -> None: pass
    def set_agent_status(self, *a, **kw) -> None: pass
    def set_agent_idle(self, *a, **kw) -> None: pass
    def add_event(self, *a, **kw) -> None: pass
    def set_trade(self, *a, **kw) -> None: pass
    def remove_trade(self, *a, **kw) -> None: pass


_ui: _NoOpUI | None = None


def get_ui() -> None:
    """Always returns None — disables all dashboard rendering."""
    return None


def init(refresh_per_second: int = 4) -> _NoOpUI:
    """Returns a no-op object so existing call-sites don't crash."""
    global _ui
    _ui = _NoOpUI()
    return _ui
