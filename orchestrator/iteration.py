"""run_iteration — thin coordinator using ScanPhase, RankPhase, ExecutePhase.

All pipeline logic moved to orchestrator/iteration_phases.py.
This file only wires inputs/outputs and handles cross-cutting concerns
(monitor open trades, post-execution logging, UI updates).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from config import settings
from database.db import Database
from models.market_data import MarketContext
from models.signal import Signal
from agents.analysis_agent import AnalysisAgent
from agents.crucix_agent import CrucixAgent
from agents.execution_agent import ExecutionAgent
from agents.learning_agent import LearningAgent
from agents.logging_agent import LoggingAgent
from agents.market_agent import MarketAgent
from agents.risk_agent import RiskAgent
from agents.sniper_entry_guard import SniperEntryGuard
from agents.strategy_agent import StrategyAgent
from agents.trade_manager import TradeManagerAgent

if TYPE_CHECKING:
    from agents.hku_client import HKUClient
    from agents.ssrt_agent import SSRTAgent
from broker.connector import BrokerConnector
from utils import telegram_bot
from utils import terminal_ui as tui
from utils.opportunity_lifecycle import OpportunityLifecycleManager
from utils.symbol_event_tracker import SymbolEventTracker

from .iteration_phases import ScanPhase, RankPhase, ExecutePhase, ScanResult

logger = logging.getLogger(__name__)


@dataclass
class MetricsDelta:
    """Values written to the cumulative metrics dict by a single run_iteration call.

    Using a dataclass instead of a bare dict makes the contract explicit —
    callers know exactly which keys may be written without cross-file inspection.
    """
    loops: int = 0
    scanned_symbols: int = 0
    raw_signals: int = 0
    ranked_signals: int = 0
    council_rejections: int = 0
    risk_rejections: int = 0
    risk_soft_rejections: int = 0
    fast_lane_attempts: int = 0
    fast_lane_fills: int = 0
    fast_lane_closed: int = 0
    full_lane_fills: int = 0
    deferred_added: int = 0
    deferred_promoted: int = 0
    budget_scan_hits: int = 0
    budget_rank_hits: int = 0
    budget_exec_hits: int = 0
    budget_iteration_hits: int = 0
    budget_council_skips: int = 0
    last_scan_latency_ms: float = 0.0
    last_rank_latency_ms: float = 0.0
    last_execution_latency_ms: float = 0.0
    last_signal_to_order_ms: float = -1.0

    def merge_into(self, cumulative: dict[str, float]) -> None:
        """Add all deltas into a cumulative metrics dict (mutates cumulative)."""
        cumulative["loops"] = cumulative.get("loops", 0) + self.loops
        cumulative["scanned_symbols"] = cumulative.get("scanned_symbols", 0) + self.scanned_symbols
        cumulative["raw_signals"] = cumulative.get("raw_signals", 0) + self.raw_signals
        cumulative["ranked_signals"] = cumulative.get("ranked_signals", 0) + self.ranked_signals
        cumulative["council_rejections"] = cumulative.get("council_rejections", 0) + self.council_rejections
        cumulative["risk_rejections"] = cumulative.get("risk_rejections", 0) + self.risk_rejections
        cumulative["risk_soft_rejections"] = cumulative.get("risk_soft_rejections", 0) + self.risk_soft_rejections
        cumulative["fast_lane_attempts"] = cumulative.get("fast_lane_attempts", 0) + self.fast_lane_attempts
        cumulative["fast_lane_fills"] = cumulative.get("fast_lane_fills", 0) + self.fast_lane_fills
        cumulative["fast_lane_closed"] = cumulative.get("fast_lane_closed", 0) + self.fast_lane_closed
        cumulative["full_lane_fills"] = cumulative.get("full_lane_fills", 0) + self.full_lane_fills
        cumulative["deferred_added"] = cumulative.get("deferred_added", 0) + self.deferred_added
        cumulative["deferred_promoted"] = cumulative.get("deferred_promoted", 0) + self.deferred_promoted
        cumulative["budget_scan_hits"] = cumulative.get("budget_scan_hits", 0) + self.budget_scan_hits
        cumulative["budget_rank_hits"] = cumulative.get("budget_rank_hits", 0) + self.budget_rank_hits
        cumulative["budget_exec_hits"] = cumulative.get("budget_exec_hits", 0) + self.budget_exec_hits
        cumulative["budget_iteration_hits"] = cumulative.get("budget_iteration_hits", 0) + self.budget_iteration_hits
        cumulative["budget_council_skips"] = cumulative.get("budget_council_skips", 0) + self.budget_council_skips
        # Overwrite (not accumulate) per-iteration latency values
        cumulative["last_scan_latency_ms"] = self.last_scan_latency_ms
        cumulative["last_rank_latency_ms"] = self.last_rank_latency_ms
        cumulative["last_execution_latency_ms"] = self.last_execution_latency_ms
        cumulative["last_signal_to_order_ms"] = self.last_signal_to_order_ms


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
    ssrt_agent: "SSRTAgent | None",
    sniper_guard: SniperEntryGuard | None,
    symbol_event_tracker: SymbolEventTracker,
    hku_client: "HKUClient | None" = None,
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
) -> MetricsDelta:
    """Single iteration of the trading loop.

    Uses a **scan-all → rank → execute-best** pipeline:
    1. Scan every symbol and collect ALL signals from ALL strategies
    2. Rank by confidence (highest first)
    3. Execute top signals that pass risk validation (up to available slots)

    This ensures we never miss a high-confidence setup just because another
    symbol happened to be checked first in the list.

    Phase implementation lives in orchestrator/iteration_phases.py.
    """
    # Deferred SSRT processing — queue closed trades here so we can resolve
    # their regime from scan_contexts AFTER scan_phase.run() completes.
    _pending_ssrt_trades: list[tuple] = []

    # ── Weekend mode notice ──────────────────────────────────────────────────
    if weekend_symbols is not None:
        logger.debug(
            "Weekend mode active — scanning only: %s",
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
            "logging", "debug", "Iteration started",
            {"trace_id": iter_trace_id, "loop": loop_count,
             "session": session_profile, "scan_workers": scan_workers},
        )

    # ── Crucix macro sweep (once per iteration) ──────────────────────────
    crucix_agent.run()

    # ── Monitor existing trades ─────────────────────────────────────────────
    _ui = tui.get_ui()
    if _ui:
        _ui.set_agent_status("trade_mgr", "monitoring open positions")
    open_before = {t.id for t in trade_manager.get_open_trades()}
    trade_manager.monitor()
    open_after = {t.id for t in trade_manager.get_open_trades()}

    # Track trade open/close events
    for t in trade_manager.get_open_trades():
        open_time = getattr(t, "open_time", None)
        ts = open_time.timestamp() if open_time and hasattr(open_time, "timestamp") else time.time()
        symbol_event_tracker.update(t.symbol, "last_trade_open", ts)
    just_closed_ids = open_before - open_after
    for trade_id in just_closed_ids:
        closed_trade = db.get_trade(trade_id)
        if closed_trade:
            close_time = getattr(closed_trade, "close_time", None)
            ts = close_time.timestamp() if close_time and hasattr(close_time, "timestamp") else time.time()
            symbol_event_tracker.update(closed_trade.symbol, "last_trade_close", ts)
            learning.review_trade(closed_trade)
            log_agent.log_trade_to_csv(closed_trade)
            log_agent.log_trade(closed_trade.id, "CLOSED",
                                f"{closed_trade.close_reason} PnL={closed_trade.pnl:.2f}")
            opportunity_lifecycle.register_trade_close(closed_trade)
            # Queue for SSRT processing — regime will be resolved post-scan
            _pending_ssrt_trades.append((closed_trade, closed_trade.symbol))

    rolled_symbols = opportunity_lifecycle.on_iteration_start(
        symbols=active_symbols,
        open_trades=trade_manager.get_open_trades(),
    )
    if rolled_symbols:
        logger.info("Opportunity lifecycle rollover: %s",
                    ", ".join(rolled_symbols[:10]))

    m = MetricsDelta()
    m.loops = 1

    # ── Skip new signals if paused ─────────────────────────────────────────
    if telegram_bot.is_paused():
        logger.warning("Bot is PAUSED — skipping signal detection (loop %d)", loop_count)
        return m

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 1: Scan
    # ══════════════════════════════════════════════════════════════════════
    open_symbols = {t.symbol for t in trade_manager.get_open_trades()}

    scan_phase = ScanPhase(
        broker=broker,
        market_agent=market_agent,
        analysis_agent=analysis_agent,
        strategy_agent=strategy_agent,
        db=db,
        symbol_event_tracker=symbol_event_tracker,
        hku_client=hku_client,
    )
    scan_result: ScanResult = scan_phase.run(
        active_symbols=active_symbols,
        open_symbols=open_symbols,
        last_scan_ts=last_scan_ts,
        symbol_fail_count=symbol_fail_count,
        symbol_disabled_until=symbol_disabled_until,
        symbol_max_fails=symbol_max_fails,
        symbol_disable_secs=symbol_disable_secs,
        scan_cooldown=scan_cooldown,
        session_profile=session_profile,
        weekend_symbols=weekend_symbols,
        scan_workers=scan_workers,
        metrics=metrics,
        loop_count=loop_count,
    )
    m.scanned_symbols = len(scan_result.scanned)
    m.raw_signals = len(scan_result.all_signals)
    m.last_scan_latency_ms = scan_result.latency_ms

    if hard_budget_enabled and scan_result.latency_ms > max_scan_ms:
        m.budget_scan_hits = 1
        logger.warning(
            "Scan hard budget exceeded: %.1fms > %.1fms",
            scan_result.latency_ms, max_scan_ms,
        )

    # Abort iteration if scan phase degraded
    if scan_result.abort_reason is not None:
        db.log_agent_event(
            "logging", "warn", "Degraded loop mode — scan quality too poor",
            {"trace_id": iter_trace_id, "loop": loop_count,
             "reason": scan_result.abort_reason, "action": "skip_rank_and_execute"},
        )
        m.last_rank_latency_ms = 0.0
        m.last_execution_latency_ms = 0.0
        m.last_signal_to_order_ms = -1.0
        return m

    if not scan_result.scanned:
        m.last_rank_latency_ms = 0.0
        m.last_execution_latency_ms = 0.0
        m.last_signal_to_order_ms = -1.0
        logger.debug("Loop %d: all symbols on cooldown or skipped", loop_count)
        return m

    if not scan_result.all_signals:
        if settings.DEFERRED_ENTRY_ENABLED and deferred_entries:
            promoted = _promote_deferred_inline(
                deferred_entries, scan_result.signal_contexts,
                scan_result.all_signals,
            )
            m.deferred_promoted = promoted
        if not scan_result.all_signals:
            m.last_rank_latency_ms = 0.0
            m.last_execution_latency_ms = 0.0
            m.last_signal_to_order_ms = -1.0
            logger.info("Loop %d: scanned %s — no signals generated",
                         loop_count, ", ".join(scan_result.scanned))
            # Process deferred SSRT trades even with no fresh signals
            if ssrt_agent and _pending_ssrt_trades:
                _process_ssrt_queue(_pending_ssrt_trades, scan_result.signal_contexts, ssrt_agent)
            return m

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 2: Rank
    # ══════════════════════════════════════════════════════════════════════
    rank_phase = RankPhase(
        sniper_guard=sniper_guard,
        opportunity_lifecycle=opportunity_lifecycle,
    )
    rank_result = rank_phase.run(
        all_signals=scan_result.all_signals,
        signal_contexts=scan_result.signal_contexts,
        deferred_entries=deferred_entries,
        metrics=metrics,
        hard_budget_enabled=hard_budget_enabled,
        max_rank_ms=max_rank_ms,
        weekend_symbols=weekend_symbols,
    )
    scan_result.signal_contexts = rank_result.signal_contexts  # updated with deferred

    m.last_rank_latency_ms = rank_result.latency_ms

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 3: Execute
    # ══════════════════════════════════════════════════════════════════════
    exec_phase = ExecutePhase(
        risk_agent=risk_agent,
        execution_agent=execution_agent,
        trade_manager=trade_manager,
        log_agent=log_agent,
        sniper_guard=sniper_guard,
    )
    signal_ready_ts = time.monotonic()
    exec_result = exec_phase.run(
        ranked=rank_result.ranked,
        signal_contexts=scan_result.signal_contexts,
        deferred_entries=deferred_entries,
        metrics=metrics,
        risk_reject_reason_counts=risk_reject_reason_counts,
        hard_budget_enabled=hard_budget_enabled,
        max_exec_ms=max_exec_ms,
        max_iter_ms=max_iter_ms,
        execution_phase_start=signal_ready_ts,
        iter_start_ts=iter_start_ts,
    )

    m.last_execution_latency_ms = exec_result.latency_ms
    m.last_signal_to_order_ms = exec_result.first_signal_to_order_ms

    logger.debug(
        "Loop %d timing | session=%s scan=%.1fms rank=%.1fms exec=%.1fms "
        "signal_to_order=%.1fms total=%.1fms",
        loop_count, session_profile,
        m.last_scan_latency_ms,
        m.last_rank_latency_ms,
        m.last_execution_latency_ms,
        m.last_signal_to_order_ms,
        (time.monotonic() - iter_start_ts) * 1000.0,
    )

    if settings.ORCHESTRATION_ENABLE_ITERATION_TRACE:
        db.log_agent_event(
            "logging", "debug", "Iteration completed",
            {
                "trace_id": iter_trace_id,
                "loop": loop_count,
                "scanned": len(scan_result.scanned),
                "scan_errors": len(scan_result.scan_error_symbols),
                "ranked_processed": len(rank_result.ranked),
                "scan_latency_ms": m.last_scan_latency_ms,
                "rank_latency_ms": m.last_rank_latency_ms,
                "exec_latency_ms": m.last_execution_latency_ms,
                "signal_to_order_ms": m.last_signal_to_order_ms,
            },
        )

    if _ui:
        for name in ("market", "analysis", "strategy", "risk", "execution", "trade_mgr"):
            _ui.set_agent_idle(name)

    # Process any pending SSRT trades now that scan_contexts is fully populated
    if ssrt_agent and _pending_ssrt_trades:
        _process_ssrt_queue(_pending_ssrt_trades, scan_result.signal_contexts, ssrt_agent)

    return m


def _process_ssrt_queue(
    pending: list[tuple],
    signal_contexts: dict[int, MarketContext],
    ssrt_agent: "SSRTAgent",
) -> None:
    """Resolve regime from scan_contexts and call SSRT update for each queued trade."""
    for trade, symbol in pending:
        context: MarketContext | None = None
        for ctx in signal_contexts.values():
            if ctx.symbol == symbol:
                context = ctx
                break
        if context is None:
            logger.warning("SSRT: no MarketContext for %s — using defaults", symbol)
            garch_regime, trend_direction = "normal", "neutral"
        else:
            garch_regime = getattr(context, "garch_regime", "normal")
            trend_direction = getattr(context, "trend_direction", "neutral")
        verdict = ssrt_agent.update_trade(trade, garch_regime, trend_direction)
        if verdict and verdict.retired:
            logger.info(
                "SSRT retired strategy=%s symbol=%s verdict=%s "
                "total_trades=%d final_msptr=%s",
                trade.strategy, trade.symbol, verdict.verdict,
                verdict.total_trades, f"{verdict.mixture_sprt:.4f}" if verdict.mixture_sprt else "n/a",
            )


def _promote_deferred_inline(
    deferred_entries: list[dict[str, object]],
    signal_contexts: dict[int, MarketContext],
    all_signals: list[Signal],
) -> int:
    """Promote deferred signals inline when no fresh signals were generated.

    Extracted from RankPhase to avoid complexity when there are no new signals.
    Returns the number of signals promoted.
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
    return len(promoted)
