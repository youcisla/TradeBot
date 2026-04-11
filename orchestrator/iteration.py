"""run_iteration — extracted from main.py's _run_iteration()."""

from __future__ import annotations

import concurrent.futures
import logging
import time
from typing import cast

from config import settings
from database.db import Database
from filters.data_validator import DataValidationError
from models.market_data import MarketContext
from models.signal import Signal
from agents.analysis_agent import AnalysisAgent
from agents.crucix_agent import CrucixAgent
from agents.execution_agent import ExecutionAgent
from agents.learning_agent import LearningAgent
from agents.logging_agent import LoggingAgent
from agents.market_agent import MarketAgent
from agents.risk_agent import RiskAgent
from agents.sniper_entry_guard import SniperEntryGuard, SniperVerdict
from agents.strategy_agent import StrategyAgent
from agents.trade_manager import TradeManagerAgent
from broker.connector import BrokerConnector
from utils import telegram_bot
from utils import terminal_ui as tui
from utils.helpers import is_market_open
from utils.opportunity_lifecycle import OpportunityLifecycleManager
from utils.symbol_event_tracker import SymbolEventTracker

logger = logging.getLogger(__name__)


def run_iteration(
    *,
    loop_count: int,
    active_symbols: list[str],
    db: Database,
    broker: BrokerConnector,
    crucix_agent: CrucixAgent,
    market_agent: MarketAgent,
    analysis_agent: AnalysisAgent,
    strategy_agent: StrategyAgent,
    risk_agent: RiskAgent,
    execution_agent: ExecutionAgent,
    trade_manager: TradeManagerAgent,
    learning: LearningAgent,
    log_agent: LoggingAgent,
    council,  # noqa: F841 — kept for call signature compatibility
    sniper_guard: SniperEntryGuard | None,
    symbol_event_tracker: SymbolEventTracker,
    last_scan_ts: dict[str, float],
    scan_cooldown: float,
    deferred_entries: list[dict[str, object]],
    metrics: dict[str, float],
    symbol_fail_count: dict[str, int],
    symbol_disabled_until: dict[str, float],
    symbol_max_fails: int,
    symbol_disable_secs: float,
    session_profile: str,
    opportunity_lifecycle: OpportunityLifecycleManager,
    weekend_symbols: list[str] | None = None,
    scan_workers: int = 6,
    risk_reject_reason_counts: dict[str, int] | None = None,
) -> None:
    """Single iteration of the trading loop.

    Uses a **scan-all → rank → execute-best** pipeline:
    1. Scan every symbol and collect ALL signals from ALL strategies
    2. Rank by confidence (highest first)
    3. Execute top signals that pass risk validation (up to available slots)

    This ensures we never miss a high-confidence setup just because another
    symbol happened to be checked first in the list.
    """

    def _to_float(value: object, default: float = 0.0) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            try:
                return float(value)
            except ValueError:
                return default
        return default

    # ── Weekend mode notice (logged once per entry into weekend window) ──
    if weekend_symbols is not None:
        logger.debug(
            "Weekend mode active — scanning only: %s (3-TF ICT: M15+H4, H1+D1, H4+W1)",
            ", ".join(weekend_symbols),
        )

    iter_start_ts = time.monotonic()
    iter_trace_id = f"iter-{loop_count}-{int(time.time())}"
    hard_budget_enabled = settings.ORCHESTRATION_HARD_BUDGET_ENABLED
    max_scan_ms = settings.ORCHESTRATION_MAX_SCAN_MS
    max_rank_ms = settings.ORCHESTRATION_MAX_RANK_MS
    max_exec_ms = settings.ORCHESTRATION_MAX_EXEC_MS
    max_iter_ms = settings.ORCHESTRATION_MAX_ITERATION_MS

    if settings.ORCHESTRATION_ENABLE_ITERATION_TRACE:
        db.log_agent_event(
            "logging",
            "debug",
            "Iteration started",
            {
                "trace_id": iter_trace_id,
                "loop": loop_count,
                "session": session_profile,
                "scan_workers": scan_workers,
            },
        )

    # ── Crucix macro sweep (once per iteration, logs to DB) ──────────────
    crucix_agent.run()

    # ── Monitor existing trades first ────────────────────────────────────
    _tui = tui.get_ui()
    if _tui:
        _tui.set_agent_status("trade_mgr", "monitoring open positions")
    open_before = {t.id for t in trade_manager.get_open_trades()}
    trade_manager.monitor()
    open_after = {t.id for t in trade_manager.get_open_trades()}

    # Track trade open/close events per symbol
    for t in trade_manager.get_open_trades():
        open_time = getattr(t, 'open_time', None)
        ts = open_time.timestamp() if open_time and hasattr(open_time, 'timestamp') else time.time()
        symbol_event_tracker.update(t.symbol, "last_trade_open", ts)
    just_closed_ids = open_before - open_after
    for trade_id in just_closed_ids:
        closed_trade = db.get_trade(trade_id)
        if closed_trade:
            close_time = getattr(closed_trade, 'close_time', None)
            ts = close_time.timestamp() if close_time and hasattr(close_time, 'timestamp') else time.time()
            symbol_event_tracker.update(closed_trade.symbol, "last_trade_close", ts)
            learning.review_trade(closed_trade)
            log_agent.log_trade_to_csv(closed_trade)
            log_agent.log_trade(closed_trade.id, "CLOSED",
                                f"{closed_trade.close_reason} PnL={closed_trade.pnl:.2f}")
            opportunity_lifecycle.register_trade_close(closed_trade)

    rolled_symbols = opportunity_lifecycle.on_iteration_start(
        symbols=active_symbols,
        open_trades=trade_manager.get_open_trades(),
    )
    if rolled_symbols:
        logger.info(
            "Opportunity lifecycle rollover: %s",
            ", ".join(rolled_symbols[:10]),
        )

    metrics["loops"] = metrics.get("loops", 0) + 1
    # council_reviews_this_loop = 0  # DISABLED — ICT-only mode

    # ── Skip new signals if paused ───────────────────────────────────────
    if telegram_bot.is_paused():
        logger.warning("Bot is PAUSED — skipping signal detection (loop %d). "
                       "Use /resume or the dashboard to resume.", loop_count)
        return

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 1: Scan ALL symbols — collect every signal
    # ══════════════════════════════════════════════════════════════════════
    all_signals: list[Signal] = []
    # Map signal → its MarketContext for the sniper guard
    signal_contexts: dict[int, MarketContext] = {}  # id(signal) → MarketContext

    # Symbols with open positions — skip strategy scan (saves compute,
    # avoids duplicate-reject log spam)
    open_symbols = {t.symbol for t in trade_manager.get_open_trades()}

    now_mono = time.monotonic()
    scan_phase_start = now_mono
    scanned: list[str] = []
    skipped_cooldown: list[str] = []
    ipc_fail_symbols: list[str] = []   # IPC failures in this iteration only
    scan_error_symbols: list[str] = []

    # Priority scan order: always evaluate BTC first (if tradable), then
    # continue through the full active universe so no symbol is forgotten.
    scan_symbols = active_symbols[:]
    btc_symbol = settings.BTC_PRIORITY_SYMBOL
    if btc_symbol in scan_symbols:
        scan_symbols = [btc_symbol] + [s for s in scan_symbols if s != btc_symbol]

    def _process_single_symbol(symbol: str):
        if not is_market_open(symbol):
            return (symbol, "skip", False, None, None, None, False)
        if weekend_symbols is not None and symbol not in weekend_symbols:
            return (symbol, "skip", False, None, None, None, False)
        if symbol in open_symbols:
            return (symbol, "skip", False, None, None, None, False)

        disabled_until = symbol_disabled_until.get(symbol, 0.0)
        is_re_enabled = False
        if disabled_until > 0.0:
            if now_mono < disabled_until:
                return (symbol, "skip", False, None, None, None, False)
            else:
                is_re_enabled = True

        symbol_cooldown = scan_cooldown
        if symbol == btc_symbol:
            symbol_cooldown = max(0, settings.BTC_PRIORITY_SCAN_COOLDOWN_SECONDS)

        # BTC always scans — it needs fresh data every loop regardless of cooldown.
        if symbol == btc_symbol:
            try:
                if _tui:
                    _tui.set_agent_status("market", f"fetching {symbol}")
                data = market_agent.get_data(symbol)
            except DataValidationError as e:
                err_str = str(e)
                is_ipc = ("IPC" in err_str or "No tick data" in err_str
                          or "-10004" in err_str or "Terminal: Call failed" in err_str)
                return (symbol, "error", is_re_enabled, None, None, err_str, is_ipc)

            if _tui:
                _tui.set_agent_status("analysis", f"analyzing {symbol}")
            context = analysis_agent.analyze(data)

            if _tui:
                _tui.set_agent_status("strategy", f"scanning {symbol}")
            signals = strategy_agent.detect_all(context)

            return (symbol, "success", is_re_enabled, context, signals, None, False)

        # Non-BTC symbols: skip aggressively if cooldown hasn't expired and
        # no new candle has arrived since the last scan.
        if now_mono - last_scan_ts.get(symbol, 0.0) < symbol_cooldown:
            # Only force a rescan if a genuine new candle has arrived.
            if settings.EVENT_DRIVEN_RESCAN_ON_NEW_CANDLE:
                last_candle_ts = symbol_event_tracker.get(symbol, "last_candle")
                if last_candle_ts > 0 and (time.time() - last_candle_ts) < symbol_cooldown:
                    return (symbol, "cooldown", is_re_enabled, None, None, None, False)
            else:
                return (symbol, "cooldown", is_re_enabled, None, None, None, False)

        try:
            if _tui:
                _tui.set_agent_status("market", f"fetching {symbol}")
            data = market_agent.get_data(symbol)
        except DataValidationError as e:
            err_str = str(e)
            is_ipc = ("IPC" in err_str or "No tick data" in err_str
                      or "-10004" in err_str or "Terminal: Call failed" in err_str)
            return (symbol, "error", is_re_enabled, None, None, err_str, is_ipc)

        if _tui:
            _tui.set_agent_status("analysis", f"analyzing {symbol}")
        context = analysis_agent.analyze(data)

        if _tui:
            _tui.set_agent_status("strategy", f"scanning {symbol}")
        signals = strategy_agent.detect_all(context)

        return (symbol, "success", is_re_enabled, context, signals, None, False)

    # MT5 IPC is thread-sensitive; concurrent symbol scans can produce random
    # tick/candle misses. Keep MT5 scans single-threaded for reliability.
    is_mt5_broker = broker.__class__.__name__ == "MT5Connector"
    scan_results: list[tuple[str, str, bool, MarketContext | None, list[Signal] | None, str | None, bool]] = []

    if is_mt5_broker:
        for symbol in scan_symbols:
            scan_results.append(_process_single_symbol(symbol))
    else:
        futures = []
        worker_count = max(1, min(scan_workers, len(scan_symbols)))
        with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
            for symbol in scan_symbols:
                futures.append(executor.submit(_process_single_symbol, symbol))
        for future in concurrent.futures.as_completed(futures):
            scan_results.append(future.result())

    for res in scan_results:
        symbol, status, is_re_enabled, context, signals, err_str, is_ipc = res

        if status == "skip":
            continue

        if is_re_enabled:
            logger.info("Re-enabling %s after IPC cooldown (was disabled for 1h)", symbol)
            symbol_fail_count[symbol] = 0
            symbol_disabled_until[symbol] = 0.0
            try:
                db.save_symbol_fault(symbol, 0, None)
            except Exception:
                logger.debug("Could not clear symbol fault for %s", symbol)

        if status == "cooldown":
            skipped_cooldown.append(symbol)
            continue

        if status == "error":
            scan_error_symbols.append(symbol)
            is_stuck_quote = bool(err_str) and "Stuck quote" in err_str

            if is_ipc or is_stuck_quote:
                if is_ipc:
                    ipc_fail_symbols.append(symbol)
                count = symbol_fail_count.get(symbol, 0) + 1
                symbol_fail_count[symbol] = count
                if count >= symbol_max_fails:
                    symbol_disabled_until[symbol] = now_mono + symbol_disable_secs
                    fail_label = "IPC" if is_ipc else "stuck-quote"
                    logger.warning(
                        "Auto-disabling %s for 1h after %d consecutive %s failures",
                        symbol, count, fail_label,
                    )
                    log_agent.record(
                        "market",
                        f"{symbol} auto-disabled for 1h — {count} consecutive {fail_label} failures",
                    )
                    try:
                        from datetime import timedelta, datetime as dt, timezone as tz
                        db.save_symbol_fault(
                            symbol, count,
                            dt.now(tz.utc) + timedelta(seconds=symbol_disable_secs),
                        )
                    except Exception:
                        logger.debug("Could not persist symbol fault for %s", symbol)
            else:
                symbol_fail_count[symbol] = 0
            logger.warning("Data validation failed for %s: %s — skipping", symbol, err_str)
            continue

        # Mark cooldown only for successful/non-error scans. Errors should
        # retry quickly in the next loop so opportunities are not missed.
        last_scan_ts[symbol] = now_mono

        # Success
        symbol_fail_count[symbol] = 0
        if context and context.candles:
            symbol_event_tracker.update(symbol, "last_candle", context.candles[-1].timestamp.timestamp())
        scanned.append(symbol)

        if signals:
            symbol_event_tracker.update(symbol, "last_signal", time.time())
            if _tui:
                for sig in signals:
                    _tui.add_event("strategy", "info", f"{sig.direction} {sig.symbol} conf={sig.confidence:.0%}")
            if context is not None:
                for sig in signals:
                    signal_contexts[id(sig)] = context
            all_signals.extend(signals)

    metrics["scanned_symbols"] = metrics.get("scanned_symbols", 0) + len(scanned)
    metrics["raw_signals"] = metrics.get("raw_signals", 0) + len(all_signals)
    metrics["last_scan_latency_ms"] = (time.monotonic() - scan_phase_start) * 1000.0
    if hard_budget_enabled and metrics["last_scan_latency_ms"] > max_scan_ms:
        metrics["budget_scan_hits"] = metrics.get("budget_scan_hits", 0) + 1
        logger.warning(
            "Scan hard budget exceeded: %.1fms > %.1fms — reducing ranked workload this loop",
            metrics["last_scan_latency_ms"],
            max_scan_ms,
        )

    # Graceful degradation: abort ranking/execution when scan quality is poor.
    sampled = len(scanned) + len(scan_error_symbols)
    scan_error_rate = (len(scan_error_symbols) / sampled) if sampled > 0 else 0.0
    if (
        sampled >= settings.ORCHESTRATION_SCAN_ERROR_MIN_SAMPLES
        and scan_error_rate >= settings.ORCHESTRATION_SCAN_ERROR_RATE_ABORT
    ):
        logger.warning(
            "Degraded loop mode: scan error rate %.0f%% (%d/%d) >= %.0f%%. "
            "Skipping ranking/execution this iteration.",
            scan_error_rate * 100.0,
            len(scan_error_symbols),
            sampled,
            settings.ORCHESTRATION_SCAN_ERROR_RATE_ABORT * 100.0,
        )
        db.log_agent_event(
            "logging",
            "warn",
            "Degraded loop mode activated",
            {
                "trace_id": iter_trace_id,
                "loop": loop_count,
                "scan_error_rate": scan_error_rate,
                "scan_errors": len(scan_error_symbols),
                "sampled_symbols": sampled,
                "threshold": settings.ORCHESTRATION_SCAN_ERROR_RATE_ABORT,
                "action": "skip_rank_and_execute",
            },
        )
        metrics["last_rank_latency_ms"] = 0.0
        metrics["last_execution_latency_ms"] = 0.0
        metrics["last_signal_to_order_ms"] = -1.0
        return

    if skipped_cooldown:
        logger.debug("Cooldown active for: %s", ", ".join(skipped_cooldown))

    # ── MT5 connection-loss detection & auto-reconnect ────────────────────
    if ipc_fail_symbols and not scanned:
        # All attempted symbols failed IPC — emit ONE event (not one per symbol)
        db.log_agent_event(
            "market", "error",
            f"MT5 disconnected — {len(ipc_fail_symbols)} symbols unreachable. Attempting reconnect...",
            {"symbols": ipc_fail_symbols[:8]},
        )
        logger.warning("MT5 IPC loss on all %d symbols — attempting reconnect", len(ipc_fail_symbols))
        try:
            if broker.connect():
                db.log_agent_event("market", "info", "MT5 reconnected — resuming normal operation")
                logger.info("MT5 reconnected successfully")
                # Reset all per-symbol fail counts so they retry immediately
                for sym in ipc_fail_symbols:
                    symbol_fail_count[sym] = 0
                    symbol_disabled_until[sym] = 0.0
                    last_scan_ts.pop(sym, None)
                try:
                    for sym in ipc_fail_symbols:
                        db.save_symbol_fault(sym, 0, None)
                except Exception:
                    logger.debug("Could not clear symbol faults after MT5 reconnect")
            else:
                logger.warning("MT5 reconnect failed — will retry next iteration")
        except Exception as _re:
            logger.warning("MT5 reconnect error: %s", _re)
        return

    if not scanned:
        metrics["last_rank_latency_ms"] = 0.0
        metrics["last_execution_latency_ms"] = 0.0
        metrics["last_signal_to_order_ms"] = -1.0
        logger.debug("Loop %d: all symbols on cooldown or skipped", loop_count)
        return
    if not all_signals:
        if settings.DEFERRED_ENTRY_ENABLED and deferred_entries:
            now_wall = time.time()
            promoted: list[Signal] = []
            remaining: list[dict[str, object]] = []
            for item in deferred_entries:
                exp = _to_float(item.get("expires_at", 0.0), 0.0)
                sig = item.get("signal")
                if exp <= now_wall or not isinstance(sig, Signal):
                    continue
                remaining.append(item)
                promoted.append(sig)
                ctx = item.get("context")
                if isinstance(ctx, MarketContext):
                    signal_contexts[id(sig)] = ctx

            deferred_entries.clear()
            deferred_entries.extend(remaining)
            if promoted:
                all_signals.extend(promoted)
                metrics["deferred_promoted"] = metrics.get("deferred_promoted", 0) + len(promoted)

        if not all_signals:
            metrics["last_rank_latency_ms"] = 0.0
            metrics["last_execution_latency_ms"] = 0.0
            metrics["last_signal_to_order_ms"] = -1.0
            logger.info("Loop %d: scanned %s — no signals generated", loop_count, ", ".join(scanned))
            return

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 2: Rank by confidence (highest first) and deduplicate
    # ══════════════════════════════════════════════════════════════════════
    # ── Advance sniper watchlist ─────────────────────────────────────────
    # on_iteration() returns list of (verdict, candidate) for non-HOLD entries.
    # Candidates are still on the watchlist until we process them here.
    if sniper_guard is not None and sniper_guard.get_watchlist_size() > 0:
        _sym_ctx: dict[str, MarketContext] = {}
        for _ctx in signal_contexts.values():
            if _ctx is not None:
                _sym_ctx[_ctx.symbol] = _ctx
        _sniper_changes = sniper_guard.on_iteration(_sym_ctx)
        for _verdict, _candidate in _sniper_changes:
            logger.info(
                "SniperGuard watchlist: %s — %s %s (fib_depth=%s age=%.0fs)",
                _verdict.value, _candidate.symbol, _candidate.direction,
                _candidate.fib_depth,
                time.time() - _candidate.added_at,
            )
            if _verdict == SniperVerdict.SNIPER_CONFIRMED:
                # Add signal back to all_signals so it enters the ranked phase
                all_signals.append(_candidate.signal)
                _ctx = _sym_ctx.get(_candidate.symbol)
                if _ctx is not None:
                    signal_contexts[id(_candidate.signal)] = _ctx
                logger.info(
                    "SniperGuard SNIPER_CONFIRMED: %s %s re-added to signals "
                    "(fib_depth=%s) — will be ranked this iteration",
                    _candidate.symbol, _candidate.direction, _candidate.fib_depth,
                )
            # Remove processed (confirmed/expired/skipped) candidates from watchlist
            sniper_guard.remove(_candidate.symbol, _candidate.direction)
        # Prune expired from watchlist
        for _expired in sniper_guard.prune_expired():
            logger.info(
                "SniperGuard EXPIRED: %s %s",
                _expired.symbol, _expired.direction,
            )
        _wl_size = sniper_guard.get_watchlist_size()
        if _wl_size > 0:
            logger.debug("SniperGuard: %d candidates still on watchlist", _wl_size)

    rank_phase_start = time.monotonic()
    all_signals.sort(key=lambda s: s.confidence, reverse=True)

    # Keep only the best signal per (symbol, direction) — avoids ICT+SMA
    # both trying to open the same trade
    seen: set[tuple[str, str]] = set()
    ranked: list[Signal] = []
    for sig in all_signals:
        key = (sig.symbol, sig.direction)
        if key not in seen:
            seen.add(key)
            ranked.append(sig)

    if settings.DEFERRED_ENTRY_ENABLED and deferred_entries:
        now_wall = time.time()
        for item in deferred_entries[:]:
            exp = _to_float(item.get("expires_at", 0.0), 0.0)
            sig = item.get("signal")
            if exp <= now_wall or not isinstance(sig, Signal):
                deferred_entries.remove(item)
                continue
            key = (sig.symbol, sig.direction)
            if key in seen:
                continue
            seen.add(key)
            ranked.append(sig)
            ctx = item.get("context")
            if isinstance(ctx, MarketContext):
                signal_contexts[id(sig)] = ctx
            metrics["deferred_promoted"] = metrics.get("deferred_promoted", 0) + 1

    logger.info(
        "Signal scan: %d raw → %d ranked  [%s]",
        len(all_signals), len(ranked),
        ", ".join(f"{s.symbol} {s.direction} conf={s.confidence:.2f}" for s in ranked[:5]),
    )

    max_ranked = max(1, settings.ORCHESTRATION_MAX_SIGNALS_PER_ITERATION)
    if len(ranked) > max_ranked:
        logger.info(
            "Signal processing bounded: %d -> %d (top-confidence only)",
            len(ranked),
            max_ranked,
        )
        ranked = ranked[:max_ranked]

    ranked, lifecycle_rejects = opportunity_lifecycle.filter_ranked_signals(
        ranked,
        signal_contexts,
    )
    if lifecycle_rejects:
        logger.info(
            "Lifecycle gate rejected %d signal(s): %s",
            len(lifecycle_rejects),
            ", ".join(
                f"{sig.symbol} {sig.direction} ({reason})"
                for sig, reason in lifecycle_rejects[:6]
            ),
        )

    metrics["ranked_signals"] = metrics.get("ranked_signals", 0) + len(ranked)
    metrics["last_rank_latency_ms"] = (time.monotonic() - rank_phase_start) * 1000.0
    if hard_budget_enabled and metrics["last_rank_latency_ms"] > max_rank_ms:
        metrics["budget_rank_hits"] = metrics.get("budget_rank_hits", 0) + 1
        logger.warning(
            "Rank hard budget exceeded: %.1fms > %.1fms — execution phase will be tightly bounded",
            metrics["last_rank_latency_ms"],
            max_rank_ms,
        )
    signal_ready_ts = time.monotonic()
    first_fill_signal_to_order_ms = -1.0
    execution_phase_start = signal_ready_ts

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 3: Execute best signals that pass risk validation
    #
    # Sniper Entry Guard logic:
    #   conf >= SNIPER_CONF_THRESHOLD  → instant execute (no waiting)
    #   conf <  SNIPER_CONF_THRESHOLD  → wait on watchlist for Fibonacci pullback
    #     → price enters valid retracement zone → SNIPER_CONFIRMED → execute
    #     → timeout or price moved past zone → skip
    #
    # Fast lane always runs hard risk checks only (pre-entry speed path).
    # ══════════════════════════════════════════════════════════════════════
    for i, signal_obj in enumerate(ranked):
        exec_elapsed_ms = (time.monotonic() - execution_phase_start) * 1000.0
        iter_elapsed_ms = (time.monotonic() - iter_start_ts) * 1000.0
        if hard_budget_enabled and exec_elapsed_ms > max_exec_ms:
            metrics["budget_exec_hits"] = metrics.get("budget_exec_hits", 0) + 1
            logger.warning(
                "Execution hard budget exceeded: %.1fms > %.1fms — stopping further ranked processing",
                exec_elapsed_ms,
                max_exec_ms,
            )
            break
        if hard_budget_enabled and iter_elapsed_ms > max_iter_ms:
            metrics["budget_iteration_hits"] = metrics.get("budget_iteration_hits", 0) + 1
            logger.warning(
                "Iteration hard budget exceeded: %.1fms > %.1fms — stopping further ranked processing",
                iter_elapsed_ms,
                max_iter_ms,
            )
            break

        is_instant = (
            settings.INSTANT_ENTRY_ENABLED
            and i == 0
            and signal_obj.confidence >= settings.INSTANT_ENTRY_MIN_CONFIDENCE
        )
        is_fast_lane = settings.FAST_LANE_ENABLED and i < settings.FAST_LANE_MAX_SIGNALS

        # ── Sniper Entry Guard (Fibonacci pullback gate) ─────────────────
        # Replaces Council/DeepSeek with confidence-split Fibonacci logic:
        #   conf >= SNIPER_CONF_THRESHOLD  → instant execute (APPROVED)
        #   conf <  SNIPER_CONF_THRESHOLD  → hold on watchlist, wait for pullback
        #     SNIPER_CONFIRMED → price pulled into Fib zone → execute immediately
        #     EXPIRED / SKIPPED → price moved past zone or timeout → skip
        #     HOLD → signal is on watchlist; skip execution this iteration
        if sniper_guard is not None and not is_instant:
            ctx = signal_contexts.get(id(signal_obj))
            if ctx is not None:
                verdict = sniper_guard.review(signal_obj, ctx)
                if verdict.name in ("HOLD", "EXPIRED", "SKIPPED"):
                    # Signal is held on watchlist (HOLD) or rejected (EXPIRED/SKIPPED).
                    # Either way: skip this iteration entirely — do NOT fall through to
                    # risk validation or execution. The watchlist is advanced separately
                    # via on_iteration() in Phase 2 of the next loop.
                    logger.info(
                        "SniperGuard %s %s %s — skipping execution",
                        verdict.value.upper(), signal_obj.symbol, signal_obj.direction,
                    )
                    if _tui:
                        _tui.add_event(
                            "sniper", "warn" if verdict.name != "HOLD" else "info",
                            f"{verdict.value.upper()} {signal_obj.symbol} {signal_obj.direction}",
                        )
                    continue
                else:
                    # APPROVED or SNIPER_CONFIRMED — log and continue to risk check
                    logger.info(
                        "SniperGuard %s %s %s conf=%.2f",
                        verdict.value.upper(), signal_obj.symbol, signal_obj.direction,
                        signal_obj.confidence,
                    )
                    if _tui:
                        _tui.add_event(
                            "sniper", "info",
                            f"{verdict.value.upper()} {signal_obj.symbol} {signal_obj.direction}",
                        )

        # ── Risk check (drawdown, spread, lot-size, etc.) ────────────────
        if _tui:
            _tui.set_agent_status("risk", f"validating {signal_obj.symbol} {signal_obj.direction}")
        # Instant entry and fast-lane both run hard checks only pre-entry.
        validation_mode = "hard" if (is_instant or is_fast_lane) else "full"
        if is_fast_lane:
            metrics["fast_lane_attempts"] = metrics.get("fast_lane_attempts", 0) + 1
        if is_instant:
            metrics["instant_entry_attempts"] = metrics.get("instant_entry_attempts", 0) + 1

        if not risk_agent.validate(signal_obj, mode=validation_mode):
            metrics["risk_rejections"] = metrics.get("risk_rejections", 0) + 1
            reject_info = risk_agent.get_last_reject_info()
            reject_reason = str(reject_info.get("reason", "unknown"))
            reject_hard = bool(reject_info.get("hard", False))
            if not reject_hard:
                metrics["risk_soft_rejections"] = metrics.get("risk_soft_rejections", 0) + 1
            if risk_reject_reason_counts is not None:
                risk_reject_reason_counts[reject_reason] = (
                    risk_reject_reason_counts.get(reject_reason, 0) + 1
                )
            log_agent.log_risk_rejection(
                signal_obj.symbol, signal_obj.direction,
                signal_obj.strategy,
                f"Failed {validation_mode} risk validation ({reject_reason})",
            )
            if _tui:
                _tui.add_event("risk", "warn",
                               f"REJECT {signal_obj.symbol} {signal_obj.direction}")

            if (
                settings.DEFERRED_ENTRY_ENABLED
                and signal_obj.confidence >= settings.DEFERRED_ENTRY_MIN_CONF
                and not reject_hard
            ):
                ttl = max(30, int(settings.DEFERRED_ENTRY_TTL_SECONDS))
                expires_at = time.time() + ttl
                deferred_entries[:] = [
                    entry for entry in deferred_entries
                    if not (
                        isinstance(entry.get("signal"), Signal)
                        and cast(Signal, entry.get("signal")).symbol == signal_obj.symbol
                        and cast(Signal, entry.get("signal")).direction == signal_obj.direction
                    )
                ]
                deferred_entries.append(
                    {
                        "signal": signal_obj,
                        "context": signal_contexts.get(id(signal_obj)),
                        "expires_at": expires_at,
                    }
                )
                metrics["deferred_added"] = metrics.get("deferred_added", 0) + 1
            continue

        # ── Execute ──────────────────────────────────────────────────────
        if _tui:
            _tui.set_agent_status("execution", f"opening {signal_obj.direction} {signal_obj.symbol}")
        trade = execution_agent.open_trade(signal_obj)
        if trade is not None:
            trade_manager.add_trade(trade)
            opportunity_lifecycle.register_trade_open(signal_obj)
            log_agent.log_trade(trade.id, "OPENED",
                                f"{trade.direction} {trade.symbol} {trade.lot_size} lots")
            log_agent.log_trade_to_csv(trade)
            if _tui:
                _tui.set_trade(trade)
                _tui.add_event("execution", "info",
                               f"OPENED {trade.direction} {trade.symbol} @ {trade.entry_price:.5f}")

            if first_fill_signal_to_order_ms < 0.0:
                first_fill_signal_to_order_ms = (time.monotonic() - signal_ready_ts) * 1000.0

            # ── Post-entry council (DISABLED — ICT-only mode) ───────────────
            # if is_instant and council is not None:
            #     ... (formerly council advisory thread)

            # ── Post-entry full risk check ───────────────────────────────
            if is_instant or is_fast_lane:
                metrics["fast_lane_fills"] = metrics.get("fast_lane_fills", 0) + 1
                full_ok = risk_agent.validate(signal_obj, mode="full", post_entry=True)
                if not full_ok and settings.FAST_LANE_CLOSE_ON_FULL_REJECT:
                    trade_manager.close_trade(trade.id, "FULL_VALIDATION_REJECT")
                    metrics["fast_lane_closed"] = metrics.get("fast_lane_closed", 0) + 1
            else:
                metrics["full_lane_fills"] = metrics.get("full_lane_fills", 0) + 1

    metrics["last_execution_latency_ms"] = (time.monotonic() - execution_phase_start) * 1000.0
    metrics["last_signal_to_order_ms"] = first_fill_signal_to_order_ms

    logger.debug(
        "Loop %d timing | session=%s cooldown=%.0fs scan=%.1fms rank=%.1fms exec=%.1fms signal_to_order=%.1fms total=%.1fms",
        loop_count,
        session_profile,
        scan_cooldown,
        metrics["last_scan_latency_ms"],
        metrics["last_rank_latency_ms"],
        metrics["last_execution_latency_ms"],
        metrics["last_signal_to_order_ms"],
        (time.monotonic() - iter_start_ts) * 1000.0,
    )

    if settings.ORCHESTRATION_ENABLE_ITERATION_TRACE:
        db.log_agent_event(
            "logging",
            "debug",
            "Iteration completed",
            {
                "trace_id": iter_trace_id,
                "loop": loop_count,
                "scanned": len(scanned),
                "scan_errors": len(scan_error_symbols),
                "ranked_processed": len(ranked),
                "scan_latency_ms": metrics["last_scan_latency_ms"],
                "rank_latency_ms": metrics["last_rank_latency_ms"],
                "exec_latency_ms": metrics["last_execution_latency_ms"],
                "signal_to_order_ms": metrics["last_signal_to_order_ms"],
            },
        )

    if _tui:
        for name in ("market", "analysis", "strategy", "risk", "execution", "trade_mgr"):
            _tui.set_agent_idle(name)
