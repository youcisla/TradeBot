"""Tradeable symbols configuration for V1."""

from __future__ import annotations

# V1 trades a single symbol on a single timeframe.
SYMBOLS: list[str] = ["EURUSD"]

# Per-symbol pip value (price movement per pip).
# For 5-digit forex pairs 1 pip = 0.0001; for JPY pairs 0.01; for XAUUSD 0.1
PIP_VALUES: dict[str, float] = {
    "EURUSD": 0.0001,
    "GBPUSD": 0.0001,
    "USDJPY": 0.01,
    "XAUUSD": 0.1,
}


def pip_value(symbol: str) -> float:
    """Return the pip size for *symbol*, defaulting to 0.0001."""
    return PIP_VALUES.get(symbol, 0.0001)
