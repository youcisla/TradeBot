"""Tradeable symbols configuration.

Symbols are grouped by asset class.  The bot iterates over
``ACTIVE_SYMBOLS`` each loop tick.  Add / remove from that list
(or via the ACTIVE_SYMBOLS env var) without touching other code.
"""

from __future__ import annotations

import os

# ── All known symbols by asset class ────────────────────────────────────

FOREX_MAJORS: list[str] = [
    "EURUSD", "USDJPY", "GBPUSD", "AUDUSD",
    "USDCAD", "USDCHF",
]

FOREX_CROSSES: list[str] = [
    "EURJPY", "GBPJPY", "EURGBP", "AUDJPY", "EURAUD",
    "EURCAD", "GBPCHF", "GBPAUD", "CADJPY", "CHFJPY",
    "EURCHF", "NZDJPY",
]

COMMODITIES: list[str] = [
    "XAUUSD", "XAGUSD", "USOUSD", "UKOUSD",
]

CRYPTO: list[str] = [
    "BTCUSD", "ETHUSD", "XRPUSD", "LTCUSD", "BCHUSD",
]

EXOTICS: list[str] = [
    "USDZAR", "USDTRY",
]

ALL_SYMBOLS: list[str] = (
    FOREX_MAJORS + FOREX_CROSSES + COMMODITIES + CRYPTO + EXOTICS
)

# ── Per-symbol pip value ────────────────────────────────────────────────

PIP_VALUES: dict[str, float] = {
    # Standard 5-digit forex
    **{s: 0.0001 for s in FOREX_MAJORS + FOREX_CROSSES},
    # JPY pairs override → 0.01
    **{s: 0.01 for s in ALL_SYMBOLS if s.endswith("JPY")},
    # Metals
    "XAUUSD": 0.01,
    "XAGUSD": 0.001,
    # Oil
    "USOUSD": 0.01,
    "UKOUSD": 0.01,
    # Crypto
    "BTCUSD": 0.01,
    "ETHUSD": 0.01,
    "XRPUSD": 0.0001,
    "LTCUSD": 0.01,
    "BCHUSD": 0.01,
    # Exotics
    "USDZAR": 0.0001,
    "USDTRY": 0.0001,
}

# ── Asset class lookup ──────────────────────────────────────────────────

SYMBOL_CLASS: dict[str, str] = {}
for _s in FOREX_MAJORS:
    SYMBOL_CLASS[_s] = "forex_major"
for _s in FOREX_CROSSES:
    SYMBOL_CLASS[_s] = "forex_cross"
for _s in COMMODITIES:
    SYMBOL_CLASS[_s] = "commodity"
for _s in CRYPTO:
    SYMBOL_CLASS[_s] = "crypto"
for _s in EXOTICS:
    SYMBOL_CLASS[_s] = "exotic"


# ── Contract sizes (units of base asset per 1 standard lot) ─────────────
# These reflect the most common MT5 broker conventions.
# Standard forex: 100,000 base currency units per lot.
# Crypto: 1 coin per lot (BTC, ETH, LTC, BCH) or 1000 coins (XRP).
# Metals: 100 oz gold, 5000 oz silver; Oil: 100 barrels.
CONTRACT_SIZES: dict[str, float] = {
    # Forex — 100,000 base units per standard lot
    **{s: 100_000.0 for s in FOREX_MAJORS + FOREX_CROSSES},
    # Commodities
    "XAUUSD": 100.0,    # 100 troy oz
    "XAGUSD": 5_000.0,  # 5,000 troy oz
    "USOUSD": 100.0,    # 100 barrels
    "UKOUSD": 100.0,    # 100 barrels
    # Crypto — 1 coin per lot (standard at most ECN brokers)
    "BTCUSD": 1.0,
    "ETHUSD": 1.0,
    "XRPUSD": 1_000.0,  # most brokers: 1 lot = 1,000 XRP
    "LTCUSD": 1.0,
    "BCHUSD": 1.0,
    # Exotics — 100,000 base units
    "USDZAR": 100_000.0,
    "USDTRY": 100_000.0,
}


def contract_size(symbol: str) -> float:
    """Return the number of base-currency units per 1 standard lot."""
    return CONTRACT_SIZES.get(symbol, 100_000.0)


def pip_value(symbol: str) -> float:
    """Return the pip size for *symbol*, defaulting to 0.0001."""
    return PIP_VALUES.get(symbol, 0.0001)


def asset_class(symbol: str) -> str:
    """Return the asset class tag for *symbol*."""
    return SYMBOL_CLASS.get(symbol, "unknown")


# ── Active symbols (what the bot actually trades) ───────────────────────
# Override via env:  ACTIVE_SYMBOLS=EURUSD,GBPUSD,XAUUSD
_env_active = os.getenv("ACTIVE_SYMBOLS", "")
SYMBOLS: list[str] = (
    [s.strip() for s in _env_active.split(",") if s.strip()]
    if _env_active
    else ALL_SYMBOLS  # default: trade all 30+ symbols
)
