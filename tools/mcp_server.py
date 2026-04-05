"""mcp_server.py — Model Context Protocol (MCP) server for bot state inspection.

Exposes the bot's live state as callable MCP tools so that AI agents and IDE
integrations can query the bot without touching the database directly.

Gated by ``settings.MCP_SERVER_ENABLED``.  Port is ``settings.MCP_SERVER_PORT``
(default 8765).

Endpoints exposed via FastMCP:
    - ``bot_status``    → heartbeat + last-known agent states
    - ``open_trades``   → live positions from broker
    - ``agent_feed``    → last N events from EventLog
    - ``macro_snapshot``→ latest MacroSnapshot from IntelligenceSweep
    - ``guard_check``   → run GuardPipeline against a hypothetical signal

Run standalone (for testing)::

    python -m tools.mcp_server

Or import and mount inside a FastAPI app::

    from tools.mcp_server import build_mcp_app
    app = build_mcp_app()
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Settings ──────────────────────────────────────────────────────────────

def _mcp_enabled() -> bool:
    try:
        from config import settings
        return bool(getattr(settings, "MCP_SERVER_ENABLED", False))
    except Exception:  # noqa: BLE001
        return False


def _mcp_port() -> int:
    try:
        from config import settings
        return int(getattr(settings, "MCP_SERVER_PORT", 8765))
    except Exception:  # noqa: BLE001
        return 8765


# ── MCP tool implementations ──────────────────────────────────────────────

def _read_heartbeat() -> dict:
    """Read the heartbeat file written by state.Heartbeat."""
    hb_path = Path("state") / "heartbeat.json"
    if hb_path.exists():
        try:
            return json.loads(hb_path.read_text())
        except Exception:  # noqa: BLE001
            pass
    return {"status": "unknown", "note": "heartbeat.json not found"}


def _tail_event_log(n: int = 20) -> list[dict]:
    """Return last N events from the rotating event log."""
    try:
        from state.event_log import EventLog
        log = EventLog()
        return log.tail(n)
    except Exception as exc:  # noqa: BLE001
        return [{"error": str(exc)}]


def _get_macro_snapshot() -> dict:
    """Return the latest MacroSnapshot as a dict (best-effort)."""
    try:
        from filters.intelligence_sweep import IntelligenceSweep
        sweep = IntelligenceSweep()
        snap = sweep.get_latest()
        if snap is None:
            return {"status": "no_snapshot_yet"}
        import dataclasses
        return dataclasses.asdict(snap)
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


def _open_trades_summary() -> list[dict]:
    """Summarise live open positions (read-only, broker-agnostic)."""
    try:
        # Try to reuse a running broker connection if registered on the mesh bus
        from utils.mesh_bus import get_shared
        broker = get_shared("broker")
        if broker is None:
            return [{"note": "broker not registered on mesh bus"}]
        positions = broker.get_open_positions()
        return [
            {
                "symbol": getattr(p, "symbol", ""),
                "direction": getattr(p, "direction", ""),
                "lots": getattr(p, "lot_size", 0),
                "ticket": getattr(p, "ticket", None) or getattr(p, "ticket_id", None),
                "pnl": getattr(p, "profit", None) or getattr(p, "pnl", None),
            }
            for p in positions
        ]
    except Exception as exc:  # noqa: BLE001
        return [{"error": str(exc)}]


def _guard_check(symbol: str, direction: str, lots: float = 0.01) -> dict:
    """Run the GuardPipeline against a hypothetical signal."""
    try:
        from agents.guards import GuardPipeline
        from models.signal import Signal

        sig = Signal(
            symbol=symbol,
            direction=direction.upper(),
            strategy="mcp_check",
            confidence=0.5,
            entry_price=0.0,
            stop_loss=0.0,
            take_profit=0.0,
        )
        pipeline = GuardPipeline(broker=None, db=None)
        passed, reason = pipeline.check(sig, open_trades=[])
        return {"passed": passed, "reason": reason}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


# ── FastMCP server builder ────────────────────────────────────────────────

def build_mcp_app():
    """Build and return a FastMCP application."""
    try:
        from fastmcp import FastMCP
    except ImportError:
        logger.error("fastmcp not installed — pip install fastmcp")
        return None

    mcp = FastMCP("NeuralFX TradingBot")

    @mcp.tool()
    def bot_status() -> dict:
        """Return the bot heartbeat and current alive status."""
        return _read_heartbeat()

    @mcp.tool()
    def agent_feed(n: int = 20) -> list:
        """Return the last *n* events from the bot event log (max 100)."""
        return _tail_event_log(min(int(n), 100))

    @mcp.tool()
    def macro_snapshot() -> dict:
        """Return the most recent macro intelligence snapshot (FRED / VIX / DXY)."""
        return _get_macro_snapshot()

    @mcp.tool()
    def open_trades() -> list:
        """Return a summary of currently open broker positions."""
        return _open_trades_summary()

    @mcp.tool()
    def guard_check(symbol: str, direction: str, lots: float = 0.01) -> dict:
        """Check whether a hypothetical trade would pass the GuardPipeline."""
        return _guard_check(symbol, direction, lots)

    return mcp


# ── Entry point ───────────────────────────────────────────────────────────

def main() -> None:
    if not _mcp_enabled():
        logger.warning("MCP server disabled (MCP_SERVER_ENABLED=False). Exiting.")
        sys.exit(0)

    port = _mcp_port()
    app = build_mcp_app()
    if app is None:
        sys.exit(1)

    logger.info("Starting NeuralFX MCP server on port %d", port)
    try:
        app.run(transport="sse", port=port)
    except Exception as exc:  # noqa: BLE001
        logger.error("MCP server crashed: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
