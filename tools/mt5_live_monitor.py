"""MT5 Live Symbol Monitor — real-time price, spread, and config diff.

Connects directly to MT5 and streams live data for every active symbol so you
can see exactly what the broker is reporting vs what the bot's config assumes.

Identifies:
  • Spread in absolute terms AND in pips (both raw and bot-computed)
  • Spread vs bot's per-class max-spread thresholds (would the bot reject this?)
  • Tick size & tick value from MT5 vs config/symbols.py
  • Contract size mismatches
  • Live bid/ask/mid and last-trade price
  • Open positions with live broker P&L vs last known DB values

Usage:
    # Single snapshot of all symbols:
    python tools/mt5_live_monitor.py

    # Continuous refresh every 3 s:
    python tools/mt5_live_monitor.py --watch

    # Specific symbols only:
    python tools/mt5_live_monitor.py --symbols BTCUSD,EURUSD,XAUUSD

    # Only show rows where spread exceeds bot threshold (noise filter):
    python tools/mt5_live_monitor.py --watch --warn-only

    # Refresh interval (default 3 s):
    python tools/mt5_live_monitor.py --watch --interval 5

Requirements:
    pip install MetaTrader5 python-dotenv
    MT5 terminal must be running and logged in.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from typing import NamedTuple

# ── Bootstrap project root ────────────────────────────────────────────────────
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")

import MetaTrader5 as mt5

from config.symbols import (
    ALL_SYMBOLS,
    PIP_VALUES,
    CONTRACT_SIZES,
    pip_value,
    contract_size,
    asset_class,
)
from config import settings

# ── ANSI colour helpers ───────────────────────────────────────────────────────
_RED    = "\033[91m"
_YELLOW = "\033[93m"
_GREEN  = "\033[92m"
_CYAN   = "\033[96m"
_BOLD   = "\033[1m"
_DIM    = "\033[2m"
_RESET  = "\033[0m"

if sys.platform == "win32":
    os.system("")   # enable VT100 on Windows


def _red(s: str) -> str:    return f"{_RED}{s}{_RESET}"
def _yellow(s: str) -> str: return f"{_YELLOW}{s}{_RESET}"
def _green(s: str) -> str:  return f"{_GREEN}{s}{_RESET}"
def _cyan(s: str) -> str:   return f"{_CYAN}{s}{_RESET}"
def _bold(s: str) -> str:   return f"{_BOLD}{s}{_RESET}"
def _dim(s: str) -> str:    return f"{_DIM}{s}{_RESET}"


# ── Per-class max-spread thresholds (mirrors risk_agent logic) ────────────────

def _max_spread_pips(symbol: str) -> float:
    """Return the bot's spread rejection threshold for this symbol (in pips)."""
    ac = asset_class(symbol)
    if ac == "crypto":
        return float("inf")   # bot uses % threshold for crypto, not pips
    if ac == "commodity":
        return settings.MAX_SPREAD_PIPS_COMMODITY
    if ac == "exotic":
        return settings.MAX_SPREAD_PIPS_EXOTIC
    return settings.MAX_SPREAD_PIPS   # forex majors / crosses / indices


def _max_spread_pct(symbol: str) -> float | None:
    """Return the % spread threshold for crypto, None for everything else."""
    if asset_class(symbol) == "crypto":
        return settings.MAX_SPREAD_PCT_CRYPTO
    return None


# ── Data container ────────────────────────────────────────────────────────────

class SymbolSnapshot(NamedTuple):
    canonical: str          # name in our config  (e.g. BTCUSD)
    broker_sym: str         # actual MT5 name     (e.g. BTCUSD)
    bid: float
    ask: float
    last: float             # last traded price
    spread_abs: float       # ask − bid (absolute)
    spread_pips_mt5: float  # spread_abs / tick_size   (MT5 point-based)
    spread_pips_cfg: float  # spread_abs / cfg pip     (config-based)
    spread_pct: float       # spread_abs / mid × 100
    tick_size_mt5: float    # trade_tick_size from MT5
    tick_size_cfg: float    # pip_value from config
    tick_value_mt5: float   # trade_tick_value from MT5 (account currency)
    contract_size_mt5: float
    contract_size_cfg: float
    digits: int
    stops_level: int
    volume_min: float
    volume_max: float
    volume_step: float
    bot_rejects_spread: bool   # True if bot would reject due to spread
    has_spec_mismatch: bool    # True if tick_size or contract_size differ


# ── MT5 helpers ───────────────────────────────────────────────────────────────

