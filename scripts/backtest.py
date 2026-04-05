"""Walk-Forward Strategy Backtester.

Fetches 2 years of H1 history per symbol from MT5, runs every strategy
over the candle history in a sliding window, simulates trade outcomes,
and produces a ranked performance report.

Usage
-----
    python scripts/backtest.py                         # all symbols, all strategies
    python scripts/backtest.py --symbols BTCUSD,ETHUSD # specific symbols
    python scripts/backtest.py --strategy ict_smc      # one strategy
    python scripts/backtest.py --seed-db               # write results to strategy_confidence
    python scripts/backtest.py --workers 8             # parallelism (default: CPU count)
    python scripts/backtest.py --candles 5000          # history depth (default: 17520 = 2yr H1)
    python scripts/backtest.py --out results.csv       # save CSV

How it works
------------
For each symbol:
1. Fetch N candles of H1 history from MT5 (cached to .cache/ to avoid
   re-fetching on repeated runs).
2. Slide a window of WINDOW_SIZE candles across the history.
3. At each step, build a MarketContext from the window and call
   strategy.detect().
4. When a signal fires, simulate forward:
   - Walk subsequent candles until price hits SL, TP1, TP2, or TP3.
   - Record the outcome (SL / TP1_only / TP2 / TP3, PnL in R).
5. Aggregate: win rate, avg R, Sharpe-like score, total signals.
6. Print ranked table and optionally write to DB.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
import json
import logging
import os
import pickle
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Optional

# ── Make sure repo root is on sys.path ───────────────────────────────────────
_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from config import settings
from config.symbols import SYMBOLS, asset_class
from backtesting.baseline_benchmarks import evaluate_baselines
from backtesting.research_intake import run_research_intake_pipeline
from backtesting.report import generate_experiment_artifact
from models.market_data import Candle, MarketContext, MarketData
from models.signal import EntrySnapshot, Signal
from utils.helpers import current_session, day_of_week

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("backtest")

# ── Constants ────────────────────────────────────────────────────────────────

WINDOW_SIZE   = 150          # candles fed to strategy.detect() at each step
STEP_SIZE     = 1            # step 1 candle at a time (true walk-forward)
MAX_HOLD_BARS = 48           # max candles to hold an open simulated trade (48h)
CACHE_DIR     = _REPO / ".backtest_cache"
CACHE_DIR.mkdir(exist_ok=True)

# ── Result dataclass ─────────────────────────────────────────────────────────

@dataclass
class TradeResult:
    symbol:    str
    strategy:  str
    direction: str
    entry:     float
    sl:        float
    tp1:       float
    tp2:       float
    tp3:       float
    open_bar:  int            # index in the history array
    outcome:   str = ""       # "SL" | "TP1" | "TP2" | "TP3" | "TIMEOUT"
    pnl_r:     float = 0.0    # PnL in R (1R = distance from entry to SL)
    bars_held: int  = 0


@dataclass
class StrategyStats:
    symbol:       str
    strategy:     str
    signals:      int = 0
    wins:         int = 0       # any TP hit
    tp1_hits:     int = 0
    tp2_hits:     int = 0
    tp3_hits:     int = 0
    sl_hits:      int = 0
    timeouts:     int = 0
    total_r:      float = 0.0
    avg_r:        float = 0.0
    win_rate:     float = 0.0
    profit_factor: float = 0.0
    score:        float = 0.0   # composite 0–1 used for confidence seeding


# ── Indicator helpers (mirrors AnalysisAgent, no DB dependency) ──────────────

def _sma(values: list[float], period: int) -> float:
    if len(values) < period:
        return 0.0
    return round(sum(values[-period:]) / period, 5)


def _rsi(closes: list[float], period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    recent = deltas[-period:]
    gains  = [d for d in recent if d > 0]
    losses = [-d for d in recent if d < 0]
    if not gains and not losses:
        return 50.0
    avg_gain = sum(gains) / period if gains else 0.0
    avg_loss = sum(losses) / period if losses else 0.0001
    rs = avg_gain / avg_loss
    return round(100 - 100 / (1 + rs), 2)


def _atr(candles: list[Candle], period: int = 14) -> float:
    if len(candles) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(candles)):
        h, l, pc = candles[i].high, candles[i].low, candles[i - 1].close
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    recent = trs[-period:]
    return round(sum(recent) / len(recent), 5) if recent else 0.0


def _build_context(symbol: str, window: list[Candle]) -> MarketContext:
    """Build a MarketContext from a candle window — no broker/DB needed."""
    closes  = [c.close for c in window]
    mid     = window[-1].close
    atr     = _atr(window, 14)
    rsi_val = _rsi(closes, 14)
    sma_f   = _sma(closes, settings.SMA_FAST_PERIOD)
    sma_s   = _sma(closes, settings.SMA_SLOW_PERIOD)
    p_sma_f = _sma(closes[:-1], settings.SMA_FAST_PERIOD) if len(closes) > settings.SMA_FAST_PERIOD else 0.0
    p_sma_s = _sma(closes[:-1], settings.SMA_SLOW_PERIOD) if len(closes) > settings.SMA_SLOW_PERIOD else 0.0

    if atr > 0 and len(closes) >= 14:
        rng = max(closes[-14:]) - min(closes[-14:])
        if rng > atr * 3:
            regime = "volatile"
        elif sma_f != 0 and sma_s != 0 and abs(sma_f - sma_s) > atr:
            regime = "trending"
        else:
            regime = "ranging"
    else:
        regime = "unknown"

    trend = "bullish" if sma_f > sma_s else ("bearish" if sma_f < sma_s else "neutral")

    ts = window[-1].timestamp
    return MarketContext(
        symbol=symbol,
        current_price=mid,
        bid=mid,
        ask=mid,
        spread=0.0,
        volume=window[-1].volume,
        timestamp=ts,
        sma_fast=sma_f,
        sma_slow=sma_s,
        prev_sma_fast=p_sma_f,
        prev_sma_slow=p_sma_s,
        rsi=rsi_val,
        atr=atr,
        regime=regime,
        trend_direction=trend,
        session=current_session(ts),
        day_of_week=ts.strftime("%A"),
        near_news_event=False,
        candles=window,
    )


# ── MT5 data fetching ────────────────────────────────────────────────────────

def _cache_path(symbol: str, candle_count: int) -> Path:
    return CACHE_DIR / f"{symbol}_H1_{candle_count}.pkl"


def _fetch_candles(symbol: str, candle_count: int) -> list[Candle]:
    """Fetch from MT5 with disk cache.  Returns [] on failure."""
    cache = _cache_path(symbol, candle_count)
    if cache.exists():
        age_hours = (time.time() - cache.stat().st_mtime) / 3600
        if age_hours < 6:
            try:
                with open(cache, "rb") as f:
                    candles = pickle.load(f)
                logger.debug("%s: loaded %d candles from cache", symbol, len(candles))
                return candles
            except Exception:
                pass

    try:
        import MetaTrader5 as mt5
        from broker.mt5_connector import MT5Connector
    except ImportError:
        logger.warning("MetaTrader5 not installed — cannot fetch live data")
        return []

    conn = MT5Connector()
    if not conn.connect():
        logger.warning("MT5 connection failed — cannot fetch %s", symbol)
        return []

    try:
        candles = conn.get_candles(symbol, "H1", candle_count)
        if candles:
            with open(cache, "wb") as f:
                pickle.dump(candles, f)
            logger.info("%s: fetched %d H1 candles from MT5", symbol, len(candles))
        return candles
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", symbol, exc)
        return []
    finally:
        try:
            mt5.shutdown()
        except Exception:
            pass


# ── Trade outcome simulator ──────────────────────────────────────────────────

def _simulate_trade(
    signal: Signal,
    future_candles: list[Candle],
) -> tuple[str, float, int]:
    """Walk future candles and determine the first level hit.

    Returns (outcome, pnl_in_R, bars_held).
    """
    if not future_candles or signal.stop_loss == 0:
        return "TIMEOUT", 0.0, 0

    entry = signal.entry_price
    sl    = signal.stop_loss
    tp1   = signal.take_profit_1
    tp2   = signal.take_profit_2
    tp3   = signal.take_profit_3
    is_buy = signal.direction == "BUY"
    r_dist = abs(entry - sl)
    if r_dist == 0:
        return "TIMEOUT", 0.0, 0

    tp1_hit = tp2_hit = False

    for i, candle in enumerate(future_candles[:MAX_HOLD_BARS]):
        hi, lo = candle.high, candle.low

        if is_buy:
            if lo <= sl:
                # SL hit — partial credit if TP1 was already hit
                if tp2_hit:
                    return "TP2", (tp2 - entry) / r_dist * 0.7 - 0.3, i + 1
                if tp1_hit:
                    return "TP1", (tp1 - entry) / r_dist * 0.4 - 0.6, i + 1
                return "SL", -1.0, i + 1
            if tp3 > 0 and hi >= tp3:
                return "TP3", (tp3 - entry) / r_dist, i + 1
            if tp2 > 0 and hi >= tp2:
                tp2_hit = True
            if tp1 > 0 and hi >= tp1:
                tp1_hit = True
        else:  # SELL
            if hi >= sl:
                if tp2_hit:
                    return "TP2", (entry - tp2) / r_dist * 0.7 - 0.3, i + 1
                if tp1_hit:
                    return "TP1", (entry - tp1) / r_dist * 0.4 - 0.6, i + 1
                return "SL", -1.0, i + 1
            if tp3 > 0 and lo <= tp3:
                return "TP3", (entry - tp3) / r_dist, i + 1
            if tp2 > 0 and lo <= tp2:
                tp2_hit = True
            if tp1 > 0 and lo <= tp1:
                tp1_hit = True

    # Held to timeout — exit at last close, estimate PnL
    last_close = future_candles[min(MAX_HOLD_BARS - 1, len(future_candles) - 1)].close
    pnl_r = (last_close - entry) / r_dist if is_buy else (entry - last_close) / r_dist
    return "TIMEOUT", round(pnl_r, 3), min(MAX_HOLD_BARS, len(future_candles))


# ── Per-symbol backtester ────────────────────────────────────────────────────

def _backtest_symbol(
    symbol: str,
    candles: list[Candle],
    strategies: list,
) -> list[TradeResult]:
    """Run all strategies over a symbol's candle history."""
    results: list[TradeResult] = []
    n = len(candles)

    if n < WINDOW_SIZE + 10:
        logger.warning("%s: only %d candles — skipping (need %d)", symbol, n, WINDOW_SIZE + 10)
        return results

    # Track last signal bar per strategy to enforce a cooldown (avoid signal spam)
    last_signal_bar: dict[str, int] = {}
    SIGNAL_COOLDOWN = 5  # bars between signals per strategy

    logger.info("%s: walking %d candles across %d strategies…", symbol, n, len(strategies))

    for bar in range(WINDOW_SIZE, n - MAX_HOLD_BARS, STEP_SIZE):
        window = candles[bar - WINDOW_SIZE: bar]
        ctx = _build_context(symbol, window)

        for strat in strategies:
            sname = strat.name
            # Enforce cooldown
            if bar - last_signal_bar.get(sname, 0) < SIGNAL_COOLDOWN:
                continue

            try:
                signal = strat.detect(ctx)
            except Exception:
                continue

            if signal is None:
                continue

            last_signal_bar[sname] = bar
            future = candles[bar: bar + MAX_HOLD_BARS + 1]
            outcome, pnl_r, bars_held = _simulate_trade(signal, future)

            results.append(TradeResult(
                symbol=symbol,
                strategy=sname,
                direction=signal.direction,
                entry=signal.entry_price,
                sl=signal.stop_loss,
                tp1=signal.take_profit_1,
                tp2=signal.take_profit_2,
                tp3=signal.take_profit_3,
                open_bar=bar,
                outcome=outcome,
                pnl_r=round(pnl_r, 4),
                bars_held=bars_held,
            ))

    return results


