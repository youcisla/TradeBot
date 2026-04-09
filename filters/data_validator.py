"""Market data sanity checks.

Catches stuck feeds, price spikes, and candle gaps before any data
reaches the Analysis or Strategy agents.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import TYPE_CHECKING

from config import settings
from config.symbols import asset_class
from models.market_data import Candle

if TYPE_CHECKING:
    from database.db import Database

logger = logging.getLogger(__name__)


class DataValidationError(Exception):
    """Raised when market data fails a sanity check."""


class DataValidator:
    """Stateful validator that tracks recent prices to detect stuck feeds."""

    def __init__(self, db: Database | None = None) -> None:
        self._recent_prices: list[float] = []
        self._db = db

    def validate_tick(
        self,
        bid: float,
        ask: float,
        spread: float,
        symbol: str | None = None,
    ) -> None:
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
                    self._emit("warn",
                               f"Price spike detected: {last:.5f} → {bid:.5f} ({change_pct:.2f}%)",
                               {"last": last, "bid": bid, "change_pct": change_pct})
                    raise DataValidationError(
                        f"Price spike: {last} → {bid} ({change_pct:.2f}%)"
                    )

        # Stuck quote detection
        threshold = settings.STUCK_QUOTE_THRESHOLD
        if symbol and asset_class(symbol) == "crypto":
            threshold = settings.STUCK_QUOTE_THRESHOLD_CRYPTO

        self._recent_prices.append(bid)
        if len(self._recent_prices) > threshold:
            self._recent_prices = self._recent_prices[-threshold:]

        if (len(self._recent_prices) >= threshold
                and len(set(self._recent_prices)) == 1):
            self._emit("warn",
                       f"Stuck quote: price unchanged for {threshold} ticks ({bid})",
                       {"bid": bid, "ticks": threshold, "symbol": symbol})
            raise DataValidationError(
                f"Stuck quote: price unchanged for {threshold} ticks ({bid})"
            )

    def validate_candles(self, candles: list[Candle], expected_gap: timedelta | None = None) -> None:
        """Check that candle timestamps are continuous."""
        if not candles or len(candles) < 2:
            return

        if expected_gap is None:
            expected_gap = timedelta(hours=1)  # default H1

        # Allow larger gaps for weekends (Fri 22:00 to Sun 22:00 = ~48h)
        # and known server maintenance windows
        max_tolerable = timedelta(hours=50)

        for i in range(1, len(candles)):
            gap = candles[i].timestamp - candles[i - 1].timestamp
            # Allow up to 1.5× expected gap for minor delays
            if gap <= expected_gap * 1.5:
                continue
            # Silently skip weekend/maintenance gaps (< 50h)
            if gap <= max_tolerable:
                continue
            # Only warn on truly anomalous gaps (>50h = not a weekend/maintenance gap)
            # Weekend gaps (Fri 22:00 → Mon 16:00 ≈ 66h) are normal market structure
            # and should not be treated as errors — log at INFO level.
            logger.info(
                "Candle gap: %s → %s (%.0f min, expected %.0f min) — normal weekend/maintenance gap",
                candles[i - 1].timestamp,
                candles[i].timestamp,
                gap.total_seconds() / 60,
                expected_gap.total_seconds() / 60,
            )
            self._emit("warn",
                       f"Candle gap: {gap.total_seconds()/60:.0f}min between "
                       f"{candles[i-1].timestamp} and {candles[i].timestamp}",
                       {"gap_min": gap.total_seconds() / 60})

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("market", level, msg, data)
