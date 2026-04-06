"""Persistent Agent Memory — Letta-style cross-session memory blocks.

Stores 8 labeled memory blocks in PostgreSQL (bot_memory table) so the bot
can remember state across restarts, log incidents, and give CrucixAgent a
warm-start cached market regime.

Memory blocks
─────────────
session_context       Last bot start time, active symbols, current regime
trade_history_summary Last 20 trades: symbol, direction, pnl, outcome
model_performance     LSTM/LGBM rolling accuracy metrics (30-day window)
market_regime         Current macro regime snapshot from Crucix
user_preferences      Risk tolerance, preferred pairs, blacklisted symbols
strategy_notes        Manual notes entered from the dashboard command panel
incident_log          Broker errors, slippage events, failed executions
performance_journal   Weekly returns, Sharpe, drawdown, equity milestones

Integration
───────────
LoggingAgent calls update_* methods after each completed trade cycle.
CrucixAgent reads market_regime on startup as a cross-session fallback so a
successful previous run is not wasted if Crucix is temporarily unreachable.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from database.db import Database
    from models.trade import Trade

logger = logging.getLogger(__name__)

# ── public block-name constants ───────────────────────────────────────────
BLOCK_SESSION_CONTEXT     = "session_context"
BLOCK_TRADE_HISTORY       = "trade_history_summary"
BLOCK_MODEL_PERFORMANCE   = "model_performance"
BLOCK_MARKET_REGIME       = "market_regime"
BLOCK_USER_PREFERENCES    = "user_preferences"
BLOCK_STRATEGY_NOTES      = "strategy_notes"
BLOCK_INCIDENT_LOG        = "incident_log"
BLOCK_PERFORMANCE_JOURNAL = "performance_journal"

_INCIDENT_LOG_MAX_ENTRIES = 50   # cap so the column doesn't grow unbounded


class MemoryAgent:
    """Persistent cross-session memory for the PulseTrade TradingBot.

    All writes are fail-open: any DB exception is logged at DEBUG level and
    the caller is never interrupted by a memory failure.

    Parameters
    ----------
    db:
        Database instance.  When ``None`` all writes are no-ops and all
        reads return ``None``.
    """

    def __init__(self, db: "Database | None" = None) -> None:
        self._db = db

    # ── raw block I/O ─────────────────────────────────────────────────────

    def write_block(self, block_name: str, content: str) -> bool:
        """Upsert a named memory block.

        Returns ``True`` on success, ``False`` when the DB is unavailable or
        an error occurs (fail-open).
        """
        if self._db is None:
            return False
        try:
            self._db.write_memory_block(block_name, content)
            return True
        except Exception:
            logger.debug("MemoryAgent.write_block(%s) failed", block_name, exc_info=True)
            return False

    def read_block(self, block_name: str) -> str | None:
        """Return the stored content for *block_name*, or ``None``."""
        if self._db is None:
            return None
        try:
            return self._db.read_memory_block(block_name)
        except Exception:
            logger.debug("MemoryAgent.read_block(%s) failed", block_name, exc_info=True)
            return None

    # ── domain-specific block writers ─────────────────────────────────────

    def update_session_context(
        self,
        symbols: list[str],
        regime: str = "",
        started_at: "datetime | None" = None,
    ) -> None:
        """Write bot startup metadata to ``session_context``."""
        try:
            payload = {
                "started_at": (started_at or datetime.now(UTC)).isoformat(),
                "symbols": list(symbols),
                "regime": regime,
            }
            self.write_block(BLOCK_SESSION_CONTEXT, json.dumps(payload))
        except Exception:
            logger.debug("update_session_context failed", exc_info=True)

    def update_trade_history(self, trades: "list[Trade]") -> None:
        """Persist a compact summary of the last 20 closed trades."""
        try:
            records = []
            for t in trades[-20:]:
                records.append(
                    {
                        "id": getattr(t, "id", None),
                        "symbol": getattr(t, "symbol", ""),
                        "direction": getattr(t, "direction", ""),
                        "pnl": float(t.pnl) if t.pnl is not None else None,
                        "outcome": "win" if (t.pnl or 0) > 0 else "loss",
                        "close_time": (
                            t.close_time.isoformat()
                            if getattr(t, "close_time", None)
                            else None
                        ),
                    }
                )
            self.write_block(BLOCK_TRADE_HISTORY, json.dumps({"trades": records}))
        except Exception:
            logger.debug("update_trade_history failed", exc_info=True)

    def update_model_performance(self, metrics: dict) -> None:
        """Persist LSTM/LGBM rolling accuracy metrics."""
        try:
            payload = dict(metrics)
            payload["updated_at"] = datetime.now(UTC).isoformat()
            self.write_block(BLOCK_MODEL_PERFORMANCE, json.dumps(payload))
        except Exception:
            logger.debug("update_model_performance failed", exc_info=True)

    def update_market_regime(self, regime_info: "dict | str") -> None:
        """Persist the current macro regime snapshot from Crucix.

        Accepts either a plain string or a dict of MacroContext fields.
        """
        try:
            if isinstance(regime_info, str):
                content = regime_info
            else:
                payload = dict(regime_info)
                payload["updated_at"] = datetime.now(UTC).isoformat()
                content = json.dumps(payload)
            self.write_block(BLOCK_MARKET_REGIME, content)
        except Exception:
            logger.debug("update_market_regime failed", exc_info=True)

    def append_incident(self, event: str) -> None:
        """Append an incident string to the ``incident_log`` block.

        The log is capped at ``_INCIDENT_LOG_MAX_ENTRIES`` entries so the
        stored JSON blob never grows unbounded.
        """
        try:
            stored = self.read_block(BLOCK_INCIDENT_LOG) or "[]"
            try:
                entries: list = json.loads(stored)
            except (json.JSONDecodeError, TypeError):
                entries = []
            entries.append(
                {
                    "ts": datetime.now(UTC).isoformat(),
                    "event": event,
                }
            )
            if len(entries) > _INCIDENT_LOG_MAX_ENTRIES:
                entries = entries[-_INCIDENT_LOG_MAX_ENTRIES:]
            self.write_block(BLOCK_INCIDENT_LOG, json.dumps(entries))
        except Exception:
            logger.debug("append_incident failed", exc_info=True)

    def update_performance_journal(self, stats: dict) -> None:
        """Persist weekly / daily performance stats."""
        try:
            payload = dict(stats)
            payload["updated_at"] = datetime.now(UTC).isoformat()
            self.write_block(BLOCK_PERFORMANCE_JOURNAL, json.dumps(payload))
        except Exception:
            logger.debug("update_performance_journal failed", exc_info=True)

    # ── convenience readers ───────────────────────────────────────────────

    def read_market_regime(self) -> str | None:
        """Return the stored ``market_regime`` block (CrucixAgent warm-start)."""
        return self.read_block(BLOCK_MARKET_REGIME)