# ── Aggregator ───────────────────────────────────────────────────────────────

def _aggregate(results: list[TradeResult]) -> list[StrategyStats]:
    """Collapse raw trade results into per-strategy-symbol stats."""
    buckets: dict[tuple[str, str], list[TradeResult]] = {}
    for r in results:
        key = (r.symbol, r.strategy)
        buckets.setdefault(key, []).append(r)

    stats: list[StrategyStats] = []
    for (sym, strat), trades in buckets.items():
        n = len(trades)
        if n == 0:
            continue

        wins     = [t for t in trades if t.outcome in ("TP1", "TP2", "TP3")]
        tp1_hits = sum(1 for t in trades if t.outcome == "TP1")
        tp2_hits = sum(1 for t in trades if t.outcome == "TP2")
        tp3_hits = sum(1 for t in trades if t.outcome == "TP3")
        sl_hits  = sum(1 for t in trades if t.outcome == "SL")
        timeouts = sum(1 for t in trades if t.outcome == "TIMEOUT")

        gross_profit = sum(t.pnl_r for t in trades if t.pnl_r > 0)
        gross_loss   = abs(sum(t.pnl_r for t in trades if t.pnl_r < 0))
        total_r      = sum(t.pnl_r for t in trades)
        avg_r        = total_r / n
        win_rate     = len(wins) / n
        pf           = gross_profit / gross_loss if gross_loss > 0 else gross_profit

        # Composite score: blend win rate, avg R, and profit factor → 0–1
        # Weights: 40% win rate, 40% avg R normalised, 20% PF normalised
        avg_r_norm = max(0.0, min(1.0, (avg_r + 2) / 4))   # map [-2, 2] → [0, 1]
        pf_norm    = max(0.0, min(1.0, pf / 3))             # map [0, 3]  → [0, 1]
        score      = round(0.40 * win_rate + 0.40 * avg_r_norm + 0.20 * pf_norm, 4)

        stats.append(StrategyStats(
            symbol=sym,
            strategy=strat,
            signals=n,
            wins=len(wins),
            tp1_hits=tp1_hits,
            tp2_hits=tp2_hits,
            tp3_hits=tp3_hits,
            sl_hits=sl_hits,
            timeouts=timeouts,
            total_r=round(total_r, 3),
            avg_r=round(avg_r, 3),
            win_rate=round(win_rate, 4),
            profit_factor=round(pf, 3),
            score=score,
        ))

    return sorted(stats, key=lambda s: s.score, reverse=True)


