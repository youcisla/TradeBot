"""MT5 reconnection helpers.

Encapsulates the per-symbol IPC backoff mechanism that throttles retry
frequency when MetaTrader 5 returns "Terminal: Call failed" errors.
"""

from __future__ import annotations

import logging
import time as _time
from typing import Any

logger = logging.getLogger(__name__)


def check_ipc_backoff(connector, broker_sym: str) -> None:
    """Raise RuntimeError if *broker_sym* is currently in IPC backoff."""
    backoff_until = connector._ipc_backoff_until.get(broker_sym, 0.0)
    now = _time.monotonic()
    if now < backoff_until:
        raise RuntimeError(
            f"IPC backoff for {broker_sym} until {_time.monotonic():.0f}"
        )


def apply_ipc_error(
    connector,
    broker_sym: str,
    err_str: str,
    now: float | None = None,
) -> None:
    """Record an IPC error and double backoff duration if already in backoff.

    The backoff starts at 30s and doubles each time a repeat failure arrives
    while the symbol is already cooling off (up to 5 minutes max).
    """
    if now is None:
        now = _time.monotonic()

    if "Terminal: Call failed" in err_str or "IPC" in err_str:
        prev = connector._ipc_backoff_until.get(broker_sym, 0.0)
        if prev > now:
            connector._ipc_backoff_secs = min(
                connector._ipc_backoff_secs * 2, 300.0
            )
        else:
            connector._ipc_backoff_secs = 30.0  # reset on fresh failure
        connector._ipc_backoff_until[broker_sym] = now + connector._ipc_backoff_secs
        logger.debug(
            "MT5 IPC backoff for %s: %.0fs (err=%s)",
            broker_sym,
            connector._ipc_backoff_secs,
            err_str,
        )


def reset_ipc_backoff(connector, broker_sym: str) -> None:
    """Clear backoff state for a symbol (call after successful operations)."""
    connector._ipc_backoff_until.pop(broker_sym, None)
    connector._ipc_backoff_secs = 30.0
