"""Spread Monitor — tracks live spread and classifies conditions.

Monitors spread in pips with running statistics (average, min, max, std-dev)
and provides filter methods for trade execution gating.

Inspired by: Algosphere SpreadMonitor.mqh
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from enum import IntEnum

from config import settings


class SpreadCondition(IntEnum):
    LOW = 0     # Below low threshold — ideal for trading
    NORMAL = 1  # Within normal range
    HIGH = 2    # Above normal — proceed with caution
    EXTREME = 3 # Spread blowout — reject new entries


@dataclass
class SpreadStats:
    current: float = 0.0
    average: float = 0.0
    minimum: float = math.inf
    maximum: float = 0.0
    std_dev: float = 0.0
    sample_count: int = 0
    condition: SpreadCondition = SpreadCondition.NORMAL


class SpreadMonitor:
    """Tracks spread history and classifies current spread conditions.

    Uses a rolling window of spread samples to compute running statistics.
    Thresholds are configurable via constructor or ``set_thresholds()``.

    Parameters
    ----------
    history_size : int
        Maximum number of spread samples to retain (circular buffer).
    threshold_low : float
        Pip value below which spread is classified LOW.
    threshold_normal : float
        Pip value below which spread is classified NORMAL.
    threshold_high : float
        Pip value above which spread is classified EXTREME.
    pip_size : float
        Pip size in price units for the symbol (e.g. 0.0001 for EURUSD).
    """

    def __init__(
        self,
        history_size: int = 1000,
        threshold_low: float = 1.0,
        threshold_normal: float = 2.0,
        threshold_high: float = 5.0,
        pip_size: float = 0.0001,
    ) -> None:
        self._history: deque[float] = deque(maxlen=history_size)
        self._threshold_low = threshold_low
        self._threshold_normal = threshold_normal
        self._threshold_high = threshold_high
        self._pip_size = pip_size

        # Running statistics (Welford's online algorithm for stable std-dev)
        self._count: int = 0
        self._mean: float = 0.0
        self._M2: float = 0.0   # sum of squared deviations
        self._min: float = math.inf
        self._max: float = 0.0

    # ── Record ────────────────────────────────────────────────────────────

    def record(self, spread_pips: float) -> None:
        """Add a new spread sample (in pips)."""
        if spread_pips < 0:
            return

        # Welford's online algorithm for stable mean/variance
        self._count += 1
        delta = spread_pips - self._mean
        self._mean += delta / self._count
        delta2 = spread_pips - self._mean
        self._M2 += delta * delta2

        self._min = min(self._min, spread_pips)
        self._max = max(self._max, spread_pips)
        self._history.append(spread_pips)

    # ── Query ─────────────────────────────────────────────────────────────

    @property
    def current(self) -> float:
        """Most recent spread in pips, or 0 if no samples."""
        return self._history[-1] if self._history else 0.0

    @property
    def average(self) -> float:
        """Rolling mean spread in pips."""
        return self._mean

    @property
    def minimum(self) -> float:
        """Minimum recorded spread in pips."""
        return self._min if self._count > 0 else 0.0

    @property
    def maximum(self) -> float:
        """Maximum recorded spread in pips."""
        return self._max

    @property
    def std_dev(self) -> float:
        """Population standard deviation of recorded spreads."""
        if self._count < 2:
            return 0.0
        variance = self._M2 / self._count
        return math.sqrt(max(0.0, variance))

    @property
    def condition(self) -> SpreadCondition:
        """Current spread condition classification."""
        return self._condition_for(self.current)

    @property
    def stats(self) -> SpreadStats:
        """All statistics as a dataclass."""
        return SpreadStats(
            current=self.current,
            average=self.average,
            minimum=self.minimum,
            maximum=self.maximum,
            std_dev=self.std_dev,
            sample_count=self._count,
            condition=self.condition,
        )

    # ── Filters ───────────────────────────────────────────────────────────

    def is_acceptable(self, max_spread_pips: float | None = None) -> bool:
        """Return True if current spread is below the max acceptable threshold.

        Uses ``settings.MAX_SPREAD_PIPS`` if no override is provided.
        """
        threshold = max_spread_pips if max_spread_pips is not None else settings.MAX_SPREAD_PIPS
        return self.current <= threshold

    def is_below_average(self, multiplier: float = 1.0) -> bool:
        """Return True if current spread is at or below average * multiplier."""
        if self._count == 0:
            return True
        return self.current <= self._mean * multiplier

    def is_stable(self, periods: int = 10, tolerance: float = 0.5) -> bool:
        """Return True if spread has been stable for the last N periods.

        Checks that the deviation from the recent average is within ``tolerance`` pips.
        """
        if self._count < periods:
            return False

        recent = list(self._history)[-periods:]
        recent_avg = sum(recent) / len(recent)
        return abs(self.current - recent_avg) <= tolerance

    # ── Configuration ─────────────────────────────────────────────────────

    def set_thresholds(
        self,
        low: float,
        normal: float,
        high: float,
    ) -> None:
        """Update the spread condition thresholds (all in pips)."""
        self._threshold_low = low
        self._threshold_normal = normal
        self._threshold_high = high

    # ── Internal ────────────────────────────────────────────────────────────

    def _condition_for(self, spread_pips: float) -> SpreadCondition:
        if spread_pips <= self._threshold_low:
            return SpreadCondition.LOW
        if spread_pips <= self._threshold_normal:
            return SpreadCondition.NORMAL
        if spread_pips <= self._threshold_high:
            return SpreadCondition.HIGH
        return SpreadCondition.EXTREME

    def __repr__(self) -> str:
        return (
            f"SpreadMonitor(current={self.current:.1f}pips "
            f"avg={self.average:.1f} condition={self.condition.name} "
            f"n={self._count})"
        )