# ── Reporter ─────────────────────────────────────────────────────────────────

def _print_report(stats: list[StrategyStats]) -> None:
    COL = "{:<10} {:<24} {:>7} {:>7} {:>7} {:>8} {:>8} {:>8}"
    header = COL.format("Symbol", "Strategy", "Signals", "WinRate", "AvgR", "TotalR", "PF", "Score")
    sep    = "─" * len(header)
    print(f"\n{'BACKTEST RESULTS':^{len(header)}}")
    print(sep)
    print(header)
    print(sep)

    prev_score_group = None
    for s in stats:
        tier = "★★★" if s.score >= 0.60 else ("★★ " if s.score >= 0.45 else "★  ")
        group = round(s.score, 1)
        if group != prev_score_group:
            prev_score_group = group
        print(COL.format(
            s.symbol[:10],
            s.strategy[:24],
            s.signals,
            f"{s.win_rate:.1%}",
            f"{s.avg_r:+.3f}",
            f"{s.total_r:+.2f}",
            f"{s.profit_factor:.2f}",
            f"{s.score:.4f} {tier}",
        ))

    print(sep)
    total_signals = sum(s.signals for s in stats)
    total_wins    = sum(s.wins for s in stats)
    overall_wr    = total_wins / total_signals if total_signals else 0
    print(f"  Total signals: {total_signals}  |  Overall win rate: {overall_wr:.1%}")
    print()