_SUFFIXES = ["", ".r", ".ecn", "m", "+", ".a", ".b", ".i", ".pro", ".raw", ".std"]
_ALIASES: dict[str, list[str]] = {
    "XAUUSD": ["Gold", "GOLD", "XAUUSD.r"],
    "XAGUSD": ["Silver", "SILVER", "XAGUSD.r"],
    "USOUSD": ["USOIL", "WTI", "CrudeOIL", "USOUSD.r"],
    "UKOUSD": ["UKOIL", "Brent", "BrentOil", "UKOUSD.r"],
}


def _resolve(canonical: str) -> str | None:
    """Return the broker-side symbol name or None if not available."""
    # Try exact
    info = mt5.symbol_info(canonical)
    if info is not None:
        mt5.symbol_select(canonical, True)
        return canonical
    mt5.symbol_select(canonical, True)
    info = mt5.symbol_info(canonical)
    if info is not None:
        return canonical
    # Try suffixes
    for sfx in _SUFFIXES:
        if not sfx:
            continue
        candidate = canonical + sfx
        mt5.symbol_select(candidate, True)
        if mt5.symbol_info(candidate) is not None:
            return candidate
    # Try aliases
    for alias in _ALIASES.get(canonical, []):
        mt5.symbol_select(alias, True)
        if mt5.symbol_info(alias) is not None:
            return alias
    return None


def _fetch_snapshot(canonical: str) -> SymbolSnapshot | None:
    """Fetch a single symbol's full live snapshot from MT5."""
    broker_sym = _resolve(canonical)
    if broker_sym is None:
        return None

    tick = mt5.symbol_info_tick(broker_sym)
    info = mt5.symbol_info(broker_sym)
    if tick is None or info is None:
        return None

    bid = float(tick.bid)
    ask = float(tick.ask)
    spread_abs = ask - bid
    mid = (bid + ask) / 2 if (bid + ask) != 0 else 1.0
    last = float(tick.last) if tick.last else mid

    tick_size_mt5 = float(info.trade_tick_size) if info.trade_tick_size else 0.00001
    tick_size_cfg = pip_value(canonical)
    tick_value_mt5 = float(info.trade_tick_value)
    contract_size_mt5 = float(info.trade_contract_size)
    contract_size_cfg = contract_size(canonical)

    spread_pips_mt5 = spread_abs / tick_size_mt5 if tick_size_mt5 else 0.0
    spread_pips_cfg = spread_abs / tick_size_cfg if tick_size_cfg else 0.0
    spread_pct = (spread_abs / mid) * 100 if mid else 0.0

    # Would the bot reject this trade due to spread?
    max_pct = _max_spread_pct(canonical)
    if max_pct is not None:
        bot_rejects = spread_pct > max_pct
    else:
        bot_rejects = spread_pips_cfg > _max_spread_pips(canonical)

    # Tick-size mismatch: config stores pip size (e.g. 0.0001 for EURUSD),
    # MT5 reports trade_tick_size which is 1 point = 0.1 pip for 5-digit brokers
    # (0.00001).  A 10× ratio between cfg and MT5 is EXPECTED and not a mismatch.
    # A real mismatch is any ratio other than 1:1 or 10:1.
    ratio = tick_size_cfg / tick_size_mt5 if tick_size_mt5 else 1.0
    tick_mismatch = abs(ratio - 1.0) > 0.01 and abs(ratio - 10.0) > 0.01
    contract_mismatch = (
        abs(contract_size_mt5 - contract_size_cfg) > contract_size_cfg * 0.01
    )
    has_spec_mismatch = tick_mismatch or contract_mismatch

    return SymbolSnapshot(
        canonical=canonical,
        broker_sym=broker_sym,
        bid=bid,
        ask=ask,
        last=last,
        spread_abs=spread_abs,
        spread_pips_mt5=spread_pips_mt5,
        spread_pips_cfg=spread_pips_cfg,
        spread_pct=spread_pct,
        tick_size_mt5=tick_size_mt5,
        tick_size_cfg=tick_size_cfg,
        tick_value_mt5=tick_value_mt5,
        contract_size_mt5=contract_size_mt5,
        contract_size_cfg=contract_size_cfg,
        digits=int(info.digits),
        stops_level=int(info.trade_stops_level),
        volume_min=float(info.volume_min),
        volume_max=float(info.volume_max),
        volume_step=float(info.volume_step),
        bot_rejects_spread=bot_rejects,
        has_spec_mismatch=has_spec_mismatch,
    )


# ── Open position live snapshot ───────────────────────────────────────────────

