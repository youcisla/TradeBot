"""Iteration phases — scan, rank, execute.

Separated from run_iteration for single-responsibility, testability,
and independent tuning of each pipeline stage.
"""

from __future__ import annotations

import concurrent.futures
import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, cast

from config import settings
from config.settings import PERMANENT_FAULT_SYMBOLS
from filters.data_validator import DataValidationError
from models.market_data import MarketContext
from models.signal import Signal
from utils import terminal_ui as tui
from utils.helpers import is_market_open

from agents.hku_signal_adapter import adapt_hku_signal
from agents.sniper_entry_guard import SniperEntryGuard, SniperVerdict

if TYPE_CHECKING:
    from agents.analysis_agent import AnalysisAgent
    from agents.execution_agent import ExecutionAgent
    from agents.hku_client import HKUClient
    from agents.learning_agent import LearningAgent
    from agents.logging_agent import LoggingAgent
    from agents.market_agent import MarketAgent
    from agents.risk_agent import RiskAgent
    from agents.strategy_agent import StrategyAgent
    from agents.trade_manager import TradeManagerAgent
    from broker.connector import BrokerConnector
    from database.db import Database
    from utils.opportunity_lifecycle import OpportunityLifecycleManager
    from utils.symbol_event_tracker import SymbolEventTracker

logger = logging.getLogger(__name__)


# ── Shared phase result types ──────────────────────────────────────────────────

@dataclass
class ScanResult:
    """Output of ScanPhase."""

    scanned: list[str] = field(default_factory=list)
    """Symbols that were successfully scanned."""

    skipped_cooldown: list[str] = field(default_factory=list)
    """Symbols skipped due to cooldown."""

    scan_error_symbols: list[str] = field(default_factory=list)
    """Symbols that returned errors."""

    ipc_fail_symbols: list[str] = field(default_factory=list)
    """Symbols that failed with IPC errors (MT5 connection)."""

    all_signals: list[Signal] = field(default_factory=list)
    """All signals collected from successful scans."""

    signal_contexts: dict[int, MarketContext] = field(default_factory=dict)
    """Maps id(signal) → MarketContext for sniper guard and execution."""

    latency_ms: float = 0.0
    """Time spent in scan phase."""

    abort_reason: str | None = None
    """If set, ranking/execution should be skipped this iteration."""


@dataclass
class RankResult:
    """Output of RankPhase."""

    ranked: list[Signal] = field(default_factory=list)
    """Ranked, deduplicated signals ready for execution."""

    lifecycle_rejects: list[tuple[Signal, str]] = field(default_factory=list)
    """Signals rejected by opportunity lifecycle gate."""

    signal_contexts: dict[int, MarketContext] = field(default_factory=dict)
    """Updated signal contexts including deferred promotions."""

    latency_ms: float = 0.0
    """Time spent in rank phase."""


@dataclass
class ExecutionResult:
    """Output of ExecutePhase."""

    fills: int = 0
    """Number of trades successfully opened."""

    fast_lane_fills: int = 0
    """Fills from fast lane."""

    fast_lane_closed: int = 0
    """Trades closed due to full validation reject after fast lane."""

    full_lane_fills: int = 0
    """Fills from full lane."""

    deferred_added: int = 0
    """Signals promoted to deferred entry."""

    risk_rejections: int = 0
    """Total risk rejections this phase."""

    risk_soft_rejections: int = 0
    """Soft risk rejections (deferrable)."""

    first_signal_to_order_ms: float = -1.0
    """Wall clock ms from signal ranking to first order fill, -1 if no fill."""

    latency_ms: float = 0.0
    """Time spent in execution phase."""


# ── Phase helpers ─────────────────────────────────────────────────────────────

def _to_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


# ── ScanPhase ─────────────────────────────────────────────────────────────────

