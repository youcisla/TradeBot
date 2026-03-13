"""Market Agent — fetches live market data with sanity checks.

Answers: *What is the market doing?*
"""

from __future__ import annotations

import logging

from broker.connector import BrokerConnector
from config import settings
from filters.data_validator import DataValidationError, DataValidator
from models.market_data import Candle, MarketData

logger = logging.getLogger(__name__)


class MarketAgent:
    """Fetches and validates market data before passing it downstream."""

    def __init__(self, broker: BrokerConnector) -> None:
        self._broker = broker
        self._validators: dict[str, DataValidator] = {}

    def _validator(self, symbol: str) -> DataValidator:
        if symbol not in self._validators:
            self._validators[symbol] = DataValidator()
        return self._validators[symbol]

    def get_data(self, symbol: str) -> MarketData:
        """Return a validated MarketData snapshot.

        Raises ``DataValidationError`` if the data fails sanity checks —
        the main loop should catch this and skip the iteration.
        """
        try:
            tick = self._broker.get_tick(symbol)
        except Exception as exc:
            raise DataValidationError(f"Failed to fetch tick for {symbol}: {exc}") from exc

        bid = tick["bid"]
        ask = tick["ask"]
        spread = tick["spread"]
        volume = tick.get("volume", 0.0)

        # Validate
        validator = self._validator(symbol)
        validator.validate_tick(bid, ask, spread)

        candles = self._get_candles(symbol)

        return MarketData(
            symbol=symbol,
            bid=bid,
            ask=ask,
            spread=spread,
            volume=volume,
            candles=candles,
        )

    def _get_candles(self, symbol: str) -> list[Candle]:
        try:
            candles = self._broker.get_candles(
                symbol, settings.DEFAULT_TIMEFRAME, count=100,
            )
            validator = self._validator(symbol)
            validator.validate_candles(candles)
            return candles
        except DataValidationError:
            raise
        except Exception:
            logger.warning("Failed to fetch candles for %s", symbol, exc_info=True)
            return []