def _fetch_open_positions() -> list[dict]:
    """Return all currently open positions from MT5 with live P&L."""
    positions = mt5.positions_get()
    if positions is None:
        return []
    result = []
    for p in positions:
        result.append({
            "ticket":     p.ticket,
            "symbol":     p.symbol,
            "direction":  "BUY" if p.type == 0 else "SELL",
            "lots":       p.volume,
            "entry":      p.price_open,
            "sl":         p.sl,
            "tp":         p.tp,
            "current":    p.price_current,
            "pnl":        p.profit,
            "swap":       p.swap,
            "comment":    p.comment,
        })
    return result


# ── Rendering ─────────────────────────────────────────────────────────────────

_HDR = (
    f"{'Symbol':<12} {'Broker':<14} {'Bid':>12} {'Ask':>12} "
    f"{'Spread(abs)':>12} {'Spr(pts/MT5)':>14} {'Spr(pip/cfg)':>14} "
    f"{'Spr%':>7} {'Tick(MT5)':>10} {'Pip(cfg)':>10} "
    f"{'TickVal':>10} {'ContSz(MT5)':>13} {'ContSz(cfg)':>13} "
    f"{'Dgt':>4} {'Stops':>6} {'MinLot':>7} {'MaxLot':>8} {'BotOK':>6}"
)
_SEP = "─" * len(_HDR)


def _fmt_row(s: SymbolSnapshot, warn_only: bool) -> str | None:
    if warn_only and not s.bot_rejects_spread and not s.has_spec_mismatch:
        return None

    bot_ok = _red("REJECT") if s.bot_rejects_spread else _green("  OK  ")
    sym_col = _yellow(f"{s.canonical:<12}") if s.has_spec_mismatch else f"{s.canonical:<12}"

    # Spread pip columns: highlight when config-computed differs from MT5-computed
    pip_diff = abs(s.spread_pips_mt5 - s.spread_pips_cfg) > 0.5
    pips_mt5_str = f"{s.spread_pips_mt5:>14.2f}"
    pips_cfg_str = f"{s.spread_pips_cfg:>14.2f}"
    if pip_diff:
        pips_mt5_str = _cyan(pips_mt5_str)
        pips_cfg_str = _yellow(pips_cfg_str)

    # Spec mismatches
    ts_mt5_str = f"{s.tick_size_mt5:>12g}"
    ts_cfg_str = f"{s.tick_size_cfg:>12g}"
    cs_mt5_str = f"{s.contract_size_mt5:>13,.0f}"
    cs_cfg_str = f"{s.contract_size_cfg:>13,.0f}"
    if abs(s.tick_size_mt5 - s.tick_size_cfg) > s.tick_size_cfg * 0.01:
        ts_mt5_str = _red(ts_mt5_str)
        ts_cfg_str = _red(ts_cfg_str)
    if abs(s.contract_size_mt5 - s.contract_size_cfg) > s.contract_size_cfg * 0.01:
        cs_mt5_str = _red(cs_mt5_str)
        cs_cfg_str = _red(cs_cfg_str)

    return (
        f"{sym_col} {s.broker_sym:<14} "
        f"{s.bid:>12.{s.digits}f} {s.ask:>12.{s.digits}f} "
        f"{s.spread_abs:>12.{s.digits}f} "
        f"{pips_mt5_str} {pips_cfg_str} "
        f"{s.spread_pct:>7.3f}% "
        f"{ts_mt5_str} {ts_cfg_str} "
        f"{s.tick_value_mt5:>10.4f} "
        f"{cs_mt5_str} {cs_cfg_str} "
        f"{s.digits:>4} {s.stops_level:>6} "
        f"{s.volume_min:>7g} {s.volume_max:>8g} "
        f"{bot_ok}"
    )


def _render_positions(positions: list[dict]) -> None:
    if not positions:
        print(_dim("  No open positions.\n"))
        return
    hdr = (
        f"  {'Ticket':>10} {'Symbol':<12} {'Dir':>5} {'Lots':>6} "
        f"{'Entry':>12} {'Current':>12} {'SL':>12} {'TP':>12} "
        f"{'P&L':>10} {'Swap':>8} {'Strategy'}"
    )
    print(_bold(hdr))
    print("  " + "─" * (len(hdr) - 2))
    for p in positions:
        pnl_str = f"{p['pnl']:>+10.2f}"
        pnl_col = _green(pnl_str) if p["pnl"] >= 0 else _red(pnl_str)
        dir_col = _green(f"{p['direction']:>5}") if p["direction"] == "BUY" else _red(f"{p['direction']:>5}")
        digits = len(str(p["entry"]).split(".")[-1]) if "." in str(p["entry"]) else 5
        print(
            f"  {p['ticket']:>10} {p['symbol']:<12} {dir_col} {p['lots']:>6g} "
            f"{p['entry']:>12.{digits}f} {p['current']:>12.{digits}f} "
            f"{p['sl']:>12.{digits}f} {p['tp']:>12.{digits}f} "
            f"{pnl_col} {p['swap']:>8.2f}  {p['comment']}"
        )
    total_pnl = sum(p["pnl"] for p in positions)
    total_col = _green if total_pnl >= 0 else _red
    print(f"\n  {'Total P&L:':>60} {total_col(f'{total_pnl:>+10.2f}')}\n")


