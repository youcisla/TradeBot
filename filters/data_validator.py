"""Market data sanity checks.

Catches stuck feeds, price spikes, and candle gaps before any data
reaches the Analysis or Strategy agents.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from config import settings
from models.market_data import Candle

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Raised when market data fails a sanity check."""


class DataValidator:
    """Stateful validator that tracks recent prices to detect stuck feeds."""

    def __init__(self) -> None:
        self._recent_prices: list[float] = []

    def validate_tick(self, bid: float, ask: float, spread: float) -> None:
        """Validate a single tick.  Raises DataValidationError on failure."""

        # Price must be positive and present
        if bid <= 0 or ask <= 0:
            raise DataValidationError(f"Invalid price: bid={bid}, ask={ask}")

        # Spread sanity
        if spread < 0:
            raise DataValidationError(f"Negative spread: {spread}")

        # Spike detection – compare to last known price
        if self._recent_prices:
            last = self._recent_prices[-1]
            if last > 0:
                change_pct = abs(bid - last) / last * 100
                if change_pct > settings.SPIKE_PERCENT_THRESHOLD:
                    raise DataValidationError(
                        f"Price spike: {last} → {bid} ({change_pct:.2f}%)"
                    )

        # Stuck quote detection
        self._recent_prices.append(bid)
        if len(self._recent_prices) > settings.STUCK_QUOTE_THRESHOLD:
            self._recent_prices = self._recent_prices[-settings.STUCK_QUOTE_THRESHOLD:]

        if (len(self._recent_prices) >= settings.STUCK_QUOTE_THRESHOLD
                and len(set(self._recent_prices)) == 1):
            raise DataValidationError(
                f"Stuck quote: price unchanged for {settings.STUCK_QUOTE_THRESHOLD} ticks ({bid})"
            )

    def validate_candles(self, candles: list[Candle], expected_gap: timedelta | None = None) -> None:
        """Check that candle timestamps are continuous."""
        if not candles or len(candles) < 2:
            return

        if expected_gap is None:
            expected_gap = timedelta(hours=1)  # default H1

        for i in range(1, len(candles)):
            gap = candles[i].timestamp - candles[i - 1].timestamp
            # Allow up to 1.5× expected gap to account for weekends / holidays
            if gap > expected_gap * 1.5:
                logger.warning(
                    "Candle gap: %s → %s (%.0f min, expected %.0f min)",
                    candles[i - 1].timestamp,
                    candles[i].timestamp,
                    gap.total_seconds() / 60,
                    expected_gap.total_seconds() / 60,
                )
