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
    "NZDUSD", "USDCAD", "USDCHF",
]

FOREX_CROSSES: list[str] = [
    # EUR crosses
    "EURJPY", "EURGBP", "EURAUD", "EURCAD", "EURCHF", "EURNZD",
    # GBP crosses
    "GBPJPY", "GBPAUD", "GBPCAD", "GBPCHF", "GBPNZD",
    # AUD crosses
    "AUDJPY", "AUDCAD", "AUDCHF", "AUDNZD",
    # NZD crosses
    "NZDJPY", "NZDCAD", "NZDCHF",
    # Other crosses
    "CADJPY", "CHFJPY", "CADCHF",
]

COMMODITIES: list[str] = [
    # Metals
    "XAUUSD", "XAGUSD", "XPTUSD", "XPDUSD",
    # Oil
    "USOUSD", "UKOUSD",
    # Agricultural / Soft
    "NATGASUSD", "COPPERUSD",
]

INDICES: list[str] = [
    # US
    "US30",    # Dow Jones
    "US500",   # S&P 500
    "USTEC",   # Nasdaq 100
    # Europe
    "GER40",   # DAX
    "UK100",   # FTSE 100
    "FRA40",   # CAC 40
    "ESP35",   # IBEX 35
    "ITA40",   # FTSE MIB
    "EU50",    # Euro Stoxx 50
    # Asia-Pacific
    "JPN225",  # Nikkei 225
    "AUS200",  # ASX 200
    "HK50",    # Hang Seng
    "CHN50",   # CSI 300
]

CRYPTO: list[str] = [
    # Large-cap
    "BTCUSD", "ETHUSD", "BNBUSD", "SOLUSD", "XRPUSD",
    # Mid-cap
    "ADAUSD", "DOTUSD", "DOGEUSD", "LTCUSD", "LINKUSD",
    # Others
    "BCHUSD", "EOSUSD", "XLMUSD", "TRXUSD", "AVAXUSD",
]

EXOTICS: list[str] = [
    "USDZAR", "USDTRY", "USDMXN", "USDSEK", "USDNOK",
    "USDDKK", "USDSGD", "USDCNH", "USDHKD",
]

ALL_SYMBOLS: list[str] = (
    FOREX_MAJORS + FOREX_CROSSES + COMMODITIES + INDICES + CRYPTO + EXOTICS
)

# ── Per-symbol pip value ────────────────────────────────────────────────

_ALL_FOREX = FOREX_MAJORS + FOREX_CROSSES + EXOTICS

PIP_VALUES: dict[str, float] = {
    # Standard 5-digit forex and exotics
    **{s: 0.0001 for s in _ALL_FOREX},
    # JPY pairs override → 0.01
    **{s: 0.01 for s in ALL_SYMBOLS if s.endswith("JPY")},
    # SGD, HKD, NOK, SEK, DKK, CNH — larger pip
    "USDSGD": 0.0001,
    "USDHKD": 0.0001,
    "USDSEK": 0.0001,
    "USDNOK": 0.0001,
    "USDDKK": 0.0001,
    "USDCNH": 0.0001,
    # Metals
    "XAUUSD": 0.01,
    "XAGUSD": 0.001,
    "XPTUSD": 0.01,
    "XPDUSD": 0.01,
    # Energy / commodities
    "USOUSD":    0.01,
    "UKOUSD":    0.01,
    "NATGASUSD": 0.001,
    "COPPERUSD": 0.0001,
    # Indices — price-point based (1 point = 1 index unit)
    **{s: 1.0 for s in INDICES},
    # Crypto — confirmed from PU Prime MT5 trade_tick_size (2026-04-01)
    "BTCUSD":  0.01,
    "ETHUSD":  0.01,
    "BNBUSD":  0.01,
    "SOLUSD":  0.01,
    "XRPUSD":  0.0001,
    "ADAUSD":  0.0001,
    "DOTUSD":  0.001,    # MT5: 0.001  (was 0.01)
    "DOGEUSD": 0.00001,
    "LTCUSD":  0.01,
    "LINKUSD": 0.001,
    "BCHUSD":  0.01,
    "EOSUSD":  0.0001,   # MT5: 0.0001 (was 0.001)
    "XLMUSD":  0.0001,   # MT5: 0.0001 (was 0.00001)
    "TRXUSD":  0.00001,
    "AVAXUSD": 0.01,
}

