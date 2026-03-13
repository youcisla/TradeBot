"""Backtesting engine — stub for Phase 1.

This module will be implemented in a later phase. The interface is
defined here so that imports don't break and the project structure
is in place.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class BacktestEngine:
    """Placeholder backtesting engine — Phase 2+."""

    def __init__(self) -> None:
        logger.info("BacktestEngine initialised (stub — not yet implemented)")

    def run(self, symbol: str, start: str, end: str) -> dict:
        raise NotImplementedError("Backtesting engine is not yet implemented")
