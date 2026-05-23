"""Crucix intelligence adapter — pure scoring interface.

Provides a clean [-30, +30] delta interface over the local Crucix server.
The server aggregates 27 world-intelligence sources and refreshes every 15 min.

If the Crucix server is unavailable, all methods return safe defaults and the
bot continues normally — Crucix is optional enrichment, never a hard dependency.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Final

from utils.mesh_bus import record_call

logger = logging.getLogger(__name__)

# ── Risk tier constants ──────────────────────────────────────────────────────

TIER_CLEAR: Final[str] = "CLEAR"
TIER_ROUTINE: Final[str] = "ROUTINE"
TIER_PRIORITY: Final[str] = "PRIORITY"
TIER_FLASH: Final[str] = "FLASH"

# ── Macro context dataclass ─────────────────────────────────────────────────

@dataclass
class MacroContext:
    """Distilled world-state from Crucix for a given moment."""

    risk_tier: str = TIER_CLEAR
    vix: float = 0.0
    yield_curve_inverted: bool = False
    usd_index: float = 0.0
    oil_price: float = 0.0
    active_flash_alerts: list[str] = field(default_factory=list)
    conflict_regions: list[str] = field(default_factory=list)
    sanctions_change: bool = False
    osint_sentiment: str = "neutral"
    osint_signal_count: int = 0
    supply_chain_stress: float = 0.0
    economic_stress: bool = False
    last_sweep_age_minutes: float = 999.0
    crucix_available: bool = False

    @property
    def is_stale(self) -> bool:
        return self.last_sweep_age_minutes > 20

    @property
    def lot_scale_factor(self) -> float:
        if self.risk_tier == TIER_FLASH:
            return 0.0
        if self.risk_tier == TIER_PRIORITY:
            return 0.5
        if self.risk_tier == TIER_ROUTINE:
            return 0.75
        return 1.0

    @property
    def is_blackout(self) -> bool:
        return self.risk_tier == TIER_FLASH

    def confidence_modifier(self, direction: str) -> float:
        mod = 1.0
        if self.vix > 30:
            mod *= 1.15 if direction == "SELL" else 0.80
        elif self.vix > 20:
            mod *= 1.05 if direction == "SELL" else 0.90
        if self.risk_tier == TIER_FLASH:
            mod *= 0.0
        if self.yield_curve_inverted:
            mod *= 1.10 if direction == "SELL" else 0.90
        if self.economic_stress:
            mod *= 0.85
        return round(min(max(mod, 0.0), 2.0), 3)


# ── Scoring result ───────────────────────────────────────────────────────────

@dataclass
class CrucixScore:
    """Crucix scoring output — delta in [-30, +30]."""
    delta: float
    confidence: float
    tier: str
    vix: float
    osint_sentiment: str
    blackout: bool
    flash_alerts: list[str]

    @property
    def direction_bias(self) -> float:
        """Positive = SELL bias, Negative = BUY bias."""
        return self.delta


# ── Client ───────────────────────────────────────────────────────────────────

class CrucixClient:
    """HTTP client for the local Crucix intelligence server.

    Caches the last successful response so multiple bot agents can
    call get_context() without hammering the server.
    """

    def __init__(
        self,
        base_url: str | None = None,
        cache_ttl_seconds: float = 900.0,
        timeout_seconds: float = 8.0,
    ) -> None:
        from config import settings
        self._base_url = (base_url or getattr(settings, "CRUCIX_URL", "http://localhost:3117")).rstrip("/")
        self._cache_ttl = cache_ttl_seconds
        self._timeout = timeout_seconds

        self._cached_context: MacroContext | None = None
        self._cache_time: float = 0.0
        self._consecutive_failures: int = 0
        self._backoff_until: float = 0.0

    def get_context(self) -> MacroContext:
        """Return the latest MacroContext, using cache if fresh. Never raises."""
        _t0 = time.monotonic()

        if self._cached_context and (time.monotonic() - self._cache_time) < self._cache_ttl:
            record_call("crucix_client", (time.monotonic() - _t0) * 1000.0, True)
            return self._cached_context

        now = time.monotonic()
        if now < self._backoff_until:
            record_call("crucix_client", (time.monotonic() - _t0) * 1000.0, False)
            return self._cached_context or MacroContext()

        try:
            raw = self._fetch_data()
            ctx = self._parse(raw)
            self._cached_context = ctx
            self._cache_time = now
            self._consecutive_failures = 0
            self._backoff_until = 0.0
            record_call("crucix_client", (time.monotonic() - _t0) * 1000.0, True)
            return ctx
        except Exception as exc:
            self._consecutive_failures += 1
            backoff_secs = min(2 ** self._consecutive_failures * 30, 300)
            self._backoff_until = now + backoff_secs
            if self._consecutive_failures <= 1 or self._consecutive_failures % 5 == 0:
                logger.warning(
                    "CrucixClient: server unavailable (%s) — using safe defaults "
                    "(failure #%d, backoff %.0fs)",
                    exc, self._consecutive_failures, backoff_secs,
                )
            record_call("crucix_client", (time.monotonic() - _t0) * 1000.0, False)
            return self._cached_context or MacroContext()

    def score(self) -> CrucixScore:
        """Return a scored signal in [-30, +30] delta format.

        Used by the scoring pipeline as a standalone scorer.
        """
        ctx = self.get_context()

        if ctx.vix > 30:
            base_delta = -15.0
        elif ctx.vix > 20:
            base_delta = -5.0
        else:
            base_delta = 0.0

        if ctx.yield_curve_inverted:
            base_delta = max(base_delta, 10.0)

        if ctx.economic_stress:
            base_delta *= 0.7

        delta = round(base_delta, 1)
        confidence = 0.5 if ctx.crucix_available else 0.0

        return CrucixScore(
            delta=delta,
            confidence=confidence,
            tier=ctx.risk_tier,
            vix=ctx.vix,
            osint_sentiment=ctx.osint_sentiment,
            blackout=ctx.is_blackout,
            flash_alerts=ctx.active_flash_alerts,
        )

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{self._base_url}/api/health",
                headers={"Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                return resp.status == 200
        except Exception:
            return False

    def _fetch_data(self) -> dict:
        req = urllib.request.Request(
            f"{self._base_url}/api/data",
            headers={"Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _parse(self, raw: dict) -> MacroContext:
        ctx = MacroContext(crucix_available=True)

        sweep_time_str = (
            raw.get("meta", {}).get("timestamp")
            or raw.get("timestamp")
            or raw.get("lastSweep")
            or ""
        )
        if sweep_time_str:
            try:
                sweep_dt = datetime.fromisoformat(sweep_time_str.replace("Z", "+00:00"))
                age = (datetime.now(UTC) - sweep_dt).total_seconds() / 60
                ctx.last_sweep_age_minutes = round(age, 1)
            except (ValueError, TypeError):
                pass

        markets = raw.get("markets") or {}
        vix_obj = markets.get("vix") if isinstance(markets, dict) else None
        if isinstance(vix_obj, dict):
            vix_raw = vix_obj.get("value")
        else:
            market_flat = raw.get("market") or raw.get("marketData") or {}
            vix_raw = None
            for key in ("vix", "VIX", "^VIX", "vixLevel"):
                val = market_flat.get(key) if isinstance(market_flat, dict) else None
                if val and isinstance(val, (int, float)):
                    vix_raw = val
                    break
        if vix_raw and isinstance(vix_raw, (int, float)):
            ctx.vix = float(vix_raw)

        tg_urgent: list = raw.get("tg", {}).get("urgent", []) if isinstance(raw.get("tg"), dict) else []
        alerts_list: list = raw.get("alerts", []) if isinstance(raw.get("alerts"), list) else []
        all_alerts = tg_urgent + alerts_list

        has_flash_alert = any(
            str(p.get("tier", "")).upper() == "FLASH"
            for p in all_alerts if isinstance(p, dict)
        )
        has_priority_alert = any(
            str(p.get("tier", "")).upper() == "PRIORITY"
            for p in all_alerts if isinstance(p, dict)
        )

        if has_flash_alert:
            ctx.risk_tier = TIER_FLASH
            ctx.active_flash_alerts = [
                str(p.get("text", p.get("title", "")))[:100]
                for p in all_alerts
                if isinstance(p, dict) and str(p.get("tier", "")).upper() == "FLASH"
            ]
        elif has_priority_alert:
            ctx.risk_tier = TIER_PRIORITY
        elif ctx.vix > 40:
            ctx.risk_tier = TIER_FLASH
            ctx.active_flash_alerts = [f"VIX spike: {ctx.vix:.1f}"]
        elif ctx.vix > 28:
            ctx.risk_tier = TIER_PRIORITY
        elif ctx.vix > 18:
            ctx.risk_tier = TIER_ROUTINE
        else:
            ctx.risk_tier = TIER_CLEAR

        gdelt_tone = raw.get("gdelt", {}).get("avgTone") if isinstance(raw.get("gdelt"), dict) else None
        if gdelt_tone is not None:
            try:
                tone = float(gdelt_tone)
                if tone < -3:
                    ctx.osint_sentiment = "bearish"
                elif tone > 3:
                    ctx.osint_sentiment = "bullish"
                else:
                    ctx.osint_sentiment = "neutral"
            except (TypeError, ValueError):
                pass
        else:
            social = raw.get("social") or raw.get("sentiment") or raw.get("osint") or {}
            if isinstance(social, dict):
                ctx.osint_sentiment = str(social.get("sentiment") or "neutral").lower()
                ctx.osint_signal_count = int(social.get("signalCount") or social.get("count") or 0)

        fred_series: list = raw.get("fred", []) if isinstance(raw.get("fred"), list) else []
        if fred_series:
            t10y = next((f.get("value") for f in fred_series if isinstance(f, dict) and f.get("id") == "GS10"), None)
            t2y = next((f.get("value") for f in fred_series if isinstance(f, dict) and f.get("id") == "GS2"), None)
            if t10y is not None and t2y is not None:
                try:
                    ctx.yield_curve_inverted = float(t10y) - float(t2y) < 0
                except (TypeError, ValueError):
                    pass
        else:
            economic = raw.get("economic") or {}
            if isinstance(economic, dict):
                spread = economic.get("yieldCurveSpread") or economic.get("t10y2y")
                if spread is not None:
                    try:
                        ctx.yield_curve_inverted = float(spread) < 0
                    except (TypeError, ValueError):
                        pass
                stress_signals = economic.get("stressSignals") or economic.get("alerts") or []
                ctx.economic_stress = len(stress_signals) >= 3 if isinstance(stress_signals, list) else False

        if isinstance(markets, dict):
            oil_obj = markets.get("oil") or markets.get("wti") or markets.get("crude") or {}
            if isinstance(oil_obj, dict):
                oil_val = oil_obj.get("value")
                if oil_val and isinstance(oil_val, (int, float)):
                    ctx.oil_price = float(oil_val)
            dxy_obj = markets.get("dxy") or markets.get("usdIndex") or {}
            if isinstance(dxy_obj, dict):
                dxy_val = dxy_obj.get("value")
                if dxy_val and isinstance(dxy_val, (int, float)):
                    ctx.usd_index = float(dxy_val)

        geo = raw.get("geopolitical") or raw.get("conflict") or {}
        if isinstance(geo, dict):
            ctx.conflict_regions = geo.get("activeRegions") or geo.get("regions") or []
            ctx.sanctions_change = bool(geo.get("sanctionsUpdate") or geo.get("newSanctions"))

        logger.debug(
            "CrucixClient: tier=%s vix=%.1f yield_inverted=%s osint=%s sweep_age=%.1fmin",
            ctx.risk_tier, ctx.vix, ctx.yield_curve_inverted,
            ctx.osint_sentiment, ctx.last_sweep_age_minutes,
        )
        return ctx


# ── Module-level singleton ───────────────────────────────────────────────────

_client: CrucixClient | None = None


def get_client() -> CrucixClient:
    global _client
    if _client is None:
        _client = CrucixClient()
    return _client


def get_macro_context() -> MacroContext:
    return get_client().get_context()


def score_crucix() -> CrucixScore:
    """Convenience function — return scored Crucix signal for the scoring pipeline."""
    return get_client().score()