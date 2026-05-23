"""Crucix Agent — macro intelligence layer.

Answers: *Is the macro environment safe to trade?*

Wraps CrucixClient and exposes a clean agent interface.  Called once per
iteration to log the current world state, and consulted by AnalysisAgent and
RiskAgent via ``is_blackout(symbol)``.

If Crucix is not running the agent returns safe defaults and the bot continues
normally — Crucix is enrichment, never a hard dependency.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from adapters.crucix.client import CrucixClient, MacroContext, get_client
from utils.mesh_bus import record_call

if TYPE_CHECKING:
    from adapters.db.db import Database

logger = logging.getLogger(__name__)


class CrucixAgent:
    """Agent wrapper around CrucixClient.

    Provides:
    - ``run()``         — call each bot iteration; logs tier/vix/sweep age to DB
    - ``is_blackout(symbol)`` — returns True if trading should be blocked
    - ``get_context()`` — returns the latest MacroContext
    """

    def __init__(self, db: "Database | None" = None) -> None:
        self._db = db
        self._client: CrucixClient = get_client()

    # ── public API ───────────────────────────────────────────────────────

    def run(self) -> MacroContext:
        """Fetch latest macro context and log it to DB.  Never raises."""
        _t0 = time.monotonic()
        try:
            ctx = self._client.get_context()
            if ctx.crucix_available:
                age_str = (
                    f"{ctx.last_sweep_age_minutes:.0f}min"
                    if ctx.last_sweep_age_minutes < 999
                    else "no sweep yet"
                )
                stale_flag = " [STALE]" if ctx.is_stale and ctx.last_sweep_age_minutes < 999 else ""
                self._emit(
                    "info",
                    f"Crucix — tier={ctx.risk_tier} vix={ctx.vix:.1f} "
                    f"sentiment={ctx.osint_sentiment} "
                    f"scale={ctx.lot_scale_factor:.2f}× "
                    f"age={age_str}{stale_flag}",
                    {
                        "tier": ctx.risk_tier,
                        "vix": ctx.vix,
                        "yield_curve_inverted": ctx.yield_curve_inverted,
                        "osint_sentiment": ctx.osint_sentiment,
                        "sweep_age_min": ctx.last_sweep_age_minutes,
                        "flash_alerts": ctx.active_flash_alerts,
                        "lot_scale": ctx.lot_scale_factor,
                    },
                )
                if ctx.is_stale and ctx.last_sweep_age_minutes < 999:
                    logger.warning(
                        "CrucixAgent: sweep data is stale (%.0f min old)",
                        ctx.last_sweep_age_minutes,
                    )
            else:
                logger.debug("CrucixAgent: Crucix not available — macro context skipped")
            record_call("crucix", (time.monotonic() - _t0) * 1000.0, True)
            return ctx
        except Exception:
            logger.exception("CrucixAgent.run failed")
            record_call("crucix", (time.monotonic() - _t0) * 1000.0, False)
            return MacroContext()

    def is_blackout(self, symbol: str) -> bool:
        """Return True if *symbol* should be blocked due to a macro FLASH alert.

        A blackout is triggered when Crucix reports a FLASH-tier event AND the
        data is not stale.  All other tiers (PRIORITY, ROUTINE, CLEAR) allow
        trading (with lot scaling applied separately).
        """
        try:
            ctx = self._client.get_context()
            if ctx.is_blackout and not ctx.is_stale:
                alerts_str = ", ".join(ctx.active_flash_alerts[:2]) or "unspecified"
                logger.info(
                    "CRUCIX BLACKOUT on %s — tier=%s alerts: %s",
                    symbol,
                    ctx.risk_tier,
                    alerts_str,
                )
                self._emit(
                    "warn",
                    f"CRUCIX FLASH BLACKOUT: {symbol} blocked — {alerts_str}",
                    {
                        "symbol": symbol,
                        "tier": ctx.risk_tier,
                        "alerts": ctx.active_flash_alerts,
                    },
                )
                return True
        except Exception as exc:
            logger.debug("CrucixAgent unavailable: %s", exc)
        return False

    def get_context(self) -> MacroContext:
        """Return the latest MacroContext.  Never raises."""
        try:
            return self._client.get_context()
        except Exception:
            return MacroContext()

    # ── internals ────────────────────────────────────────────────────────

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("crucix", level, msg, data)
