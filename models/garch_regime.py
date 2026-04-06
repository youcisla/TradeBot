"""garch_regime.py — GARCH(1,1) volatility regime detector.

Estimates a rolling GARCH(1,1) model on recent returns to classify the
current volatility regime as one of:

    ``low``      — conditional σ < 0.8× historical mean
    ``normal``   — near historical mean
    ``high``     — conditional σ > GARCH_HIGH_VOL_THRESHOLD × historical mean
    ``extreme``  — conditional σ > 3× historical mean

When the ``arch`` package is available it is used for maximum-likelihood
estimation. Otherwise, an analytic EWMA fall-back (single exponential
smoothing of squared returns) is used — GARCH-lite, sufficient for regime
classification.

Usage::

    from models.garch_regime import GarchRegimeDetector

    detector = GarchRegimeDetector(symbol="EURUSD")
    detector.update(ret=-0.0012)      # feed one log-return
    regime = detector.regime          # "low" | "normal" | "high" | "extreme"
    sigma = detector.conditional_vol  # annualised volatility estimate
"""

from __future__ import annotations

import logging
import math
from collections import deque

from config import settings

logger = logging.getLogger(__name__)

Regime = str  # "low" | "normal" | "high" | "extreme"


class GarchRegimeDetector:
    """Rolling volatility regime classifier backed by GARCH(1,1) or EWMA.

    Parameters
    ----------
    window : int
        Minimum number of return observations before the model fires.
    max_history : int
        Maximum observations kept in the rolling window.
    ewma_lambda : float
        Decay parameter for the EWMA fall-back (RiskMetrics standard: 0.94).
    """

    def __init__(
        self,
        symbol: str = "",
        *,
        window: int = 60,
        max_history: int = 500,
        ewma_lambda: float = 0.94,
    ) -> None:
        self.symbol = symbol
        self._window = window
        self._lambda = ewma_lambda
        self._returns: deque[float] = deque(maxlen=max_history)
        self._ewma_var: float | None = None
        self._garch_enabled = settings.GARCH_ENABLED

        self._regime: Regime = "normal"
        self._cond_vol: float = 0.0             # annualised
        self._threshold = settings.GARCH_HIGH_VOL_THRESHOLD

    # ── Public API ────────────────────────────────────────────────────────

    @property
    def regime(self) -> Regime:
        return self._regime

    @property
    def conditional_vol(self) -> float:
        """Current conditional annualised volatility estimate."""
        return self._cond_vol

    @property
    def is_high_vol(self) -> bool:
        return self._regime in ("high", "extreme")

    def update(self, ret: float) -> None:
        """Feed one log-return (e.g. log(close/prev_close)).

        Call once per closed candle.
        """
        self._returns.append(ret)
        if len(self._returns) < self._window:
            return

        if self._garch_enabled:
            self._cond_vol = self._estimate_garch_vol()
        else:
            self._cond_vol = self._estimate_ewma_vol(ret)

        self._classify()

    def update_price(self, price: float, prev_price: float) -> None:
        """Convenience wrapper — feeds log-return computed from two prices."""
        if prev_price and prev_price > 0:
            ret = math.log(price / prev_price)
            self.update(ret)

    # ── Internal helpers ──────────────────────────────────────────────────

    def _estimate_garch_vol(self) -> float:
        """Try arch.arch_model GARCH(1,1); fall back to EWMA on failure."""
        if not self._returns:
            return self._cond_vol

        ret = self._returns[-1]
        ewma = self._estimate_ewma_vol(ret)

        try:
            import numpy as np  # noqa: PLC0415
            from arch import arch_model  # type: ignore[import] # noqa: PLC0415

            returns_arr = np.array(list(self._returns)) * 10_000  # pip-scale returns (avoids DataScaleWarning)
            am = arch_model(returns_arr, vol="Garch", p=1, q=1, dist="normal", rescale=False)
            with _suppress_arch_output():
                res = am.fit(disp="off", show_warning=False)
            # Last conditional variance (percentage²) → annualised vol
            last_var = float(res.conditional_volatility[-1]) / 10_000
            # Annualise: assuming 252 trading days, 24 candles per day (H1)
            ann_vol = last_var * math.sqrt(252 * 24)
            return ann_vol
        except Exception as exc:  # noqa: BLE001
            logger.debug("GARCH estimation failed, using EWMA: %s", exc)
            return ewma

    def _estimate_ewma_vol(self, ret: float) -> float:
        """EWMA variance update (RiskMetrics roll)."""
        r2 = ret * ret
        if self._ewma_var is None:
            # Seed with recent sample variance
            rets = list(self._returns)
            mean = sum(rets) / len(rets)
            self._ewma_var = sum((r - mean) ** 2 for r in rets) / len(rets)
        else:
            self._ewma_var = self._lambda * self._ewma_var + (1 - self._lambda) * r2
        # Annualise (H1 data: 252 days × 24 bars)
        return math.sqrt(self._ewma_var * 252 * 24)

    def _classify(self) -> None:
        """Map conditional vol to a regime label relative to recent history."""
        if len(self._returns) < self._window:
            self._regime = "normal"
            return

        rets = list(self._returns)
        mean_abs = sum(abs(r) for r in rets) / len(rets)
        hist_vol = mean_abs * math.sqrt(252 * 24) * math.sqrt(math.pi / 2)

        if hist_vol == 0:
            self._regime = "normal"
            return

        ratio = self._cond_vol / hist_vol

        if ratio >= 3.0:
            self._regime = "extreme"
        elif ratio >= self._threshold:
            self._regime = "high"
        elif ratio <= 0.8:
            self._regime = "low"
        else:
            self._regime = "normal"


class _suppress_arch_output:
    """Context manager: suppress stdout from arch model fitting."""

    def __enter__(self):
        import sys
        import os
        self._devnull = open(os.devnull, "w")
        self._old_stdout = sys.stdout
        sys.stdout = self._devnull
        return self

    def __exit__(self, *_):
        import sys
        sys.stdout = self._old_stdout
        self._devnull.close()
