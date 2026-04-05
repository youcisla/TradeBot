"""macro_features.py — FRED + yfinance macro indicators as ML features.

Produces a fixed-length float vector suitable for feeding into LGBM,
neural networks, or any model that needs macro context.

Feature vector layout (15 features, all z-scored or logically bounded):

    [0]  dgs10          — 10-Y Treasury yield (%)
    [1]  dgs2           — 2-Y Treasury yield (%)
    [2]  t10y2y         — Yield spread / inversion flag rescaled
    [3]  vixcls         — VIX level
    [4]  dtwexbgs       — USD broad index
    [5]  dcoilwtico     — WTI crude (USD/bbl)
    [6]  fedfunds       — Effective Fed Funds rate (%)
    [7]  m2sl_yoy       — M2 YoY growth (estimated from latest observation)
    [8]  unrate         — Unemployment rate (%)
    [9]  cpi_yoy        — CPI YoY estimate
    [10] spy_ret        — S&P 500 1-day return proxy
    [11] gld_ret        — Gold 1-day return proxy (risk-off signal)
    [12] dxy_level      — DXY level rescaled to [0, 1] over 80-120 range
    [13] crude_draw     — EIA weekly crude change (million bbl, clipped ±10)
    [14] gdelt_tone     — GDELT global risk tone (-1 … +1)

Missing values are filled with 0.0 (neutral).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from filters.intelligence_sweep import MacroSnapshot


# ── Feature metadata ──────────────────────────────────────────────────────
FEATURE_NAMES: list[str] = [
    "dgs10", "dgs2", "t10y2y", "vixcls", "dtwexbgs",
    "dcoilwtico", "fedfunds", "m2sl_yoy_est", "unrate", "cpi_yoy_est",
    "spy_1d_ret", "gld_1d_ret", "dxy_norm", "eia_crude_draw_mbbl",
    "gdelt_tone",
]

FEATURE_DIM = len(FEATURE_NAMES)


@dataclass
class MacroFeatureVector:
    values: list[float]
    names: list[str]
    built_at: datetime

    def to_dict(self) -> dict[str, float]:
        return dict(zip(self.names, self.values))


class MacroFeatureBuilder:
    """Converts a ``MacroSnapshot`` into a normalised feature vector."""

    # Running stats for online z-scoring (naive exponential moving estimates).
    # Pre-seeded with approximate historical means and stds.
    _MEANS: dict[str, float] = {
        "dgs10": 3.5, "dgs2": 3.0, "t10y2y": 0.5, "vixcls": 20.0,
        "dtwexbgs": 103.0, "dcoilwtico": 75.0, "fedfunds": 3.0,
        "m2sl_yoy_est": 5.0, "unrate": 4.5, "cpi_yoy_est": 3.0,
        "spy_1d_ret": 0.0, "gld_1d_ret": 0.0, "dxy_norm": 0.5,
        "eia_crude_draw_mbbl": 0.0, "gdelt_tone": 0.0,
    }

    _STDS: dict[str, float] = {
        "dgs10": 1.5, "dgs2": 1.5, "t10y2y": 1.0, "vixcls": 10.0,
        "dtwexbgs": 8.0, "dcoilwtico": 20.0, "fedfunds": 1.5,
        "m2sl_yoy_est": 4.0, "unrate": 1.5, "cpi_yoy_est": 2.0,
        "spy_1d_ret": 1.0, "gld_1d_ret": 1.0, "dxy_norm": 0.2,
        "eia_crude_draw_mbbl": 3.0, "gdelt_tone": 1.0,
    }

    def __init__(self, *, z_score: bool = True) -> None:
        self._z_score = z_score
        self._prev_spy: float | None = None
        self._prev_gld: float | None = None

    def build(self, snap: "MacroSnapshot") -> MacroFeatureVector:
        raw = self._extract_raw(snap)
        if self._z_score:
            values = self._normalise(raw)
        else:
            values = [raw.get(n, 0.0) for n in FEATURE_NAMES]

        return MacroFeatureVector(
            values=values,
            names=FEATURE_NAMES[:],
            built_at=datetime.now(timezone.utc),
        )

    # ── Internal helpers ──────────────────────────────────────────────────

    def _extract_raw(self, snap: "MacroSnapshot") -> dict[str, float]:
        # Simple YoY estimates from level data (rough proxy).
        m2sl_yoy = snap.m2sl * 0.05 if snap.m2sl else 0.0
        cpi_yoy = snap.cpiaucsl * 0.025 if snap.cpiaucsl else 0.0

        # Intraday returns from previous-close data.
        spy_ret = 0.0
        if self._prev_spy and snap.spy_prev_close:
            spy_ret = (snap.spy_prev_close - self._prev_spy) / self._prev_spy * 100
        self._prev_spy = snap.spy_prev_close

        gld_ret = 0.0
        if self._prev_gld and snap.gld_prev_close:
            gld_ret = (snap.gld_prev_close - self._prev_gld) / self._prev_gld * 100
        self._prev_gld = snap.gld_prev_close

        # DXY normalised to [0, 1] over 80-120 band.
        dxy_raw = snap.dxy_prev_close or snap.dtwexbgs or 100.0
        dxy_norm = max(0.0, min(1.0, (dxy_raw - 80) / 40))

        crude_draw = float(snap.crude_inventory_change_mbbl or 0.0)
        crude_draw = max(-10.0, min(10.0, crude_draw))

        return {
            "dgs10": snap.dgs10 or 0.0,
            "dgs2": snap.dgs2 or 0.0,
            "t10y2y": snap.t10y2y or 0.0,
            "vixcls": snap.vixcls or 20.0,
            "dtwexbgs": snap.dtwexbgs or 103.0,
            "dcoilwtico": snap.dcoilwtico or 75.0,
            "fedfunds": snap.fedfunds or 0.0,
            "m2sl_yoy_est": m2sl_yoy,
            "unrate": snap.unrate or 0.0,
            "cpi_yoy_est": cpi_yoy,
            "spy_1d_ret": spy_ret,
            "gld_1d_ret": gld_ret,
            "dxy_norm": dxy_norm,
            "eia_crude_draw_mbbl": crude_draw,
            "gdelt_tone": float(snap.gdelt_risk_tone or 0.0),
        }

    def _normalise(self, raw: dict[str, float]) -> list[float]:
        out: list[float] = []
        for name in FEATURE_NAMES:
            val = raw.get(name, 0.0)
            mean = self._MEANS.get(name, 0.0)
            std = self._STDS.get(name, 1.0) or 1.0
            z = (val - mean) / std
            # Hard clip to [-4, 4] to avoid extreme outliers poisoning models.
            z = max(-4.0, min(4.0, z))
            out.append(round(z, 6))
        return out


def _safe(val: float | None, default: float = 0.0) -> float:
    if val is None or math.isnan(val):
        return default
    return val