def _save_csv(stats: list[StrategyStats], path: str) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "symbol", "strategy", "signals", "wins", "tp1_hits", "tp2_hits",
            "tp3_hits", "sl_hits", "timeouts", "total_r", "avg_r",
            "win_rate", "profit_factor", "score",
        ])
        w.writeheader()
        for s in stats:
            w.writerow(s.__dict__)
    logger.info("CSV saved → %s", path)


def _run_ml4t_benchmark(
    candle_map: dict[str, list[Candle]],
    *,
    purge_size: int,
    embargo_size: int,
    output_path: str,
) -> dict:
    """Run baseline model benchmarks over all symbols and export one artifact."""
    symbol_reports: dict[str, dict] = {}

    for symbol, candles in candle_map.items():
        results = evaluate_baselines(
            candles,
            purge_size=purge_size,
            embargo_size=embargo_size,
        )
        models = [
            {
                "name": r.model,
                "accuracy": round(r.accuracy, 4),
                "avg_strategy_return": round(r.avg_strategy_return, 6),
                "trades": r.trades,
            }
            for r in results
        ]
        symbol_reports[symbol] = {"models": models}

    artifact = generate_experiment_artifact(
        experiment_name="ml4t_baseline_benchmarks",
        symbol_reports=symbol_reports,
        metadata={
            "purge_size": purge_size,
            "embargo_size": embargo_size,
            "validation": "purged_walk_forward",
        },
    )

    out_file = Path(output_path) if output_path else (_REPO / "backtesting" / "runs" / "ml4t_baselines.json")
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=2)

    logger.info("ML4T baseline benchmark artifact saved → %s", out_file)
    return artifact


