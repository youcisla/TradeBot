"""Crucix intelligence client.

Reads the Crucix intelligence server's /api/data endpoint (running on
localhost:3117) and returns a MacroContext snapshot.

Crucix is the world intelligence layer — 27 data sources updated every 15
minutes.  This client caches the result so the bot doesn't hammer the server
(the data only changes every 15 minutes anyway).

If Crucix is not running, all methods return safe defaults and the bot
continues normally.  Crucix is optional enrichment, never a hard dependency.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Macro risk tiers (mirrors Crucix alert tiers) ────────────────────────────
TIER_CLEAR    = "CLEAR"      # No significant alerts
TIER_ROUTINE  = "ROUTINE"    # Minor background signals
TIER_PRIORITY = "PRIORITY"   # Significant macro event in play
TIER_FLASH    = "FLASH"      # Critical — same as a news blackout


@dataclass
class MacroContext:
    """Distilled world-state from Crucix for a given moment."""

    # Overall risk tier — drives lot scaling and blackout decisions
    risk_tier: str = TIER_CLEAR       # CLEAR / ROUTINE / PRIORITY / FLASH

    # Key economic indicators
    vix: float = 0.0                  # VIX fear index (0 = unknown)
    yield_curve_inverted: bool = False # 10Y-2Y spread negative
    usd_index: float = 0.0            # DXY (0 = unknown)
    oil_price: float = 0.0            # WTI crude

    # Geopolitical / OSINT signals
    active_flash_alerts: list[str] = field(default_factory=list)   # e.g. ["Russia escalation"]
    conflict_regions: list[str] = field(default_factory=list)      # e.g. ["Eastern Europe"]
    sanctions_change: bool = False     # New sanctions event detected this sweep

    # Social sentiment
    osint_sentiment: str = "neutral"  # bullish / bearish / neutral / fearful
    osint_signal_count: int = 0       # Number of active OSINT signals

    # Supply chain / economic stress
    supply_chain_stress: float = 0.0  # GSCPI value (positive = stressed)
    economic_stress: bool = False      # Multiple FRED indicators flashing

    # Metadata
    last_sweep_age_minutes: float = 999.0   # How old the Crucix data is
    crucix_available: bool = False          # Whether Crucix responded at all

    @property
    def is_stale(self) -> bool:
        """True if the Crucix sweep is older than 20 minutes."""
        return self.last_sweep_age_minutes > 20

    @property
    def lot_scale_factor(self) -> float:
        """Risk multiplier to apply to calculated lot sizes based on macro tier."""
        if self.risk_tier == TIER_FLASH:    return 0.0   # No trading
        if self.risk_tier == TIER_PRIORITY: return 0.5   # Half size
        if self.risk_tier == TIER_ROUTINE:  return 0.75  # Reduced
        return 1.0                                        # Full size

    @property
    def is_blackout(self) -> bool:
        """True if macro conditions warrant a full trading blackout."""
        return self.risk_tier == TIER_FLASH

    def confidence_modifier(self, direction: str) -> float:
        """
        Return a confidence multiplier based on macro alignment.

        direction: "BUY" or "SELL"

        Examples:
        - SELL signal during VIX spike (risk-off) → boost confidence
        - BUY signal during FLASH alert → reduce confidence
        """
        mod = 1.0

        # VIX above 30 = fear regime: boost SELL, penalise BUY
        if self.vix > 30:
            mod *= 1.15 if direction == "SELL" else 0.80
        elif self.vix > 20:
            mod *= 1.05 if direction == "SELL" else 0.90

        # FLASH alert → penalise all new entries
        if self.risk_tier == TIER_FLASH:
            mod *= 0.0

        # Inverted yield curve = bearish macro → boost SELL
        if self.yield_curve_inverted:
            mod *= 1.10 if direction == "SELL" else 0.90

        # Economic stress → reduce all confidence
        if self.economic_stress:
            mod *= 0.85

        return round(min(max(mod, 0.0), 2.0), 3)


class CrucixClient:
    """HTTP client for the local Crucix intelligence server.

    Caches the last successful response so multiple bot agents can
    call get_context() without hammering the server.
    """

    def __init__(
        self,
        base_url: str | None = None,
        cache_ttl_seconds: float = 900.0,   # 15 min — matches Crucix sweep interval
        timeout_seconds: float = 3.0,        # fail fast — Crucix is optional
    ) -> None:
        from config import settings
        self._base_url = (base_url or getattr(settings, "CRUCIX_URL", "http://localhost:3117")).rstrip("/")
        self._cache_ttl = cache_ttl_seconds
        self._timeout = timeout_seconds

        self._cached_context: MacroContext | None = None
        self._cache_time: float = 0.0
        self._consecutive_failures: int = 0

    # ── Public API ────────────────────────────────────────────────────────

    def get_context(self) -> MacroContext:
        """Return the latest MacroContext, using cache if fresh.

        Never raises — returns a safe default MacroContext if Crucix
        is unavailable.
        """
        # Return cached value if still fresh
        if self._cached_context and (time.monotonic() - self._cache_time) < self._cache_ttl:
            return self._cached_context

        try:
            raw = self._fetch_data()
            ctx = self._parse(raw)
            self._cached_context = ctx
            self._cache_time = time.monotonic()
            self._consecutive_failures = 0
            return ctx
        except Exception as exc:
            self._consecutive_failures += 1
            # Only log once every 5 failures to avoid log spam
            if self._consecutive_failures <= 1 or self._consecutive_failures % 5 == 0:
                logger.warning(
                    "CrucixClient: server unavailable (%s) — using safe defaults "
                    "(failure #%d)",
                    exc, self._consecutive_failures,
                )
            # Return stale cache if available, else safe defaults
            return self._cached_context or MacroContext()

    def is_available(self) -> bool:
        """Quick health check — True if Crucix server is responding."""
        try:
            req = urllib.request.Request(
                f"{self._base_url}/api/health",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    # ── Internal ─────────────────────────────────────────────────────────

    def _fetch_data(self) -> dict:
        """Fetch /api/data from Crucix. Raises on any error."""
        req = urllib.request.Request(
            f"{self._base_url}/api/data",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _parse(self, raw: dict) -> MacroContext:
        """Convert Crucix /api/data response to MacroContext.

        Crucix's data shape can change as the owner adds sources.
        Every access is defensive — missing keys produce safe defaults.
        This is intentional: owner updates should never crash the bot.
        """
        ctx = MacroContext(crucix_available=True)

        # ── Sweep age ────────────────────────────────────────────────────
        sweep_time_str = raw.get("timestamp") or raw.get("lastSweep") or ""
        if sweep_time_str:
            try:
                from datetime import UTC, datetime
                sweep_dt = datetime.fromisoformat(
                    sweep_time_str.replace("Z", "+00:00")
                )
                age = (datetime.now(UTC) - sweep_dt).total_seconds() / 60
                ctx.last_sweep_age_minutes = round(age, 1)
            except (ValueError, TypeError):
                pass

        # ── Alert tier ───────────────────────────────────────────────────
        # Crucix delta engine produces FLASH/PRIORITY/ROUTINE alerts
        alerts = raw.get("alerts") or raw.get("delta", {}).get("alerts") or []
        tiers = [str(a.get("tier", "")).upper() for a in alerts if isinstance(a, dict)]
        flash_alerts = [a for a in alerts if isinstance(a, dict)
                        and str(a.get("tier", "")).upper() == "FLASH"]

        if "FLASH" in tiers:
            ctx.risk_tier = TIER_FLASH
            ctx.active_flash_alerts = [
                a.get("title", "Unknown alert") for a in flash_alerts
            ]
        elif "PRIORITY" in tiers:
            ctx.risk_tier = TIER_PRIORITY
        elif "ROUTINE" in tiers:
            ctx.risk_tier = TIER_ROUTINE
        else:
            ctx.risk_tier = TIER_CLEAR

        # ── Market data ──────────────────────────────────────────────────
        market = raw.get("market") or raw.get("marketData") or {}
        if isinstance(market, dict):
            # VIX — try multiple possible key names Crucix might use
            for key in ("vix", "VIX", "^VIX", "vixLevel"):
                val = market.get(key)
                if val and isinstance(val, (int, float)):
                    ctx.vix = float(val)
                    break

            # Oil price
            for key in ("wti", "oil", "crude", "WTI", "CL=F"):
                val = market.get(key)
                if val and isinstance(val, (int, float)):
                    ctx.oil_price = float(val)
                    break

            # USD index
            for key in ("dxy", "DXY", "usdIndex", "USD"):
                val = market.get(key)
                if val and isinstance(val, (int, float)):
                    ctx.usd_index = float(val)
                    break

        # ── Economic indicators (FRED) ────────────────────────────────────
        economic = raw.get("economic") or raw.get("fred") or {}
        if isinstance(economic, dict):
            # Yield curve — 10Y minus 2Y spread
            spread = economic.get("yieldCurveSpread") or economic.get("t10y2y")
            if spread is not None:
                try:
                    ctx.yield_curve_inverted = float(spread) < 0
                except (TypeError, ValueError):
                    pass

            # Economic stress — multiple signals flashing
            stress_signals = economic.get("stressSignals") or economic.get("alerts") or []
            ctx.economic_stress = len(stress_signals) >= 3 if isinstance(stress_signals, list) else False

        # ── Supply chain ─────────────────────────────────────────────────
        supply = raw.get("supplyChain") or raw.get("gscpi") or {}
        if isinstance(supply, dict):
            gscpi = supply.get("value") or supply.get("gscpi") or 0
            try:
                ctx.supply_chain_stress = float(gscpi)
            except (TypeError, ValueError):
                pass

        # ── Geopolitical / OSINT ─────────────────────────────────────────
        geo = raw.get("geopolitical") or raw.get("conflict") or {}
        if isinstance(geo, dict):
            ctx.conflict_regions = geo.get("activeRegions") or geo.get("regions") or []
            ctx.sanctions_change = bool(geo.get("sanctionsUpdate") or geo.get("newSanctions"))

        # ── Social sentiment ─────────────────────────────────────────────
        social = raw.get("social") or raw.get("sentiment") or raw.get("osint") or {}
        if isinstance(social, dict):
            ctx.osint_sentiment = str(social.get("sentiment") or "neutral").lower()
            ctx.osint_signal_count = int(social.get("signalCount") or social.get("count") or 0)

        logger.debug(
            "CrucixClient: tier=%s vix=%.1f yield_inverted=%s osint=%s "
            "sweep_age=%.1fmin",
            ctx.risk_tier, ctx.vix, ctx.yield_curve_inverted,
            ctx.osint_sentiment, ctx.last_sweep_age_minutes,
        )
        return ctx


# ── Module-level singleton ───────────────────────────────────────────────────

_client: CrucixClient | None = None


def get_client() -> CrucixClient:
    """Return the shared CrucixClient instance."""
    global _client
    if _client is None:
        _client = CrucixClient()
    return _client


def get_macro_context() -> MacroContext:
    """Convenience function — get current MacroContext from singleton client."""
    return get_client().get_context()
