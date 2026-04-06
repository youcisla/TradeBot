"""Fetch live symbol specifications from PU Prime MT5 and compare against
config/symbols.py hardcoded values.

Usage:
    python tools/fetch_mt5_specs.py

Output:
  - Full spec table for every available symbol
  - MISMATCH warnings for contract_size and point (pip size) vs config
  - Suggested Python dict snippets to paste into config/symbols.py
  - Suggested .env overrides for lot limits (MIN_LOT_SIZE, MAX_LOT_SIZE)

Requirements:
  - MetaTrader5 package installed  (pip install MetaTrader5)
  - MT5 terminal running and logged in to PUPrime-Demo
  - .env in project root with BROKER_ACCOUNT / BROKER_PASSWORD / BROKER_SERVER
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# ── Add project root to sys.path so config imports work ─────────────────────
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")

import MetaTrader5 as mt5

from config.symbols import ALL_SYMBOLS, PIP_VALUES, CONTRACT_SIZES, SYMBOLS
from config import settings


# ── Helpers ──────────────────────────────────────────────────────────────────

def _col(text: str, width: int) -> str:
    return str(text)[:width].ljust(width)


def _fmt(val: float) -> str:
    if val >= 1_000:
        return f"{val:,.0f}"
    if val >= 1:
        return f"{val:.4f}"
    return f"{val:.8f}".rstrip("0").rstrip(".")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 90)
    print("  PulseTrade — MT5 Symbol Spec Fetcher (PU Prime)")
    print("=" * 90)

    # ── Connect ──────────────────────────────────────────────────────────
    if not mt5.initialize():
        print(f"[ERROR] MT5 initialize failed: {mt5.last_error()}")
        sys.exit(1)

    account = int(os.getenv("BROKER_ACCOUNT", "0"))
    password = os.getenv("BROKER_PASSWORD", "")
    server = os.getenv("BROKER_SERVER", "")

    if not mt5.login(account, password=password, server=server):
        print(f"[ERROR] MT5 login failed: {mt5.last_error()}")
        mt5.shutdown()
        sys.exit(1)

    info = mt5.account_info()
    print(f"\n  Connected: account={info.login}  server={info.server}"
          f"  balance={info.balance:.2f}  leverage={info.leverage}\n")

    # ── Collect specs ─────────────────────────────────────────────────────
    header = (
        f"{'Symbol':<14} {'Digits':>6} {'Point':>12} {'Config_pip':>12} "
        f"{'ContractSz':>12} {'Cfg_CS':>12} "
        f"{'LotMin':>8} {'LotMax':>10} {'LotStep':>8} "
        f"{'TickSz':>10} {'TickVal':>10} {'Spread':>8}"
    )
    print(header)
    print("-" * len(header))

    mismatches_pip: dict[str, tuple[float, float]] = {}    # symbol → (mt5, config)
    mismatches_cs:  dict[str, tuple[float, float]] = {}    # symbol → (mt5, config)
    lot_min_global = 9999.0
    lot_max_global = 0.0
    not_found: list[str] = []

    for sym in ALL_SYMBOLS:
        # Try to select the symbol first
        mt5.symbol_select(sym, True)
        si = mt5.symbol_info(sym)
        if si is None:
            not_found.append(sym)
            continue

        mt5_point = float(si.point)
        mt5_cs    = float(si.trade_contract_size)
        lot_min   = float(si.volume_min)
        lot_max   = float(si.volume_max)
        lot_step  = float(si.volume_step)
        tick_sz   = float(si.trade_tick_size)
        tick_val  = float(si.trade_tick_value)
        spread    = float(si.spread) * mt5_point  # spread in price units

        cfg_pip = PIP_VALUES.get(sym, 0.0001)
        cfg_cs  = CONTRACT_SIZES.get(sym, 100_000.0)

        pip_ok = abs(mt5_point - cfg_pip) < cfg_pip * 0.05  # within 5%
        cs_ok  = abs(mt5_cs - cfg_cs) < cfg_cs * 0.05

        pip_flag = "" if pip_ok else " ← PIP MISMATCH"
        cs_flag  = "" if cs_ok  else " ← CS MISMATCH"

        if not pip_ok:
            mismatches_pip[sym] = (mt5_point, cfg_pip)
        if not cs_ok:
            mismatches_cs[sym] = (mt5_cs, cfg_cs)

        lot_min_global = min(lot_min_global, lot_min)
        lot_max_global = max(lot_max_global, lot_max)

        row = (
            f"{sym:<14} {si.digits:>6} {_fmt(mt5_point):>12} {_fmt(cfg_pip):>12}"
            f" {_fmt(mt5_cs):>12} {_fmt(cfg_cs):>12}"
            f" {_fmt(lot_min):>8} {_fmt(lot_max):>10} {_fmt(lot_step):>8}"
            f" {_fmt(tick_sz):>10} {_fmt(tick_val):>10} {_fmt(spread):>8}"
            f"{pip_flag}{cs_flag}"
        )
        print(row)

    mt5.shutdown()

    # ── Summary ──────────────────────────────────────────────────────────
    print()
    if not_found:
        print(f"[NOT FOUND ON BROKER] {len(not_found)} symbols skipped:")
        print("  " + ", ".join(not_found))
        print()

    # ── PIP VALUE mismatches → suggest PIP_VALUES patch ──────────────────
    if mismatches_pip:
        print("=" * 70)
        print("  PIP VALUE MISMATCHES — paste into config/symbols.py → PIP_VALUES")
        print("=" * 70)
        for sym, (mt5_val, cfg_val) in sorted(mismatches_pip.items()):
            print(f'    "{sym}": {mt5_val},  # MT5={mt5_val}  was={cfg_val}')
        print()
    else:
        print("  ✓ All pip values match MT5 — config/symbols.py PIP_VALUES is correct.\n")

    # ── CONTRACT SIZE mismatches → suggest CONTRACT_SIZES patch ──────────
    if mismatches_cs:
        print("=" * 70)
        print("  CONTRACT SIZE MISMATCHES — paste into config/symbols.py → CONTRACT_SIZES")
        print("=" * 70)
        for sym, (mt5_val, cfg_val) in sorted(mismatches_cs.items()):
            print(f'    "{sym}": {mt5_val:.1f},  # MT5={mt5_val}  was={cfg_val}')
        print()
    else:
        print("  ✓ All contract sizes match MT5 — config/symbols.py CONTRACT_SIZES is correct.\n")

    # ── Lot size limits summary ───────────────────────────────────────────
    print("=" * 70)
    print("  LOT SIZE LIMITS (from broker)")
    print("=" * 70)
    print(f"  Smallest MIN lot across all symbols : {lot_min_global}")
    print(f"  Largest  MAX lot across all symbols : {lot_max_global}")
    cfg_min = settings.MIN_LOT_SIZE
    cfg_max = settings.MAX_LOT_SIZE
    if cfg_min != lot_min_global:
        print(f"\n  [SUGGEST] .env: MIN_LOT_SIZE={lot_min_global}  (currently {cfg_min})")
    else:
        print(f"  ✓ MIN_LOT_SIZE={cfg_min} matches broker minimum.")
    if cfg_max > lot_max_global:
        print(f"  [SUGGEST] .env: MAX_LOT_SIZE={lot_max_global}  (currently {cfg_max} exceeds broker max)")
    else:
        print(f"  ✓ MAX_LOT_SIZE={cfg_max} is within broker limits.")

    print()
    print("Done.")


if __name__ == "__main__":
    main()
