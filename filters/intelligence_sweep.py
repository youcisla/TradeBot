"""IntelligenceSweep — parallel multi-source macro data aggregator.

Pulls macro intelligence from FRED, GDELT, yfinance, and EIA in parallel
and normalises results into a single `MacroSnapshot` dict. Results are
cached so the main bot loop can call `get_latest()` cheaply at any tick.

Usage::

    from filters.intelligence_sweep import IntelligenceSweep

    sweep = IntelligenceSweep()
    await sweep.start()                  # launches background refresh task
    snapshot = sweep.get_latest()        # returns latest cached snapshot
    await sweep.stop()
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class MacroSnapshot:
    """Normalised output from all macro data sources."""

    # Timestamps
    fetched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # FRED series (latest values)
    dgs10: float | None = None          # 10-Year Treasury yield
    dgs2: float | None = None           # 2-Year Treasury yield
    t10y2y: float | None = None         # 10Y-2Y spread (inversion flag)
    vixcls: float | None = None         # VIX closing level
    dtwexbgs: float | None = None       # USD index
    dcoilwtico: float | None = None     # WTI crude price
    fedfunds: float | None = None       # Effective Fed Funds rate
    m2sl: float | None = None           # M2 money supply
    unrate: float | None = None         # Unemployment rate
    cpiaucsl: float | None = None       # CPI all-urban

    # yfinance snapshots
    spy_prev_close: float | None = None  # S&P 500 proxy
    gld_prev_close: float | None = None  # Gold proxy
    dxy_prev_close: float | None = None  # DXY index proxy

    # EIA crude inventory (million barrels)
    crude_inventory_change_mbbl: float | None = None

    # GDELT risk tone (-1.0 = very negative … +1.0 = very positive)
    gdelt_risk_tone: float | None = None

    # Derived composite signals
    yield_curve_inverted: bool = False
    usd_strength: str = "neutral"       # "strong" | "neutral" | "weak"
    risk_tier: str = "normal"           # "low" | "normal" | "elevated" | "crisis"

    # Source health
    sources_ok: list[str] = field(default_factory=list)
    sources_failed: list[str] = field(default_factory=list)


class IntelligenceSweep:
    """Async background sweeper that refreshes macro data on a schedule."""

    _FRED_SERIES = [
        "DGS10", "DGS2", "T10Y2Y", "VIXCLS",
        "DTWEXBGS", "DCOILWTICO", "FEDFUNDS",
        "M2SL", "UNRATE", "CPIAUCSL",
    ]

    def __init__(self) -> None:
        self._snapshot: MacroSnapshot = MacroSnapshot()
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._interval = settings.INTELLIGENCE_SWEEP_INTERVAL_MINUTES * 60

    # ── Public API ────────────────────────────────────────────────────────

    def get_latest(self) -> MacroSnapshot:
        """Return the most recently fetched snapshot (non-blocking)."""
        return self._snapshot

    async def start(self) -> None:
        """Launch the background refresh coroutine."""
        if self._task is None or self._task.done():
            await self._refresh_once()   # eager first fetch
            self._task = asyncio.create_task(self._loop(), name="intelligence_sweep")
            logger.info("IntelligenceSweep background task started")

    async def stop(self) -> None:
        """Cancel the background task gracefully."""
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("IntelligenceSweep stopped")

    async def run_once(self) -> MacroSnapshot:
        """Force an immediate refresh and return the result."""
        await self._refresh_once()
        return self._snapshot

    # ── Internal loop ─────────────────────────────────────────────────────

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self._interval)
            await self._refresh_once()

    async def _refresh_once(self) -> None:
        results = await asyncio.gather(
            self._fetch_fred(),
            self._fetch_yfinance(),
            self._fetch_eia(),
            self._fetch_gdelt(),
            return_exceptions=True,
        )

        snap = MacroSnapshot()

        # FRED
        if not isinstance(results[0], Exception):
            self._apply_fred(snap, results[0])
            snap.sources_ok.append("fred")
        else:
            snap.sources_failed.append("fred")
            logger.warning("FRED fetch failed: %s", results[0])

        # yfinance
        if not isinstance(results[1], Exception):
            self._apply_yfinance(snap, results[1])
            snap.sources_ok.append("yfinance")
        else:
            snap.sources_failed.append("yfinance")
            logger.debug("yfinance fetch skipped: %s", results[1])

        # EIA
        if not isinstance(results[2], Exception):
            self._apply_eia(snap, results[2])
            snap.sources_ok.append("eia")
        else:
            snap.sources_failed.append("eia")
            logger.debug("EIA fetch failed: %s", results[2])

        # GDELT
        if not isinstance(results[3], Exception):
            self._apply_gdelt(snap, results[3])
            snap.sources_ok.append("gdelt")
        else:
            snap.sources_failed.append("gdelt")
            logger.debug("GDELT fetch failed: %s", results[3])

        self._derive_composites(snap)

        async with self._lock:
            self._snapshot = snap

        logger.debug(
            "IntelligenceSweep refreshed — ok: %s  failed: %s",
            snap.sources_ok,
            snap.sources_failed,
        )

    # ── Source fetchers ───────────────────────────────────────────────────

    async def _fetch_fred(self) -> dict[str, float]:
        """Fetch latest value for each FRED series.

        Requires ``fredapi`` package and FRED_API_KEY in settings.
        Falls back to returning an empty dict if the key is missing.
        """
        api_key = settings.FRED_API_KEY
        if not api_key:
            return {}

        loop = asyncio.get_event_loop()

        def _sync_fetch() -> dict[str, float]:
            # Import lazily so the bot works even if fredapi is not installed.
            from fredapi import Fred  # type: ignore[import]

            fred = Fred(api_key=api_key)
            out: dict[str, float] = {}
            for series_id in self._FRED_SERIES:
                try:
                    series = fred.get_series_latest_release(series_id)
                    if series is not None and len(series) > 0:
                        val = float(series.dropna().iloc[-1])
                        out[series_id] = val
                except Exception as exc:  # noqa: BLE001
                    logger.debug("FRED series %s failed: %s", series_id, exc)
            return out

        return await loop.run_in_executor(None, _sync_fetch)

    async def _fetch_yfinance(self) -> dict[str, Any]:
        """Fetch previous-close prices for key market proxies via yfinance."""
        if not settings.YFINANCE_ENABLED:
            return {}

        loop = asyncio.get_event_loop()

        def _sync_fetch() -> dict[str, Any]:
            import yfinance as yf  # type: ignore[import]

            tickers = {"SPY": "spy", "GLD": "gld", "UUP": "dxy"}
            out: dict[str, Any] = {}
            for ticker, key in tickers.items():
                try:
                    data = yf.Ticker(ticker).fast_info
                    out[key] = getattr(data, "previous_close", None)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("yfinance %s failed: %s", ticker, exc)
            return out

        return await loop.run_in_executor(None, _sync_fetch)

    async def _fetch_eia(self) -> dict[str, Any]:
        """Fetch EIA weekly crude oil inventory change.

        Returns empty dict when no data is available — caller treats as
        non-critical. No API key required for the public EIA JSON endpoint.
        """
        import urllib.request
        import json as _json

        url = (
            "https://api.eia.gov/v2/petroleum/stoc/wstk/data/"
            "?api_key=DEMO_KEY&frequency=weekly&data[0]=value"
            "&facets[product][]=EPC0&facets[area][]=NUS"
            "&sort[0][column]=period&sort[0][direction]=desc&length=2"
        )

        loop = asyncio.get_event_loop()

        def _sync_get() -> dict[str, Any]:
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    payload = _json.loads(resp.read())
                rows = payload.get("response", {}).get("data", [])
                if len(rows) >= 2:
                    latest = float(rows[0]["value"])
                    prev = float(rows[1]["value"])
                    return {"change_mbbl": latest - prev}
            except Exception as exc:  # noqa: BLE001
                logger.debug("EIA fetch failed: %s", exc)
            return {}

        return await loop.run_in_executor(None, _sync_get)

    async def _fetch_gdelt(self) -> dict[str, Any]:
        """Fetch latest GDELT GKG global risk tone average.

        GDELT updates every 15 minutes. We request the last 1-day summary
        from the free GDG REST API (no key required).
        """
        import urllib.request
        import json as _json

        url = (
            "https://api.gdeltproject.org/api/v2/doc/doc"
            "?query=finance%20economy&mode=artlist&maxrecords=5&format=json"
        )

        loop = asyncio.get_event_loop()

        def _sync_get() -> dict[str, Any]:
            try:
                with urllib.request.urlopen(url, timeout=8) as resp:
                    payload = _json.loads(resp.read())
                articles = payload.get("articles", [])
                tones = [float(a["tone"]) for a in articles if "tone" in a]
                if tones:
                    return {"tone": sum(tones) / len(tones)}
            except Exception as exc:  # noqa: BLE001
                logger.debug("GDELT fetch failed: %s", exc)
            return {}

        return await loop.run_in_executor(None, _sync_get)

    # ── Apply helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _apply_fred(snap: MacroSnapshot, data: dict[str, float]) -> None:
        mapping = {
            "DGS10": "dgs10", "DGS2": "dgs2", "T10Y2Y": "t10y2y",
            "VIXCLS": "vixcls", "DTWEXBGS": "dtwexbgs",
            "DCOILWTICO": "dcoilwtico", "FEDFUNDS": "fedfunds",
            "M2SL": "m2sl", "UNRATE": "unrate", "CPIAUCSL": "cpiaucsl",
        }
        for fred_id, attr in mapping.items():
            if fred_id in data:
                setattr(snap, attr, data[fred_id])

    @staticmethod
    def _apply_yfinance(snap: MacroSnapshot, data: dict[str, Any]) -> None:
        snap.spy_prev_close = data.get("spy")
        snap.gld_prev_close = data.get("gld")
        snap.dxy_prev_close = data.get("dxy")

    @staticmethod
    def _apply_eia(snap: MacroSnapshot, data: dict[str, Any]) -> None:
        snap.crude_inventory_change_mbbl = data.get("change_mbbl")

    @staticmethod
    def _apply_gdelt(snap: MacroSnapshot, data: dict[str, Any]) -> None:
        snap.gdelt_risk_tone = data.get("tone")

    # ── Composite derivation ──────────────────────────────────────────────

    @staticmethod
    def _derive_composites(snap: MacroSnapshot) -> None:
        # Yield curve
        if snap.t10y2y is not None:
            snap.yield_curve_inverted = snap.t10y2y < 0.0

        # USD strength (DTWEXBGS broad index — >110 strong, <95 weak)
        if snap.dtwexbgs is not None:
            if snap.dtwexbgs > 110:
                snap.usd_strength = "strong"
            elif snap.dtwexbgs < 95:
                snap.usd_strength = "weak"
            else:
                snap.usd_strength = "neutral"

        # Risk tier from VIX
        vix = snap.vixcls
        if vix is None:
            snap.risk_tier = "normal"
        elif vix >= 40:
            snap.risk_tier = "crisis"
        elif vix >= 25:
            snap.risk_tier = "elevated"
        elif vix < 15:
            snap.risk_tier = "low"
        else:
            snap.risk_tier = "normal"
