"""Market Agent — fetches live market data with sanity checks.

Answers: *What is the market doing?*
"""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from broker.connector import BrokerConnector
from config import settings
from filters.data_validator import DataValidationError, DataValidator
from models.market_data import Candle, MarketData
from utils.helpers import current_session

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
        # Cache slow-changing higher-timeframe candles to reduce MT5 round-trips.
        self._htf_cache: dict[tuple[str, str, int], tuple[float, list[Candle]]] = {}
        self._htf_cache_base_ttl_seconds: dict[str, float] = {
            "M15": settings.HTF_CACHE_TTL_M15_SECONDS,
            "M30": settings.HTF_CACHE_TTL_M30_SECONDS,
            "H4": settings.HTF_CACHE_TTL_H4_SECONDS,
            "D1": settings.HTF_CACHE_TTL_D1_SECONDS,
        }

    def _validator(self, symbol: str) -> DataValidator:
        if symbol not in self._validators:
            self._validators[symbol] = DataValidator(db=self._db)
        return self._validators[symbol]

    @staticmethod
    def _session_profile() -> str:
        session_name = current_session(datetime.now(UTC))
        if session_name in {"london", "newyork", "overlap"}:
            return "london_ny"
        return "asia"

    def _htf_ttl_seconds(self, timeframe: str, session_profile: str) -> float:
        base = self._htf_cache_base_ttl_seconds.get(timeframe, 30.0)
        if session_profile == "london_ny":
            return max(5.0, base * settings.HTF_CACHE_TTL_MULTIPLIER_LONDON_NY)
        return max(5.0, base * settings.HTF_CACHE_TTL_MULTIPLIER_ASIA)

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
        validator.validate_tick(bid, ask, spread, symbol=symbol)

        session_profile = self._session_profile()

        candles = self._get_candles(symbol)
        m30_candles = self._get_htf_candles(symbol, "M30", settings.M30_CANDLE_COUNT, session_profile)
        m15_candles = self._get_htf_candles(symbol, "M15", settings.M15_CANDLE_COUNT, session_profile)
        h4_candles = self._get_htf_candles(symbol, "H4", settings.H4_CANDLE_COUNT, session_profile)
        d1_candles = self._get_htf_candles(symbol, "D1", settings.D1_CANDLE_COUNT, session_profile)

        self._emit("info",
                   f"{symbol} — bid={bid:.5f} spread={spread:.5f} "
                   f"h1={len(candles)} m30={len(m30_candles)} m15={len(m15_candles)} "
                   f"h4={len(h4_candles)} d1={len(d1_candles)} vol={volume:.0f}",
                   {"bid": bid, "ask": ask, "spread": spread,
                    "volume": volume, "candles": len(candles),
                    "m30": len(m30_candles), "m15": len(m15_candles),
                    "last_close": candles[-1].close if candles else None})

        return MarketData(
            symbol=symbol,
            bid=bid,
            ask=ask,
            spread=spread,
            volume=volume,
            candles=candles,
            m30_candles=m30_candles,
            m15_candles=m15_candles,
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

    def _get_htf_candles(
        self,
        symbol: str,
        timeframe: str,
        count: int,
        session_profile: str,
    ) -> list[Candle]:
        """Fetch higher-timeframe candles; returns [] silently on failure."""
        cache_key = (symbol, timeframe, count)
        now = time.monotonic()
        ttl = self._htf_ttl_seconds(timeframe, session_profile)
        cached = self._htf_cache.get(cache_key)
        if cached is not None:
            fetched_at, candles = cached
            if now - fetched_at <= ttl:
                return candles

        try:
            candles = self._broker.get_candles(symbol, timeframe, count=count) or []
            self._htf_cache[cache_key] = (now, candles)
            return candles
        except Exception:
            logger.debug("HTF candles unavailable for %s %s", symbol, timeframe)
            return []
