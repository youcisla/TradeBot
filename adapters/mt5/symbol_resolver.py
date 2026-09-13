"""MetaTrader 5 symbol resolution and metadata.

Handles canonical → broker symbol mapping, contract size, tick size,
tick value, and broker symbol availability detection.
"""

from __future__ import annotations

import logging
from typing import Any, cast

import MetaTrader5 as _mt5

mt5 = cast(Any, _mt5)

logger = logging.getLogger(__name__)

# ── Symbol resolution ───────────────────────────────────────────────────

# Common suffixes / variants brokers use for symbol name resolution
# Broker symbol suffixes, most specific first.  PU Prime (the live broker here)
# uses ".p" for forex/CFDs and ".crp" for crypto-index variants — verified
# against the account: EURUSD.p, XAUUSD.p, XAUUSD.crp.  Without these the
# resolver silently failed to map gold and every suffixed symbol.
_SUFFIXES = [
    ".crp", ".p", "", ".r", ".ecn", "m", "+", ".a", ".b", ".i",
    ".pro", ".raw", ".std", ".", "#", "-ECN",
]

# Some brokers use completely different names for commodities
_ALIASES: dict[str, list[str]] = {
    "XAUUSD": ["XAUUSD.s", "Gold", "GOLD", "GoldUSD", "XAUUSD.r", "XAUUSD+"],
    "XAGUSD": ["XAGUSD.s", "Silver", "SILVER", "SilverUSD", "XAGUSD.r"],
    "USOUSD": ["USOUSD.s", "USOIL", "WTI", "CrudeOIL", "USOil", "USOUSD.r", "WTI.r", "USOIL.r"],
    "UKOUSD": ["UKOUSD.s", "UKOIL", "Brent", "BrentOil", "UKOUSD.r", "UKOIL.r"],
}


def resolve_broker_symbol(connector, symbol: str) -> str:
    """Translate canonical symbol to broker symbol name using cached maps."""
    return getattr(connector, 'symbol_map', {}).get(symbol, symbol)


def get_available_symbols(connector, candidates: list[str]) -> list[str]:
    """Return the subset of *candidates* that are visible in the MT5 terminal.

    Populates ``connector.symbol_map`` (canonical → broker name) and
    ``connector._reverse_map`` (broker name → canonical).
    """
    available = []
    connector.symbol_map = {}
    connector._reverse_map = {}

    for sym in candidates:
        broker_sym = _find_broker_symbol(sym)
        if broker_sym:
            available.append(sym)
            connector.symbol_map[sym] = broker_sym
            connector._reverse_map[broker_sym] = sym

    return available


def _find_broker_symbol(sym: str) -> str | None:
    """Try to find *sym* on the broker under any known variant."""
    # 1. Exact match
    info = mt5.symbol_info(sym)
    if info is not None:
        mt5.symbol_select(sym, True)
        return sym

    # 2. Enable then retry
    mt5.symbol_select(sym, True)
    info = mt5.symbol_info(sym)
    if info is not None:
        return sym

    # 3. Try suffixes
    for sfx in _SUFFIXES:
        if not sfx:
            continue
        candidate = sym + sfx
        mt5.symbol_select(candidate, True)
        info = mt5.symbol_info(candidate)
        if info is not None:
            logger.info("Symbol mapped: %s → %s", sym, candidate)
            return candidate

    # 4. Try aliases
    for alias in _ALIASES.get(sym, []):
        mt5.symbol_select(alias, True)
        info = mt5.symbol_info(alias)
        if info is not None:
            logger.info("Symbol mapped: %s → %s (alias)", sym, alias)
            return alias

    return None


def get_contract_size(symbol: str) -> float:
    """Fetch the actual contract size from MT5 symbol info."""
    from config.symbols import contract_size as _cfg_cs

    info = mt5.symbol_info(symbol)
    if info is not None:
        cs = float(info.trade_contract_size)
        cfg_cs = _cfg_cs(symbol)
        if abs(cs - cfg_cs) > 0.01:
            logger.warning(
                "CONTRACT SIZE MISMATCH for %s: broker=%.2f config=%.2f — using broker value",
                symbol, cs, cfg_cs,
            )
        return cs
    return _cfg_cs(symbol)


def get_tick_size(symbol: str) -> float:
    """Return the broker's actual minimum price movement (trade_tick_size)."""
    from config.symbols import pip_value as _pv

    info = mt5.symbol_info(symbol)
    if info is not None:
        return float(info.trade_tick_size)
    return _pv(symbol)


def get_tick_value(symbol: str) -> float:
    """Return trade_tick_value from MT5 — P&L in account currency per tick per lot."""
    from config.symbols import pip_value as _pv, contract_size as _cs

    info = mt5.symbol_info(symbol)
    if info is not None:
        return float(info.trade_tick_value)
    return _pv(symbol) * _cs(symbol)