class ScanPhase:
    """Phase 1: Scan all symbols and collect every signal.

    Handles:
    - Symbol cooldown logic (including BTC priority)
    - MT5 IPC failure tracking and reconnection
    - Per-symbol: market data → analysis → strategy → signals
    - Graceful degradation when scan error rate is too high
    """

    def __init__(
        self,
        broker: BrokerConnector,
        market_agent: MarketAgent,
        analysis_agent: AnalysisAgent,
        strategy_agent: StrategyAgent,
        db: Database,
        symbol_event_tracker: SymbolEventTracker,
        hku_client: "HKUClient | None" = None,
    ) -> None:
        self._broker = broker
        self._market_agent = market_agent
        self._analysis_agent = analysis_agent
        self._strategy_agent = strategy_agent
        self._db = db
        self._symbol_event_tracker = symbol_event_tracker
        self._hku_client = hku_client

    def run(
        self,
        *,
        active_symbols: list[str],
        open_symbols: set[str],
        last_scan_ts: dict[str, float],
        symbol_fail_count: dict[str, int],
        symbol_disabled_until: dict[str, float],
        symbol_max_fails: int,
        symbol_disable_secs: float,
        scan_cooldown: float,
        session_profile: str,
        weekend_symbols: list[str] | None,
        scan_workers: int,
        metrics: dict[str, float],
        loop_count: int,
    ) -> ScanResult:
        result = ScanResult()
        now_mono = time.monotonic()
        scan_phase_start = now_mono
        btc_symbol = settings.BTC_PRIORITY_SYMBOL

        # Priority scan order: BTC first, then everything else
        scan_symbols = active_symbols[:]
        if btc_symbol in scan_symbols:
            scan_symbols = [btc_symbol] + [s for s in scan_symbols if s != btc_symbol]

        # BTC always scans regardless of cooldown
        # Non-BTC symbols skip if cooldown hasn't expired
        def process_symbol(symbol: str) -> tuple[
            str, str, bool,
            MarketContext | None, list[Signal] | None,
            str | None, bool
        ]:
            """Returns (symbol, status, is_re_enabled, context, signals, err_str, is_ipc)."""
            if symbol in PERMANENT_FAULT_SYMBOLS:
                return (symbol, "skip", False, None, None, None, False)
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
                is_re_enabled = True

            # Non-BTC cooldown check
            symbol_cooldown = scan_cooldown
            if symbol == btc_symbol:
                symbol_cooldown = max(0, settings.BTC_PRIORITY_SCAN_COOLDOWN_SECONDS)

            if symbol != btc_symbol:
                if now_mono - last_scan_ts.get(symbol, 0.0) < symbol_cooldown:
                    if settings.EVENT_DRIVEN_RESCAN_ON_NEW_CANDLE:
                        last_candle_ts = self._symbol_event_tracker.get(symbol, "last_candle")
                        if last_candle_ts > 0 and (time.time() - last_candle_ts) < symbol_cooldown:
                            last_scan_ts[symbol] = now_mono
                            return (symbol, "cooldown", is_re_enabled, None, None, None, False)
                    else:
                        last_scan_ts[symbol] = now_mono
                        return (symbol, "cooldown", is_re_enabled, None, None, None, False)

            _ui = tui.get_ui()
            try:
                if _ui:
                    _ui.set_agent_status("market", f"fetching {symbol}")
                data = self._market_agent.get_data(symbol)
            except DataValidationError as e:
                err_str = str(e)
                is_ipc = (
                    "IPC" in err_str or "No tick data" in err_str
                    or "-10004" in err_str or "Terminal: Call failed" in err_str
                )
                return (symbol, "error", is_re_enabled, None, None, err_str, is_ipc)

            try:
                if _ui:
                    _ui.set_agent_status("analysis", f"analyzing {symbol}")
                context = self._analysis_agent.analyze(data)

                if _ui:
                    _ui.set_agent_status("strategy", f"scanning {symbol}")
                signals = self._strategy_agent.detect_all(context)

                return (symbol, "success", is_re_enabled, context, signals, None, False)
            except Exception as e:
                return (symbol, "error", False, None, None, str(e), False)

        # Run scans: MT5 sequential (IPC-sensitive), others parallel
        is_mt5 = self._broker.__class__.__name__ == "MT5Connector"
        scan_results: list[tuple[str, str, bool, MarketContext | None, list[Signal] | None, str | None, bool]] = []

        if is_mt5:
            for sym in scan_symbols:
                scan_results.append(process_symbol(sym))
        else:
            worker_count = max(1, min(scan_workers, len(scan_symbols)))
            with concurrent.futures.ThreadPoolExecutor(max_workers=worker_count) as executor:
                futures = {executor.submit(process_symbol, sym): sym for sym in scan_symbols}
                for future in concurrent.futures.as_completed(futures):
                    scan_results.append(future.result())

        # Process results
        for res in scan_results:
            sym, status, is_re_enabled, context, signals, err_str, is_ipc = res

            if status == "skip":
                continue

            if is_re_enabled:
                logger.info("Re-enabling %s after IPC cooldown (was disabled for 1h)", sym)
                symbol_fail_count[sym] = 0
                symbol_disabled_until[sym] = 0.0
                try:
                    self._db.save_symbol_fault(sym, 0, None)
                except Exception:
                    logger.debug("Could not clear symbol fault for %s", sym)

            if status == "cooldown":
                result.skipped_cooldown.append(sym)
                continue

            if status == "error":
                result.scan_error_symbols.append(sym)
                is_stuck_quote = bool(err_str) and "Stuck quote" in err_str

                if is_ipc or is_stuck_quote:
                    if is_ipc:
                        result.ipc_fail_symbols.append(sym)
                    count = symbol_fail_count.get(sym, 0) + 1
                    symbol_fail_count[sym] = count
                    if count >= symbol_max_fails:
                        symbol_disabled_until[sym] = now_mono + symbol_disable_secs
                        logger.warning(
                            "Auto-disabling %s for 1h after %d consecutive %s failures",
                            sym, count, "IPC" if is_ipc else "stuck-quote",
                        )
                        try:
                            from datetime import timedelta, datetime as dt, timezone as tz
                            self._db.save_symbol_fault(
                                sym, count,
                                dt.now(tz.utc) + timedelta(seconds=symbol_disable_secs),
                            )
                        except Exception:
                            logger.debug("Could not persist symbol fault for %s", sym)
                else:
                    symbol_fail_count[sym] = 0
                continue

            # Successful scan
            last_scan_ts[sym] = now_mono
            symbol_fail_count[sym] = 0
            if context and context.candles:
                self._symbol_event_tracker.update(
                    sym, "last_candle",
                    context.candles[-1].timestamp.timestamp(),
                )
            result.scanned.append(sym)

            if signals:
                self._symbol_event_tracker.update(sym, "last_signal", time.time())
                if context is not None:
                    for sig in signals:
                        result.signal_contexts[id(sig)] = context
                result.all_signals.extend(signals)

        result.latency_ms = (time.monotonic() - scan_phase_start) * 1000.0

        # Graceful degradation: abort if too many scan errors
        sampled = len(result.scanned) + len(result.scan_error_symbols)
        scan_error_rate = len(result.scan_error_symbols) / sampled if sampled > 0 else 0.0

        if (
            sampled >= settings.ORCHESTRATION_SCAN_ERROR_MIN_SAMPLES
            and scan_error_rate >= settings.ORCHESTRATION_SCAN_ERROR_RATE_ABORT
        ):
            result.abort_reason = (
                f"Scan error rate {scan_error_rate:.0%} ({len(result.scan_error_symbols)}/{sampled}) "
                f">= threshold {settings.ORCHESTRATION_SCAN_ERROR_RATE_ABORT:.0%}"
            )
            logger.warning("ScanPhase: %s", result.abort_reason)

        # MT5 connection-loss: all symbols had IPC errors
        if result.ipc_fail_symbols and not result.scanned:
            self._handle_mt5_disconnect(result.ipc_fail_symbols, symbol_fail_count,
                                         symbol_disabled_until, last_scan_ts)

        if result.skipped_cooldown:
            logger.debug("ScanPhase cooldown active for: %s",
                         ", ".join(result.skipped_cooldown))

        # Fetch and normalize external HKU signals after internal scan completes
        self._fetch_hku_signals(result)

        return result

    def _fetch_hku_signals(self, result: ScanResult) -> None:
        """Fetch external HKU marketplace signals and inject into the scan result.

        HKU signals are normalized with a confidence discount so they never
        reach full confidence until our own LGBM pipeline validates them.
        They bypass opportunity lifecycle (no market context at fetch time).
        Fails open — any error logs a warning and leaves result unchanged.
        """
        if not self._hku_client:
            return

        try:
            raw_signals = self._hku_client.get_external_signals(
                limit=settings.HKU_FEED_LIMIT,
            )
            if not raw_signals:
                return

            for payload in raw_signals:
                sig = adapt_hku_signal(payload, discount_factor=settings.HKU_SIGNAL_DISCOUNT)
                result.all_signals.append(sig)
                # HKU signals have no market context — lifecycle gate will skip them
                result.signal_contexts[id(sig)] = None
                hku_id = sig.metadata.get("hku_signal_id", "")
                try:
                    self._db.signal_repo.save_hku_signal(
                        sig,
                        hku_signal_id=hku_id,
                        author=f"hku:{sig.metadata.get('hku_agent_id', 'unknown')}",
                    )
                except Exception as exc:
                    logger.debug("Failed to persist HKU signal %s: %s", hku_id, exc)

            logger.debug("ScanPhase: injected %d HKU signals", len(raw_signals))
        except Exception as exc:
            logger.warning("HKU signal fetch failed (failing open): %s", exc)

    def _handle_mt5_disconnect(
        self,
        ipc_fail_symbols: list[str],
        symbol_fail_count: dict[str, int],
        symbol_disabled_until: dict[str, float],
        last_scan_ts: dict[str, float],
    ) -> None:
        """Handle MT5 disconnection: attempt reconnect and reset fail counts."""
        self._db.log_agent_event(
            "market", "error",
            f"MT5 disconnected — {len(ipc_fail_symbols)} symbols unreachable. Attempting reconnect...",
            {"symbols": ipc_fail_symbols[:8]},
        )
        logger.warning("MT5 IPC loss on all %d symbols — attempting reconnect",
                       len(ipc_fail_symbols))
        try:
            if self._broker.connect():
                self._db.log_agent_event("market", "info",
                                          "MT5 reconnected — resuming normal operation")
                logger.info("MT5 reconnected successfully")
                for sym in ipc_fail_symbols:
                    symbol_fail_count[sym] = 0
                    symbol_disabled_until[sym] = 0.0
                    last_scan_ts.pop(sym, None)
                try:
                    for sym in ipc_fail_symbols:
                        self._db.save_symbol_fault(sym, 0, None)
                except Exception:
                    logger.debug("Could not clear symbol faults after MT5 reconnect")
            else:
                logger.warning("MT5 reconnect failed — will retry next iteration")
        except Exception as exc:
            logger.warning("MT5 reconnect error: %s", exc)