# ── Asset class lookup ──────────────────────────────────────────────────

SYMBOL_CLASS: dict[str, str] = {}
for _s in FOREX_MAJORS:
    SYMBOL_CLASS[_s] = "forex_major"
for _s in FOREX_CROSSES:
    SYMBOL_CLASS[_s] = "forex_cross"
for _s in COMMODITIES:
    SYMBOL_CLASS[_s] = "commodity"
for _s in INDICES:
    SYMBOL_CLASS[_s] = "index"
for _s in CRYPTO:
    SYMBOL_CLASS[_s] = "crypto"
for _s in EXOTICS:
    SYMBOL_CLASS[_s] = "exotic"


# ── Contract sizes (units of base asset per 1 standard lot) ─────────────
# Forex: 100,000 base units.  Indices: 1 contract.  Crypto: 1 coin (XRP=1000).
CONTRACT_SIZES: dict[str, float] = {
    # Forex — 100,000 base units per standard lot
    **{s: 100_000.0 for s in _ALL_FOREX},
    # Commodities
    "XAUUSD":    100.0,      # 100 troy oz
    "XAGUSD":    5_000.0,    # 5,000 troy oz
    "XPTUSD":    100.0,      # 100 troy oz
    "XPDUSD":    100.0,      # 100 troy oz
    "USOUSD":    100.0,      # 100 barrels
    "UKOUSD":    100.0,      # 100 barrels
    "NATGASUSD": 10_000.0,   # 10,000 MMBtu
    "COPPERUSD": 25_000.0,   # 25,000 lbs
    # Indices — 1 contract = 1 index unit (price × contract = dollar value)
    **{s: 1.0 for s in INDICES},
    # Crypto — confirmed from PU Prime MT5 trade_contract_size (2026-04-01)
    "BTCUSD":  1.0,
    "ETHUSD":  1.0,
    "BNBUSD":  10.0,        # MT5: 10   (was 1)
    "SOLUSD":  10.0,        # MT5: 10   (was 1)
    "XRPUSD":  10_000.0,    # MT5: 10k  (was 1k)
    "ADAUSD":  10_000.0,    # MT5: 10k  (was 1k)
    "DOTUSD":  100.0,       # MT5: 100  (was 1)
    "DOGEUSD": 1_000.0,
    "LTCUSD":  100.0,       # MT5: 100  (was 1)
    "LINKUSD": 1.0,
    "BCHUSD":  10.0,        # MT5: 10   (was 1)
    "EOSUSD":  10_000.0,    # MT5: 10k  (was 1)
    "XLMUSD":  10_000.0,    # MT5: 10k  (was 1k)
    "TRXUSD":  100_000.0,   # MT5: 100k (was 1k)
    "AVAXUSD": 1.0,
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


def commission_per_lot(symbol: str) -> float:
    """Return the round-trip commission per standard lot for *symbol*.

    Rates are configured per asset class in settings so they can be tuned
    once the broker's actual fee schedule is confirmed.
    """
    from config import settings  # lazy import to avoid circular dependency
    ac = asset_class(symbol)
    if ac == "crypto":
        return settings.COMMISSION_PER_LOT_CRYPTO
    elif ac in ("commodity", "index"):
        return settings.COMMISSION_PER_LOT_COMMODITY
    elif ac == "exotic":
        return settings.COMMISSION_PER_LOT_EXOTIC
    return settings.COMMISSION_PER_LOT  # forex_major, forex_cross


# ── Active symbols (what the bot actually trades) ───────────────────────
# Override via env:  ACTIVE_SYMBOLS=EURUSD,GBPUSD,XAUUSD
_env_active = os.getenv(
    "ACTIVE_SYMBOLS",
    (
        "EURUSD,USDJPY,GBPUSD,AUDUSD,USDCAD,USDCHF,"
        "BTCUSD,ETHUSD,BNBUSD,SOLUSD,XRPUSD,ADAUSD,DOTUSD,LTCUSD,"
        "EOSUSD,XLMUSD,TRXUSD,USDSGD,USDCNH,USDHKD,"
        "USOUSD,UKOUSD,XAUUSD"
    ),
)
SYMBOLS: list[str] = (
    [s.strip() for s in _env_active.split(",") if s.strip()]
    if _env_active
    else ALL_SYMBOLS  # default: scan everything
)

# Alias — some scripts import the old name
ACTIVE_SYMBOLS = SYMBOLS
