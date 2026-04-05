"""kalman_filter.py — online Kalman filter for mid-price smoothing.

Implements a 1-D constant-velocity Kalman filter useful for removing
high-frequency microstructure noise from bid/ask mid-prices.

Usage::

    from utils.kalman_filter import KalmanPriceFilter

    kf = KalmanPriceFilter(symbol="EURUSD")
    smoothed = kf.update(1.08450)   # returns filtered mid-price
    velocity = kf.velocity          # estimated price velocity (pip/tick)
"""

from __future__ import annotations

import math


class KalmanPriceFilter:
    """Univariate scalar Kalman filter for mid-price smoothing.

    State vector: [price, velocity]
    Measurement: raw mid-price

    Parameters
    ----------
    process_noise_q : float
        Process noise covariance. Higher → filter reacts faster but is noisier.
        Typical range 1e-5 (very smooth) … 1e-3 (very reactive).
    measurement_noise_r : float
        Measurement noise variance. Higher → filter trusts measurements less.
    """

    def __init__(
        self,
        symbol: str = "",
        *,
        process_noise_q: float = 1e-4,
        measurement_noise_r: float = 1e-3,
    ) -> None:
        self.symbol = symbol
        self._q = process_noise_q
        self._r = measurement_noise_r

        # State estimate [price, velocity]
        self._x = [0.0, 0.0]
        # Covariance matrix (2×2, stored as flat [p00, p01, p10, p11])
        self._p = [1.0, 0.0, 0.0, 1.0]

        self._initialised = False

    @property
    def price(self) -> float:
        return self._x[0]

    @property
    def velocity(self) -> float:
        return self._x[1]

    @property
    def uncertainty(self) -> float:
        """1-σ uncertainty of the current price estimate."""
        return math.sqrt(max(0.0, self._p[0]))

    def update(self, measurement: float) -> float:
        """Feed one raw price observation; return the filtered estimate."""
        if not self._initialised:
            self._x[0] = measurement
            self._x[1] = 0.0
            self._initialised = True
            return measurement

        # ── Predict ──────────────────────────────────────────────────────
        # F = [[1, 1], [0, 1]]  (constant-velocity transition)
        x0 = self._x[0] + self._x[1]
        x1 = self._x[1]

        # P = F @ P @ F.T + Q
        p00, p01, p10, p11 = self._p
        # F @ P
        fp00 = p00 + p10
        fp01 = p01 + p11
        fp10 = p10
        fp11 = p11
        # (F @ P) @ F.T
        self._p[0] = fp00 + fp01 + self._q
        self._p[1] = fp01
        self._p[2] = fp10 + fp11
        self._p[3] = fp11 + self._q
        p00 = self._p[0]
        p01 = self._p[1]
        p10 = self._p[2]
        p11 = self._p[3]

        # ── Update ────────────────────────────────────────────────────────
        # H = [1, 0]  → only observe position
        s = p00 + self._r          # innovation covariance
        k0 = p00 / s               # Kalman gain for position
        k1 = p10 / s               # Kalman gain for velocity

        innov = measurement - x0
        self._x[0] = x0 + k0 * innov
        self._x[1] = x1 + k1 * innov

        # P = (I - K @ H) @ P
        self._p[0] = (1 - k0) * p00
        self._p[1] = (1 - k0) * p01
        self._p[2] = p10 - k1 * p00
        self._p[3] = p11 - k1 * p01

        return self._x[0]

    def reset(self) -> None:
        """Reset state — call when a trading session ends or gap is detected."""
        self._x = [0.0, 0.0]
        self._p = [1.0, 0.0, 0.0, 1.0]
        self._initialised = False