# ── RankPhase ─────────────────────────────────────────────────────────────────

class RankPhase:
    """Phase 2: Rank signals by confidence and deduplicate.

    Handles:
    - Confidence sorting (highest first)
    - Best-signal-per-(symbol, direction) deduplication
    - Deferred entry promotion
    - Sniper guard watchlist advancement
    - Opportunity lifecycle filtering
    """

    def __init__(
        self,
        sniper_guard: SniperEntryGuard | None,
        opportunity_lifecycle: OpportunityLifecycleManager,
    ) -> None:
        self._sniper_guard = sniper_guard
        self._lifecycle = opportunity_lifecycle

    def run(
        self,
        *,
        all_signals: list[Signal],
        signal_contexts: dict[int, MarketContext],
        deferred_entries: list[dict[str, object]],
        metrics: dict[str, float],
        hard_budget_enabled: bool,
        max_rank_ms: float,
        weekend_symbols: list[str] | None,
    ) -> RankResult:
        result = RankResult()
        rank_phase_start = time.monotonic()

        # Advance sniper watchlist first
        if self._sniper_guard is not None and self._sniper_guard.get_watchlist_size() > 0:
            self._advance_sniper_watchlist(signal_contexts)

        # Sort by confidence descending
        all_signals.sort(key=lambda s: s.confidence, reverse=True)

        # Deduplicate: keep best per (symbol, direction)
        seen: set[tuple[str, str]] = set()
        ranked: list[Signal] = []
        for sig in all_signals:
            key = (sig.symbol, sig.direction)
            if key not in seen:
                seen.add(key)
                ranked.append(sig)

        # Promote deferred entries
        promoted_signals = self._promote_deferred(deferred_entries, signal_contexts, seen)
        ranked.extend(promoted_signals)
        metrics["deferred_promoted"] = (
            metrics.get("deferred_promoted", 0) + len(promoted_signals)
        )

        # Bound ranked signals
        max_ranked = max(1, settings.ORCHESTRATION_MAX_SIGNALS_PER_ITERATION)
        if len(ranked) > max_ranked:
            logger.info("RankPhase: bounding %d → %d (top-confidence only)",
                         len(ranked), max_ranked)
            ranked = ranked[:max_ranked]

        # Lifecycle gate — HKU signals bypass (no market context at fetch time)
        ranked_internal = []
        ranked_hku = []
        for sig in ranked:
            if sig.source == "hku":
                ranked_hku.append(sig)
            else:
                ranked_internal.append(sig)

        ranked_internal, lifecycle_rejects = self._lifecycle.filter_ranked_signals(
            ranked_internal, signal_contexts,
        )
        result.lifecycle_rejects = lifecycle_rejects
        if lifecycle_rejects:
            logger.info("RankPhase: lifecycle gate rejected %d signal(s)",
                         len(lifecycle_rejects))

        # HKU signals always pass lifecycle gate; merged back after filtering
        result.ranked = ranked_internal + ranked_hku
        result.signal_contexts = signal_contexts
        result.latency_ms = (time.monotonic() - rank_phase_start) * 1000.0

        if hard_budget_enabled and result.latency_ms > max_rank_ms:
            metrics["budget_rank_hits"] = metrics.get("budget_rank_hits", 0) + 1
            logger.warning(
                "RankPhase: hard budget exceeded: %.1fms > %.1fms",
                result.latency_ms, max_rank_ms,
            )

        metrics["ranked_signals"] = metrics.get("ranked_signals", 0) + len(ranked)
        logger.info(
            "RankPhase: %d raw → %d ranked  [%s]",
            len(all_signals), len(ranked),
            ", ".join(f"{s.symbol} {s.direction} conf={s.confidence:.2f}"
                      for s in ranked[:5]),
        )
        return result

    def _advance_sniper_watchlist(
        self, signal_contexts: dict[int, MarketContext]
    ) -> None:
        """Advance sniper watchlist and re-add confirmed signals to all_signals."""
        if self._sniper_guard is None:
            return
        sym_ctx: dict[str, MarketContext] = {}
        for ctx in signal_contexts.values():
            if ctx is not None:
                sym_ctx[ctx.symbol] = ctx
        changes = self._sniper_guard.on_iteration(sym_ctx)
        for verdict, candidate in changes:
            logger.info(
                "SniperGuard watchlist: %s — %s %s (fib_depth=%s age=%.0fs)",
                verdict.value, candidate.symbol, candidate.direction,
                candidate.fib_depth,
                time.time() - candidate.added_at,
            )
            if verdict == SniperVerdict.SNIPER_CONFIRMED:
                logger.info(
                    "SniperGuard SNIPER_CONFIRMED: %s %s re-added to signals",
                    candidate.symbol, candidate.direction,
                )
            self._sniper_guard.remove(candidate.symbol, candidate.direction)
        for expired in self._sniper_guard.prune_expired():
            logger.info("SniperGuard EXPIRED: %s %s", expired.symbol, expired.direction)
        wl_size = self._sniper_guard.get_watchlist_size()
        if wl_size > 0:
            logger.debug("SniperGuard: %d candidates still on watchlist", wl_size)

    def _promote_deferred(
        self,
        deferred_entries: list[dict[str, object]],
        signal_contexts: dict[int, MarketContext],
        seen: set[tuple[str, str]],
    ) -> list[Signal]:
        """Promote deferred signals that have not expired and are not duplicates."""
        promoted: list[Signal] = []
        now_wall = time.time()
        remaining: list[dict[str, object]] = []
        for item in deferred_entries:
            exp = _to_float(item.get("expires_at", 0.0), 0.0)
            sig = item.get("signal")
            if exp <= now_wall or not isinstance(sig, Signal):
                continue
            remaining.append(item)
            key = (sig.symbol, sig.direction)
            if key in seen:
                continue
            promoted.append(sig)
            ctx = item.get("context")
            if isinstance(ctx, MarketContext):
                signal_contexts[id(sig)] = ctx
        deferred_entries.clear()
        deferred_entries.extend(remaining)
        return promoted