def _run_research_intake(
    *,
    candidates_path: str,
    curated_sources_path: str,
    scoring_rubric_path: str,
    promotion_checklist_path: str,
    output_path: str,
) -> dict:
    """Score research candidates and export promotion decisions as an experiment artifact."""
    out_file = Path(output_path) if output_path else (_REPO / "backtesting" / "runs" / "research_intake.json")
    artifact = run_research_intake_pipeline(
        candidates_path=candidates_path,
        curated_sources_path=curated_sources_path,
        scoring_rubric_path=scoring_rubric_path,
        promotion_checklist_path=promotion_checklist_path,
        output_path=out_file,
    )
    logger.info("Research intake artifact saved → %s", out_file)
    return artifact


# ── DB seeder ────────────────────────────────────────────────────────────────

def _seed_db(stats: list[StrategyStats]) -> None:
    """Write per-strategy confidence to the DB, keyed by strategy name.

    Uses the best score across all symbols for each strategy name as the
    new confidence — the live system can still adjust per-symbol via the
    learning agent.
    """
    from database.db import Database
    db = Database()

    # Aggregate best score per strategy name (across all symbols)
    best: dict[str, float] = {}
    for s in stats:
        if s.signals < 10:       # ignore strategies with too few signals
            continue
        key = s.strategy
        if key not in best or s.score > best[key]:
            best[key] = s.score

    for strat_name, score in best.items():
        # Clamp to [CONFIDENCE_MIN, CONFIDENCE_MAX]
        conf = max(0.10, min(1.00, score))
        db.upsert_confidence(strat_name, conf, 0, 0)
        logger.info("Seeded %s → confidence=%.4f", strat_name, conf)

    db.close()
    logger.info("DB seeded with %d strategy confidence values", len(best))


# ── Strategy factory ─────────────────────────────────────────────────────────

