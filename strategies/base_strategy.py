"""Abstract base class for all trading strategies."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from models.market_data import MarketContext
from models.signal import Signal


class BaseStrategy(ABC):
    """Every concrete strategy must inherit from this class."""

    name: str = "unnamed"

    @abstractmethod
    def detect(self, context: MarketContext) -> Optional[Signal]:
        """Return a Signal if a setup is found, or None."""

    @abstractmethod
    def calculate_sl(self, context: MarketContext, direction: str) -> float:
        """Calculate stop-loss price for this setup."""

    @abstractmethod
    def calculate_tps(
        self, context: MarketContext, entry: float, sl: float, direction: str
    ) -> tuple[float, float, float]:
        """Return (TP1, TP2, TP3) prices."""
