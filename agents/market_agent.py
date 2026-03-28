"""Market Agent — fetches live market data with sanity checks.

Answers: *What is the market doing?*
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from broker.connector import BrokerConnector
from config import settings
from filters.data_validator import DataValidationError, DataValidator
from models.market_data import Candle, MarketData

if TYPE_CHECKING:
    from database.db import Database

logger = logging.getLogger(__name__)


class MarketAgent:
    """Fetches and validates market data before passing it downstream."""

    def __init__(
        self,
        broker: BrokerConnector,
        db: Database | None = None,
        candle_count: int = 100,
    ) -> None:
        self._broker = broker
        self._db = db
        self._validators: dict[str, DataValidator] = {}
        self._candle_count = candle_count

    def _validator(self, symbol: str) -> DataValidator:
        if symbol not in self._validators:
            self._validators[symbol] = DataValidator(db=self._db)
        return self._validators[symbol]

    def get_data(self, symbol: str) -> MarketData:
        """Return a validated MarketData snapshot.

        Raises ``DataValidationError`` if the data fails sanity checks —
        the main loop should catch this and skip the iteration.
        """
        logger.debug("Scanning %s — pulling live tick data...", symbol)
        try:
            tick = self._broker.get_tick(symbol)
        except Exception as exc:
            # Log to file only — main loop emits a single consolidated DB event
            # when it detects a full IPC loss, avoiding agent-feed spam.
            logger.warning("No tick data for %s: %s", symbol, exc)
            raise DataValidationError(f"No tick data for {symbol}: {exc}") from exc

        bid = tick["bid"]
        ask = tick["ask"]
        spread = tick["spread"]
        volume = tick.get("volume", 0.0)

        # Validate
        validator = self._validator(symbol)
        validator.validate_tick(bid, ask, spread)

        candles    = self._get_candles(symbol)
        h4_candles = self._get_htf_candles(symbol, "H4", settings.H4_CANDLE_COUNT)
        d1_candles = self._get_htf_candles(symbol, "D1", settings.D1_CANDLE_COUNT)

        self._emit("info",
                   f"{symbol} — bid={bid:.5f} spread={spread:.5f} "
                   f"candles={len(candles)} h4={len(h4_candles)} d1={len(d1_candles)} vol={volume:.0f}",
                   {"bid": bid, "ask": ask, "spread": spread,
                    "volume": volume, "candles": len(candles),
                    "last_close": candles[-1].close if candles else None})

        return MarketData(
            symbol=symbol,
            bid=bid,
            ask=ask,
            spread=spread,
            volume=volume,
            candles=candles,
            h4_candles=h4_candles,
            d1_candles=d1_candles,
        )

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("market", level, msg, data)

    def _get_candles(self, symbol: str) -> list[Candle]:
        try:
            candles = self._broker.get_candles(
                symbol, settings.DEFAULT_TIMEFRAME, count=self._candle_count,
            )
            validator = self._validator(symbol)
            validator.validate_candles(candles)
            return candles
        except DataValidationError:
            raise
        except Exception:
            logger.warning("Failed to fetch candles for %s", symbol, exc_info=True)
            return []

    def _get_htf_candles(self, symbol: str, timeframe: str, count: int) -> list[Candle]:
        """Fetch higher-timeframe candles; returns [] silently on failure."""
        try:
            return self._broker.get_candles(symbol, timeframe, count=count) or []
        except Exception:
            logger.debug("HTF candles unavailable for %s %s", symbol, timeframe)
            return []