def _build_strategies(filter_name: str | None = None) -> list:
    """Instantiate all backtestable strategies (no API calls, no DB)."""
    from strategies.sma_crossover import SmaCrossoverStrategy
    from strategies.ict_strategy import ICTStrategy

    strats = [
        SmaCrossoverStrategy(),
        ICTStrategy(),
    ]

    if filter_name:
        strats = [s for s in strats if filter_name in s.name]
        if not strats:
            logger.warning("No strategy matches '%s' — running all", filter_name)
            return _build_strategies()

    return strats


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Walk-forward strategy backtester")
    parser.add_argument("--symbols",  default="",   help="Comma-separated symbol list (default: all)")
    parser.add_argument("--strategy", default="",   help="Filter by strategy name substring")
    parser.add_argument("--candles",  type=int, default=17_520, help="History depth in H1 bars (default: 17520 = 2yr)")
    parser.add_argument("--workers",  type=int, default=os.cpu_count() or 4, help="Parallel workers")
    parser.add_argument("--seed-db",  action="store_true", help="Write confidence values to DB")
    parser.add_argument("--out",      default="",   help="Save results to CSV file")
    parser.add_argument("--no-cache", action="store_true", help="Force re-fetch from MT5 (ignore cache)")
    parser.add_argument("--ml4t-benchmark", action="store_true", help="Run baseline ML4T benchmark workflow")
    parser.add_argument("--benchmark-out", default="", help="Save ML4T benchmark artifact JSON")
    parser.add_argument("--purge-size", type=int, default=5, help="Purged split buffer size")
    parser.add_argument("--embargo-size", type=int, default=3, help="Embargo gap between folds")
    parser.add_argument("--research-intake", action="store_true", help="Run research candidate scoring + promotion gates")
    parser.add_argument("--research-candidates", default="", help="Path to research candidate backlog JSON")
    parser.add_argument("--research-sources", default="", help="Path to curated sources JSON")
    parser.add_argument("--research-rubric", default="", help="Path to scoring rubric JSON")
    parser.add_argument("--research-checklist", default="", help="Path to promotion checklist JSON")
    parser.add_argument("--research-out", default="", help="Save research intake artifact JSON")
    args = parser.parse_args()

    research_defaults = {
        "candidates": _REPO / "research" / "candidate_backlog.json",
        "sources": _REPO / "research" / "curated_sources.json",
        "rubric": _REPO / "research" / "scoring_rubric.json",
        "checklist": _REPO / "research" / "promotion_checklist.json",
    }

    # Standalone research intake mode: no MT5 dependency, no backtest run.
    if args.research_intake and not args.ml4t_benchmark:
        artifact = _run_research_intake(
            candidates_path=args.research_candidates or str(research_defaults["candidates"]),
            curated_sources_path=args.research_sources or str(research_defaults["sources"]),
            scoring_rubric_path=args.research_rubric or str(research_defaults["rubric"]),
            promotion_checklist_path=args.research_checklist or str(research_defaults["checklist"]),
            output_path=args.research_out,
        )
        promoted = [
            key
            for key, report in artifact.get("symbols", {}).items()
            if report.get("promotion", {}).get("promoted")
        ]
        print("\nRESEARCH INTAKE PROMOTION")
        print("─" * 60)
        print(f"  Candidates scored: {len(artifact.get('symbols', {}))}")
        print(f"  Promoted:          {len(promoted)}")
        if promoted:
            print("  Promotion list:")
            for item in promoted:
                print(f"    - {item}")
        print("─" * 60)
        return

    target_symbols = (
        [s.strip() for s in args.symbols.split(",") if s.strip()]
        if args.symbols else SYMBOLS
    )
    strategies = _build_strategies(args.strategy or None)

    logger.info(
        "Backtesting %d symbols × %d strategies | %d H1 bars | %d workers",
        len(target_symbols), len(strategies), args.candles, args.workers,
    )
    logger.info("Strategies: %s", ", ".join(s.name for s in strategies))

    if args.no_cache:
        for sym in target_symbols:
            _cache_path(sym, args.candles).unlink(missing_ok=True)

    # ── Fetch all candle data ────────────────────────────────────────────
    t0 = time.time()
    candle_map: dict[str, list[Candle]] = {}
    logger.info("Fetching historical data…")

    with concurrent.futures.ThreadPoolExecutor(max_workers=min(args.workers, 4)) as ex:
        futures = {ex.submit(_fetch_candles, sym, args.candles): sym for sym in target_symbols}
        for fut in concurrent.futures.as_completed(futures):
            sym = futures[fut]
            candles = fut.result()
            if candles:
                candle_map[sym] = candles
            else:
                logger.warning("%s: no data — skipping", sym)

    logger.info("Data ready for %d/%d symbols in %.1fs", len(candle_map), len(target_symbols), time.time() - t0)

    if not candle_map:
        logger.error("No candle data available. Is MT5 running?")
        sys.exit(1)

    # ── Run walk-forward in parallel ─────────────────────────────────────
    all_results: list[TradeResult] = []

    def _run(sym: str) -> list[TradeResult]:
        # Each worker gets its own strategy instances (not thread-safe to share)
        local_strats = _build_strategies(args.strategy or None)
        return _backtest_symbol(sym, candle_map[sym], local_strats)

    t1 = time.time()
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.workers) as ex:
        futures = {ex.submit(_run, sym): sym for sym in candle_map}
        done = 0
        for fut in concurrent.futures.as_completed(futures):
            sym = futures[fut]
            done += 1
            try:
                results = fut.result()
                all_results.extend(results)
                logger.info("[%d/%d] %s — %d signals fired", done, len(candle_map), sym, len(results))
            except Exception as exc:
                logger.warning("%s failed: %s", sym, exc)

    logger.info("Backtest complete in %.1fs — %d total simulated trades", time.time() - t1, len(all_results))

    if args.ml4t_benchmark:
        artifact = _run_ml4t_benchmark(
            candle_map,
            purge_size=args.purge_size,
            embargo_size=args.embargo_size,
            output_path=args.benchmark_out,
        )
        print("\nML4T BASELINE BENCHMARK")
        print("─" * 60)
        for symbol, report in artifact.get("symbols", {}).items():
            models = report.get("models", [])
            if not models:
                continue
            best = models[0]
            print(
                f"  {symbol:<10} {best['name']:<24} "
                f"acc={best['accuracy']:.2%} avg_ret={best['avg_strategy_return']:+.4f}"
            )
        print("─" * 60)

    if args.research_intake:
        artifact = _run_research_intake(
            candidates_path=args.research_candidates or str(research_defaults["candidates"]),
            curated_sources_path=args.research_sources or str(research_defaults["sources"]),
            scoring_rubric_path=args.research_rubric or str(research_defaults["rubric"]),
            promotion_checklist_path=args.research_checklist or str(research_defaults["checklist"]),
            output_path=args.research_out,
        )
        promoted = [
            key
            for key, report in artifact.get("symbols", {}).items()
            if report.get("promotion", {}).get("promoted")
        ]

        print("\nRESEARCH INTAKE PROMOTION")
        print("─" * 60)
        print(f"  Candidates scored: {len(artifact.get('symbols', {}))}")
        print(f"  Promoted:          {len(promoted)}")
        if promoted:
            print("  Promotion list:")
            for item in promoted:
                print(f"    - {item}")
        print("─" * 60)

    # ── Aggregate and report ─────────────────────────────────────────────
    stats = _aggregate(all_results)
    _print_report(stats)

    if args.out:
        _save_csv(stats, args.out)

    if args.seed_db:
        _seed_db(stats)

    # ── Per-asset-class summary ──────────────────────────────────────────
    print("\nBEST SETUP PER ASSET CLASS:")
    print("─" * 60)
    classes: dict[str, list[StrategyStats]] = {}
    for s in stats:
        ac = asset_class(s.symbol)
        classes.setdefault(ac, []).append(s)
    for ac, ac_stats in sorted(classes.items()):
        best = ac_stats[0]  # already sorted by score
        print(f"  {ac:<16}  {best.symbol:<10} + {best.strategy:<24}  score={best.score:.4f}  wr={best.win_rate:.1%}")
    print()


if __name__ == "__main__":
    main()