def _render_snapshot(
    snapshots: list[SymbolSnapshot],
    warn_only: bool,
    elapsed_ms: float,
) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{_bold('MT5 Live Symbol Monitor')}  —  {ts}  "
          f"{_dim(f'({elapsed_ms:.0f} ms fetch)')}")

    print(_bold("\n── Open Positions ─────────────────────────────────────────"))
    _render_positions(_fetch_open_positions())

    print(_bold("── Symbol Prices & Spread Analysis ───────────────────────"))
    if warn_only:
        print(_yellow("  [warn-only mode: showing rejected/mismatched symbols only]\n"))

    reject_count = sum(1 for s in snapshots if s.bot_rejects_spread)
    mismatch_count = sum(1 for s in snapshots if s.has_spec_mismatch)
    total = len(snapshots)
    print(
        f"  Symbols fetched: {_bold(str(total))}   "
        f"Spread rejects: {_red(str(reject_count)) if reject_count else _green('0')}   "
        f"Spec mismatches: {_yellow(str(mismatch_count)) if mismatch_count else _green('0')}\n"
    )

    print(_bold(_HDR))
    print(_dim(_SEP))

    rows_printed = 0
    for s in snapshots:
        row = _fmt_row(s, warn_only)
        if row is not None:
            print(row)
            rows_printed += 1

    if rows_printed == 0:
        print(_green("  All symbols within bot thresholds — no issues detected."))

    # Legend
    print(_dim(_SEP))
    print(
        _dim(
            "  Colours: ")
        + _red("RED") + _dim(" = bot rejects / spec mismatch  ")
        + _yellow("YELLOW") + _dim(" = config pip differs from MT5 tick  ")
        + _cyan("CYAN") + _dim(" = MT5-side spread pips\n")
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def _connect() -> bool:
    if not mt5.initialize():
        print(_red(f"MT5 initialize failed: {mt5.last_error()}"))
        return False
    account = int(os.getenv("BROKER_ACCOUNT", "0"))
    password = os.getenv("BROKER_PASSWORD", "")
    server = os.getenv("BROKER_SERVER", "")
    if not mt5.login(account, password=password, server=server):
        print(_red(f"MT5 login failed: {mt5.last_error()}"))
        mt5.shutdown()
        return False
    info = mt5.account_info()
    print(
        _green(f"Connected: {info.name} | {info.server} | "
               f"Balance={info.balance:.2f} {info.currency} | "
               f"Equity={info.equity:.2f}")
    )
    return True


def _run(symbols: list[str], warn_only: bool, interval: float, watch: bool) -> None:
    while True:
        t0 = time.monotonic()
        snapshots: list[SymbolSnapshot] = []
        failed: list[str] = []
        for sym in symbols:
            snap = _fetch_snapshot(sym)
            if snap is not None:
                snapshots.append(snap)
            else:
                failed.append(sym)
        elapsed_ms = (time.monotonic() - t0) * 1000

        if watch:
            # Clear screen (ANSI)
            print("\033[2J\033[H", end="")

        _render_snapshot(snapshots, warn_only, elapsed_ms)

        if failed:
            print(_dim(f"  Symbols not available on this broker: {', '.join(failed)}\n"))

        if not watch:
            break
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="MT5 Live Symbol Monitor — real-time price/spread/spec diff"
    )
    parser.add_argument(
        "--symbols", "-s",
        default="",
        help="Comma-separated list of symbols (default: all active symbols)",
    )
    parser.add_argument(
        "--watch", "-w",
        action="store_true",
        help="Continuously refresh (press Ctrl+C to stop)",
    )
    parser.add_argument(
        "--interval", "-i",
        type=float,
        default=3.0,
        help="Refresh interval in seconds for --watch mode (default: 3)",
    )
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Only show symbols that the bot would reject or that have spec mismatches",
    )
    args = parser.parse_args()

    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    else:
        # Use ACTIVE_SYMBOLS env var if set (mirrors bot behaviour), else all symbols
        active_env = os.getenv("ACTIVE_SYMBOLS", "")
        if active_env:
            symbols = [s.strip() for s in active_env.split(",") if s.strip()]
        else:
            symbols = ALL_SYMBOLS

    if not _connect():
        sys.exit(1)

    try:
        _run(symbols, args.warn_only, args.interval, args.watch)
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    main()
