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

    def __init__(self, broker: BrokerConnector, db: Database | None = None) -> None:
        self._broker = broker
        self._db = db
        self._validators: dict[str, DataValidator] = {}

    def _validator(self, symbol: str) -> DataValidator:
        if symbol not in self._validators:
            self._validators[symbol] = DataValidator(db=self._db)
        return self._validators[symbol]

    def get_data(self, symbol: str) -> MarketData:
        """Return a validated MarketData snapshot.

        Raises ``DataValidationError`` if the data fails sanity checks —
        the main loop should catch this and skip the iteration.
        """
        self._emit("info", f"Scanning {symbol} — pulling live tick data...")
        try:
            tick = self._broker.get_tick(symbol)
        except Exception as exc:
            self._emit("error", f"Lost connection to {symbol} feed: {exc}")
            raise DataValidationError(f"Failed to fetch tick for {symbol}: {exc}") from exc

        bid = tick["bid"]
        ask = tick["ask"]
        spread = tick["spread"]
        volume = tick.get("volume", 0.0)

        # Validate
        validator = self._validator(symbol)
        validator.validate_tick(bid, ask, spread)

        candles = self._get_candles(symbol)

        self._emit("info",
                   f"{symbol} feed healthy — bid={bid:.5f} ask={ask:.5f} spread={spread:.5f} "
                   f"vol={volume:.0f} candles={len(candles)}",
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
        )

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("market", level, msg, data)

    def _get_candles(self, symbol: str) -> list[Candle]:
        try:
            candles = self._broker.get_candles(
                symbol, settings.DEFAULT_TIMEFRAME, count=250,
            )
            validator = self._validator(symbol)
            validator.validate_candles(candles)
            if candles:
                hi = max(c.high for c in candles[-14:])
                lo = min(c.low for c in candles[-14:])
                self._emit("info",
                           f"{symbol} {settings.DEFAULT_TIMEFRAME} candles OK — "
                           f"count={len(candles)} 14-bar range={hi:.5f}/{lo:.5f}",
                           {"count": len(candles), "high_14": hi, "low_14": lo,
                            "open": candles[-1].open, "close": candles[-1].close})
            return candles
        except DataValidationError:
            raise
        except Exception:
            logger.warning("Failed to fetch candles for %s", symbol, exc_info=True)
            return []