# ── ExecutePhase ───────────────────────────────────────────────────────────────

class ExecutePhase:
    """Phase 3: Execute ranked signals that pass risk validation.

    Handles:
    - Hard budget enforcement (time limits per phase)
    - Sniper entry guard review
    - Risk validation (hard vs soft mode)
    - Trade execution via execution_agent
    - Deferred entry creation for soft rejections
    - Post-entry full risk check for fast-lane trades
    """

    def __init__(
        self,
        risk_agent: RiskAgent,
        execution_agent: ExecutionAgent,
        trade_manager: TradeManagerAgent,
        log_agent: LoggingAgent,
        sniper_guard: SniperEntryGuard | None,
    ) -> None:
        self._risk_agent = risk_agent
        self._execution_agent = execution_agent
        self._trade_manager = trade_manager
        self._log_agent = log_agent
        self._sniper_guard = sniper_guard

    def run(
        self,
        *,
        ranked: list[Signal],
        signal_contexts: dict[int, MarketContext],
        deferred_entries: list[dict[str, object]],
        metrics: dict[str, float],
        risk_reject_reason_counts: dict[str, int] | None,
        hard_budget_enabled: bool,
        max_exec_ms: float,
        max_iter_ms: float,
        execution_phase_start: float,
        iter_start_ts: float,
    ) -> ExecutionResult:
        result = ExecutionResult()
        first_fill_ms = -1.0

        for i, sig in enumerate(ranked):
            exec_elapsed_ms = (time.monotonic() - execution_phase_start) * 1000.0
            iter_elapsed_ms = (time.monotonic() - iter_start_ts) * 1000.0

            # Hard budget checks
            if hard_budget_enabled and exec_elapsed_ms > max_exec_ms:
                metrics["budget_exec_hits"] = metrics.get("budget_exec_hits", 0) + 1
                logger.warning(
                    "ExecutePhase: hard budget exceeded: %.1fms > %.1fms",
                    exec_elapsed_ms, max_exec_ms,
                )
                break
            if hard_budget_enabled and iter_elapsed_ms > max_iter_ms:
                metrics["budget_iteration_hits"] = metrics.get("budget_iteration_hits", 0) + 1
                logger.warning(
                    "ExecutePhase: iteration budget exceeded: %.1fms > %.1fms",
                    iter_elapsed_ms, max_iter_ms,
                )
                break

            # Determine execution mode
            is_instant = (
                settings.INSTANT_ENTRY_ENABLED
                and i == 0
                and sig.confidence >= settings.INSTANT_ENTRY_MIN_CONFIDENCE
            )
            is_fast_lane = (
                settings.FAST_LANE_ENABLED
                and i < settings.FAST_LANE_MAX_SIGNALS
            )

            if is_fast_lane:
                metrics["fast_lane_attempts"] = metrics.get("fast_lane_attempts", 0) + 1
            if is_instant:
                metrics["instant_entry_attempts"] = metrics.get("instant_entry_attempts", 0) + 1

            # ── Sniper Entry Guard ────────────────────────────────────────────
            if self._sniper_guard is not None and not is_instant:
                ctx = signal_contexts.get(id(sig))
                if ctx is not None:
                    verdict = self._sniper_guard.review(sig, ctx)
                    if verdict.name in ("HOLD", "EXPIRED", "SKIPPED"):
                        logger.info(
                            "ExecutePhase SniperGuard %s %s %s — skipping",
                            verdict.value.upper(), sig.symbol, sig.direction,
                        )
                        _ui = tui.get_ui()
                        if _ui:
                            _ui.add_event(
                                "sniper",
                                "warn" if verdict.name != "HOLD" else "info",
                                f"{verdict.value.upper()} {sig.symbol} {sig.direction}",
                            )
                        continue
                    else:
                        logger.info(
                            "ExecutePhase SniperGuard %s %s %s conf=%.2f",
                            verdict.value.upper(), sig.symbol, sig.direction, sig.confidence,
                        )
                        _ui = tui.get_ui()
                        if _ui:
                            _ui.add_event(
                                "sniper", "info",
                                f"{verdict.value.upper()} {sig.symbol} {sig.direction}",
                            )

            # ── Risk validation ───────────────────────────────────────────────
            validation_mode = "hard" if (is_instant or is_fast_lane) else "full"
            _ui = tui.get_ui()
            if _ui:
                _ui.set_agent_status("risk", f"validating {sig.symbol} {sig.direction}")

            if not self._risk_agent.validate(sig, mode=validation_mode):
                metrics["risk_rejections"] = metrics.get("risk_rejections", 0) + 1
                reject_info = self._risk_agent.get_last_reject_info()
                reject_reason = str(reject_info.get("reason", "unknown"))
                reject_hard = bool(reject_info.get("hard", False))
                if not reject_hard:
                    metrics["risk_soft_rejections"] = (
                        metrics.get("risk_soft_rejections", 0) + 1
                    )
                if risk_reject_reason_counts is not None:
                    risk_reject_reason_counts[reject_reason] = (
                        risk_reject_reason_counts.get(reject_reason, 0) + 1
                    )
                self._log_agent.log_risk_rejection(
                    sig.symbol, sig.direction, sig.strategy,
                    f"Failed {validation_mode} risk validation ({reject_reason})",
                )
                if _ui:
                    _ui.add_event("risk", "warn",
                                   f"REJECT {sig.symbol} {sig.direction}")

                # Deferred entry for soft rejections
                if (
                    settings.DEFERRED_ENTRY_ENABLED
                    and sig.confidence >= settings.DEFERRED_ENTRY_MIN_CONF
                    and not reject_hard
                ):
                    ttl = max(30, int(settings.DEFERRED_ENTRY_TTL_SECONDS))
                    expires_at = time.time() + ttl
                    # Remove stale entries for same symbol/direction
                    deferred_entries[:] = [
                        e for e in deferred_entries
                        if not (
                            isinstance(e.get("signal"), Signal)
                            and cast(Signal, e.get("signal")).symbol == sig.symbol
                            and cast(Signal, e.get("signal")).direction == sig.direction
                        )
                    ]
                    deferred_entries.append({
                        "signal": sig,
                        "context": signal_contexts.get(id(sig)),
                        "expires_at": expires_at,
                    })
                    metrics["deferred_added"] = metrics.get("deferred_added", 0) + 1
                continue

            # ── Execute ──────────────────────────────────────────────────────
            if _ui:
                _ui.set_agent_status("execution",
                                       f"opening {sig.direction} {sig.symbol}")
            trade = self._execution_agent.open_trade(sig)
            if trade is None:
                continue

            self._trade_manager.add_trade(trade)
            result.fills += 1

            if _ui:
                _ui.set_trade(trade)
                _ui.add_event(
                    "execution", "info",
                    f"OPENED {trade.direction} {trade.symbol} @ {trade.entry_price:.5f}",
                )

            if first_fill_ms < 0.0:
                first_fill_ms = (time.monotonic() - execution_phase_start) * 1000.0

            # Post-entry full risk check for fast lane
            if is_instant or is_fast_lane:
                metrics["fast_lane_fills"] = metrics.get("fast_lane_fills", 0) + 1
                full_ok = self._risk_agent.validate(sig, mode="full", post_entry=True)
                if not full_ok and settings.FAST_LANE_CLOSE_ON_FULL_REJECT:
                    self._trade_manager.close_trade(trade.id, "FULL_VALIDATION_REJECT")
                    metrics["fast_lane_closed"] = metrics.get("fast_lane_closed", 0) + 1
            else:
                metrics["full_lane_fills"] = metrics.get("full_lane_fills", 0) + 1

        result.first_signal_to_order_ms = first_fill_ms
        result.latency_ms = (time.monotonic() - execution_phase_start) * 1000.0
        return result
