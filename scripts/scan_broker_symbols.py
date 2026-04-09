#!/usr/bin/env python3
"""Scan all tradeable symbols from MT5 (bid > 0) and auto-generate
config/symbols.py with correct pip values and contract sizes.

Usage:
    python scripts/scan_broker_symbols.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERROR: MetaTrader5 package not installed.")
    print("  pip install MetaTrader5")
    sys.exit(1)


SKIP_CONTAINS = {".crp", ".ft", ".24H", " ROBOT"}


def load_existing_priority_symbols() -> list[str]:
    """Load PRIORITY_SYMBOLS from an existing config/symbols.py so they survive re-generation."""
    existing_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "symbols.py")
    if not os.path.exists(existing_path):
        return []
    try:
        import re
        text = open(existing_path, encoding="utf-8").read()
        match = re.search(r"PRIORITY_SYMBOLS\s*:\s*list\[str\]\s*=\s*\[(.*?)\]", text, re.DOTALL)
        if not match:
            return []
        inner = match.group(1)
        # Remove comment lines (# ...) and blank lines, then extract symbol names
        clean = re.sub(r'#[^\n]*\n', '\n', inner)  # remove line comments
        clean = re.sub(r'\n[^"]*', '', clean)      # remove non-symbol line prefixes
        symbols = [s.strip().strip('"').strip("'") for s in clean.split(",") if s.strip()]
        return [s for s in symbols if s and s not in ('"', "'")]
    except Exception:
        return []


def fmt_list_py(items: list[str]) -> str:
    if not items:
        return "    []"
    items = sorted(set(items))
    lines = []
    for i in range(0, len(items), 5):
        chunk = items[i : i + 5]
        end = "," if i + 5 < len(items) else ""
        lines.append('    "' + '", "'.join(chunk) + '"' + end)
    return "\n".join(lines)


def main():
    if not mt5.initialize():
        print(f"MT5 init failed: {mt5.last_error()}")
        sys.exit(1)

    print("MT5 connected — scanning all symbols...\n")
    all_symbols = mt5.symbols_get()
    print(f"Total symbols from broker: {len(all_symbols)}")

    # ── Collect tradeable symbols with full info ─────────────────────────
    tradeable = []
    for s in all_symbols:
        info = mt5.symbol_info(s.name)
        if info is None:
            continue
        bid = info.bid
        if bid <= 0:
            continue
        if any(skip in s.name for skip in SKIP_CONTAINS):
            continue
        tradeable.append({
            "name": s.name,
            "path": s.path,
            "bid": bid,
            "digits": info.digits,
            "point": info.point,
            "tick_value": info.trade_tick_value,
            "contract_size": info.trade_contract_size,
        })

    print(f"Tradeable (bid > 0): {len(tradeable)}")

    # Build name -> path lookup
    name_to_path = {t["name"]: t["path"] for t in tradeable}
    names = [t["name"] for t in tradeable]

    # ── Categorise by path ────────────────────────────────────────────────
    def by_path(path_prefix):
        return sorted(n for n in names if name_to_path.get(n, "").startswith(path_prefix))

    def by_contains(substr_tuple):
        return sorted(n for n in names if any(x in n for x in substr_tuple))

    def remaining(exclude_sets):
        excluded = set()
        for s in exclude_sets:
            excluded.update(s)
        return sorted(n for n in names if n not in excluded)

    forex_majors_list = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD", "USDCAD", "USDCHF"]
    forex_majors = sorted(n for n in forex_majors_list if n in name_to_path)

    # Forex .s — path Forex .s
    forex_s = by_path("Forex .s")

    # All other Forex — path Forex (but not the majors, not .s)
    forex_all = by_path("Forex")
    forex_crosses = sorted(n for n in forex_all
                           if n not in forex_majors
                           and not n.endswith(".s")
                           and not n.endswith(".crp"))

    # Commodities — Commodities.s path + Gold .s + Oil .s + Silver .s
    commodities = sorted(by_path("Commodities.s") + by_path("Gold .s") + by_path("Oil .s") + by_path("Silver .s"))

    # Index CFDs — Indices.s + Indices-JP.s
    indices = sorted(by_path("Indices.s") + by_path("Indices-JP.s"))

    # ETFs
    etfs = sorted(by_path("ETFs\\ETF-C") + by_path("ETFs\\ETF-R") + by_path("ETFs\\ETFs-Crypto"))

    # Crypto
    crypto = sorted(by_path("Cryptos"))

    # Bonds
    bonds = sorted(by_path("Bonds"))

    # Stock CFDs — Equity paths + remaining .s
    stock_cfds = sorted(by_path("Equity-US") + by_path("Equity-EU") + by_path("Equity-UK"))

    # Remaining .s that aren't in other categories
    already_cat = set(forex_majors + forex_crosses + forex_s + commodities + indices + etfs + crypto + bonds + stock_cfds)
    other_s = sorted(n for n in names if n.endswith(".s") and n not in already_cat)
    stock_cfds = sorted(stock_cfds + other_s)

    # Print summary
    print(f"\n=== CATEGORISED ({len(names)} total) ===")
    print(f"  FOREX_MAJORS : {len(forex_majors)}")
    print(f"  FOREX_CROSSES: {len(forex_crosses)}")
    print(f"  FOREX_S      : {len(forex_s)}")
    print(f"  COMMODITIES  : {len(commodities)}")
    print(f"  INDICES      : {len(indices)}")
    print(f"  ETFs         : {len(etfs)}")
    print(f"  CRYPTO       : {len(crypto)}")
    print(f"  STOCK_CFDS   : {len(stock_cfds)}")
    print(f"  BONDS        : {len(bonds)}")

    total_cat = (len(forex_majors) + len(forex_crosses) + len(forex_s) +
                 len(commodities) + len(indices) + len(etfs) + len(crypto) +
                 len(stock_cfds) + len(bonds))
    print(f"  TOTAL        : {total_cat}")
    if total_cat != len(names):
        print(f"  MISSING      : {len(names) - total_cat}")

    # ── Build PIP_VALUES and CONTRACT_SIZES ───────────────────────────
    name_to_info = {t["name"]: t for t in tradeable}

    pip_values = {}
    contract_sizes = {}
    symbol_class = {}

    def classify(name):
        if name in forex_majors:
            return "forex_major"
        elif name in forex_crosses or name in forex_s:
            return "forex_cross"
        elif name in commodities:
            return "commodity"
        elif name in indices:
            return "index"
        elif name in etfs:
            return "etf"
        elif name in crypto:
            return "crypto"
        elif name in bonds:
            return "bond"
        return "stock_cfd"

    for t in tradeable:
        name = t["name"]
        digits = t["digits"]
        point = t["point"]

        # Pip = point * 10, rounded to reasonable precision
        pip = round(point * 10, 8)
        if name.endswith("JPY"):
            pip = round(point * 10, 4)

        contract_sizes[name] = t["contract_size"]
        pip_values[name] = pip
        symbol_class[name] = classify(name)

    # ── Write symbols.py ─────────────────────────────────────────────────
    existing_priority = load_existing_priority_symbols()
    lines = [
        '"""Tradeable symbols — auto-generated from MT5 broker scan.',
        '    Do NOT edit manually. Run: python scripts/scan_broker_symbols.py',
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "",
        "# ── All known symbols by asset class ───────────────────────────",
        "",
        f"FOREX_MAJORS: list[str] = [",
        fmt_list_py(forex_majors),
        "]",
        "",
        f"FOREX_CROSSES: list[str] = [",
        fmt_list_py(forex_crosses),
        "]",
        "",
        f"FOREX_S_SUFFIX: list[str] = [   # .s forex variants",
        fmt_list_py(forex_s),
        "]",
        "",
        f"COMMODITIES: list[str] = [",
        fmt_list_py(commodities),
        "]",
        "",
        f"INDICES: list[str] = [   # Index CFDs (.s)",
        fmt_list_py(indices),
        "]",
        "",
        f"ETFS: list[str] = [",
        fmt_list_py(etfs),
        "]",
        "",
        f"CRYPTO: list[str] = [",
        fmt_list_py(crypto),
        "]",
        "",
        f"STOCK_CFDS: list[str] = [   # Individual stock CFDs",
        fmt_list_py(stock_cfds),
        "]",
        "",
        f"BONDS: list[str] = [",
        fmt_list_py(bonds),
        "]",
        "",
        "ALL_SYMBOLS: list[str] = (",
        "    FOREX_MAJORS + FOREX_CROSSES + FOREX_S_SUFFIX",
        "    + COMMODITIES + INDICES + ETFS + CRYPTO",
        "    + STOCK_CFDS + BONDS",
        ")",
        "",
        "",
        "# ── Per-symbol pip value (from broker tick data) ────────────────",
        "PIP_VALUES: dict[str, float] = {",
    ]

    for name in sorted(pip_values):
        lines.append(f"    \"{name}\": {pip_values[name]},  # digits={name_to_info[name]['digits']}")

    lines.append("}")
    lines.append("")
    lines.append("# ── Contract sizes (from broker) ─────────────────────────")
    lines.append("CONTRACT_SIZES: dict[str, float] = {")
    for name in sorted(contract_sizes):
        lines.append(f'    "{name}": {contract_sizes[name]},')
    lines.append("}")
    lines.append("")
    lines.append("# ── Asset class lookup ───────────────────────────────────")
    lines.append("SYMBOL_CLASS: dict[str, str] = {")
    for name in sorted(symbol_class):
        lines.append(f'    "{name}": "{symbol_class[name]}",')
    lines.append("}")
    lines.append("")
    lines.extend([
        "",
        "# ── Helpers ───────────────────────────────────────────────────",
        "",
        "_ALL_FOREX = FOREX_MAJORS + FOREX_CROSSES + FOREX_S_SUFFIX",
        "",
        "def pip_value(symbol: str) -> float:",
        '    """Return pip size for symbol."""',
        "    return PIP_VALUES.get(symbol, 0.0001)",
        "",
        "def contract_size(symbol: str) -> float:",
        '    """Return contract size (units per lot) from broker data."""',
        "    return CONTRACT_SIZES.get(symbol, 100_000.0)",
        "",
        "def asset_class(symbol: str) -> str:",
        '    """Return asset class tag for symbol."""',
        "    return SYMBOL_CLASS.get(symbol, \"unknown\")",
        "",
        "# ── Priority subset (fast scan ~60 symbols) ────────────────────",
        "# Curated high-liquidity instruments — preserved across re-generations.",
        "# Activate full universe: ACTIVE_SYMBOLS=ALL or USE_FULL_UNIVERSE=1",
        f"PRIORITY_SYMBOLS: list[str] = [",
        (fmt_list_py(existing_priority) if existing_priority else "    # (copy from previous symbols.py or leave empty to use full universe on restart)"),
        "]",
        "",
        "# ── Active symbols ─────────────────────────────────────────────",
        'import os',
        '_env_active = os.getenv("ACTIVE_SYMBOLS", None)',
        '_use_full = os.getenv("USE_FULL_UNIVERSE", "0") == "1"',
        "SYMBOLS: list[str] = (",
        "    [s.strip() for s in _env_active.split(\",\") if s.strip()]",
        "    if _env_active",
        "    else ALL_SYMBOLS",
        "    if _use_full",
        "    else PRIORITY_SYMBOLS",
        ")",
        "ACTIVE_SYMBOLS = SYMBOLS",
    ])

    out_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "symbols.py")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nWritten: {out_path}")
    print(f"Total tradable symbols: {len(tradeable)}")
    print("\nRun: python main.py  # restart bot")

    mt5.shutdown()


if __name__ == "__main__":
    main()
