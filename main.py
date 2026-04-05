"""Trading Bot — main entry point.

Wires all agents, runs the time-corrected main loop, handles startup
reconciliation and graceful shutdown.

Phase 1 uses MockConnector + DEMO_MODE = False — fully runnable end-to-end.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import os
import signal
import sys
import threading
import time

# Enable ANSI colour codes on Windows CMD / PowerShell
if sys.platform == "win32":
    os.system("")  # activates VT100 processing for the current console
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from broker.connector import BrokerConnector
from broker.mock_connector import MockConnector
from config import settings
from config.symbols import SYMBOLS

# ── Filter symbols to only those available on the broker ────────────────
_active_symbols = SYMBOLS[:]
from database.db import Database
from filters.data_validator import DataValidationError
from state.persistence import StatePersistence
from models.market_data import MarketContext
from models.signal import Signal
from strategies.sma_crossover import SmaCrossoverStrategy
from strategies.ict_strategy import ICTStrategy

from agents.market_agent import MarketAgent
from agents.analysis_agent import AnalysisAgent
from agents.strategy_agent import StrategyAgent
from agents.risk_agent import RiskAgent
from agents.execution_agent import ExecutionAgent
from agents.trade_manager import TradeManagerAgent
from agents.learning_agent import LearningAgent
from agents.logging_agent import LoggingAgent
from agents.reflector import Reflector
from agents.council_agent import CouncilAgent
from agents.crucix_agent import CrucixAgent
from agents.deepseek_strategy import DeepSeekStrategy

from utils import telegram_bot
from utils import candle_server
from utils import terminal_ui as tui
from utils.helpers import current_session, is_market_open, is_any_market_open, is_weekend, local_now
from utils.orchestration_profiler import OrchestrationProfiler, OrchestrationTargets
from utils.symbol_event_tracker import SymbolEventTracker
from utils.telegram_reports import build_pnl_curve_png
from utils.tool_system import AutonomousToolSystem, result_to_text

logger = logging.getLogger(__name__)

# ── Global shutdown flag ────────────────────────────────────────────────
_shutdown = False


def _request_shutdown() -> None:
    global _shutdown
    _shutdown = True


def main() -> None:
    global _shutdown

    # ── 1. Core infrastructure ──────────────────────────────────────────
    db = Database()

    # ── 1a. Symbol event tracker ─────────────────────────────────────────
    symbol_event_tracker = SymbolEventTracker()

    # Resolve broker credentials: DB active account → .env fallback
    _acct_id: int | None = None
    db_account = db.get_active_broker_account()
    if db_account:
        acct_num = db_account["account_number"]
        acct_pwd = db_account["password"]
        acct_srv = db_account["server"]
        _acct_id = db_account["id"]
        logger.info("Using DB broker account: %s @ %s (id=%d)",
                     acct_num, acct_srv, _acct_id)
    else:
        acct_num = settings.BROKER_ACCOUNT
        acct_pwd = settings.BROKER_PASSWORD
        acct_srv = settings.BROKER_SERVER

    broker: BrokerConnector
    if acct_num and acct_pwd and acct_srv:
        try:
            from broker.mt5_connector import MT5Connector
            broker = MT5Connector(
                account=acct_num, password=acct_pwd, server=acct_srv,
            )
            if not broker.connect():
                logger.critical("MT5 connection failed — aborting")
                sys.exit(1)
            if _acct_id:
                db.mark_broker_connected(_acct_id)
        except ImportError:
            logger.warning(
                "MetaTrader5 package not available (requires Python ≤3.13) "
                "— falling back to MockConnector"
            )
            broker = MockConnector()
            broker.connect()
    else:
        broker = MockConnector()
        broker.connect()

    state = StatePersistence(db, broker)
    crucix_agent = CrucixAgent(db=db)

    # ── Filter symbols to those available on the broker ─────────────────
    global _active_symbols
    if hasattr(broker, "get_available_symbols"):
        _active_symbols = broker.get_available_symbols(SYMBOLS)
        removed = set(SYMBOLS) - set(_active_symbols)
        if removed:
            logger.warning("Symbols not available on broker (removed): %s", ", ".join(sorted(removed)))
    else:
        _active_symbols = SYMBOLS[:]
    logger.info("Active symbols: %s", ", ".join(_active_symbols))

    # ── 2. Logging agent first (sets up Python logging) ─────────────────
    log_agent = LoggingAgent(db)
    log_agent.record("STARTUP", f"Bot started — DEMO_MODE={settings.DEMO_MODE}")

    # ── Crucix intelligence layer ────────────────────────────────────────
    _startup_macro = crucix_agent.get_context()
    if _startup_macro.crucix_available:
        _age = _startup_macro.last_sweep_age_minutes
        _age_str = f"{_age:.0f}min" if _age < 999 else "no sweep yet"
        log_agent.record(
            "STARTUP",
            f"Crucix connected — tier={_startup_macro.risk_tier} vix={_startup_macro.vix:.1f} "
            f"sweep_age={_age_str}",
        )
        logger.info(
            "Crucix intelligence: CONNECTED — tier=%s vix=%.1f",
            _startup_macro.risk_tier, _startup_macro.vix,
        )
    else:
        log_agent.record("STARTUP", "Crucix intelligence: NOT RUNNING — macro context disabled (bot continues normally)")
        logger.info("Crucix intelligence: NOT RUNNING — starting without macro context")

    # ── 1b. Candle HTTP server for dashboard charts ──────────────────────
    # (moved after log_agent so startup errors can be logged)
    candle_server.start(broker, db)

    # ── 3. Learning agent + post-trade Reflector ─────────────────────────
    learning = LearningAgent(db)
    reflector = Reflector()
    learning.set_reflector(reflector)

    # ── 4. Strategies — DeepSeek (primary LLM) + ICT/SMC + SMA crossover
    deepseek_strategy = DeepSeekStrategy()
    ict_strategy = ICTStrategy(broker=broker, db=db, min_confidence=55.0)
    sma_strategy = SmaCrossoverStrategy()
    strategies = [deepseek_strategy, ict_strategy, sma_strategy]
    logger.info("Multi-strategy mode: DeepSeek LLM + ICT/SMC + SMAcrossover")

    # ── Weekend crypto strategies — multi-TF ICT for BTCUSD ─────────────
    # During the forex weekend, only crypto trades.  Three ICT instances
    # cover the full timeframe stack: intraday (M15+H4), swing (H1+D1),
    # and macro (H4+W1).  The existing ict_strategy covers M15+H4.
    ict_btc_h1d1 = ICTStrategy(
        broker=broker, db=db, min_confidence=55.0,
        htf_timeframe="D1", htf_candle_count=100,
        entry_timeframe="H1", entry_candle_count=200,
    )
    ict_btc_h4w1 = ICTStrategy(
        broker=broker, db=db, min_confidence=50.0,  # slightly lower — H4 setups are rarer
        htf_timeframe="W1", htf_candle_count=52,
        entry_timeframe="H4", entry_candle_count=150,
    )
    weekend_strategies = [deepseek_strategy, ict_btc_h4w1, ict_strategy, ict_btc_h1d1]

    # Parse weekend symbol list (e.g. "BTCUSD" or "BTCUSD,ETHUSD")
    _weekend_symbols: list[str] = [
        s.strip() for s in settings.WEEKEND_SYMBOLS.split(",") if s.strip()
    ]

    # ── 6. Agents (db passed for persona events) ────────────────────────
    market_agent = MarketAgent(broker, db=db)
    analysis_agent = AnalysisAgent(crucix_agent, db=db)
    trade_manager = TradeManagerAgent(broker, state, db)
    risk_agent = RiskAgent(broker, trade_manager.get_open_trades, crucix_agent, db=db)
    strategy_agent = StrategyAgent(strategies, learning.get_confidence, db=db)
    weekend_strategy_agent = StrategyAgent(weekend_strategies, learning.get_confidence, db=db)
    execution_agent = ExecutionAgent(broker, state, risk_agent.calculate_position_size, db=db)

    def _get_active_symbols_local() -> list[str]:
        return _active_symbols[:]

    def _set_active_symbols_local(new_symbols: list[str]) -> None:
        global _active_symbols
        _active_symbols = new_symbols[:]
        logger.warning("Tool system updated active symbols: %s", ", ".join(_active_symbols))

    tool_system = AutonomousToolSystem(
        repo_root=Path(__file__).resolve().parent,
        db=db,
        broker=broker,
        trade_manager=trade_manager,
        risk_agent=risk_agent,
        get_active_symbols=_get_active_symbols_local,
        set_active_symbols=_set_active_symbols_local,
        base_symbols=_active_symbols[:],
    )

    # ── Trading Council (algorithmic quality gate) ────────────────────────
    council: CouncilAgent | None = None
    if settings.COUNCIL_ENABLED:
        council = CouncilAgent()
    # Always log the Council state regardless of the flag
    council_state = "ENABLED" if settings.COUNCIL_ENABLED else "DISABLED"
    logger.info(
        "Trading Council %s (min confidence: %.0f%%)",
        council_state,
        settings.COUNCIL_MIN_CONFIDENCE * 100,
    )
    log_agent.record(
        "STARTUP",
        f"Trading Council {council_state} — 3-expert algorithmic gate "
        f"(min conf {settings.COUNCIL_MIN_CONFIDENCE:.0%})",
    )

    # ── 7. Startup reconciliation ───────────────────────────────────────
    trade_manager.load_open_trades()
    trade_manager.reconcile()
    log_agent.record("STARTUP", f"Reconciliation done — {len(trade_manager.get_open_trades())} open trades")
    db.set_bot_uptime_start()

    # ── 7b. Terminal UI (Rich live dashboard) ───────────────────────────
    _ui = tui.init(refresh_per_second=4)
    _ui.set_bot_status("STARTING", open_trades=len(trade_manager.get_open_trades()))

    # ── 7. Telegram ─────────────────────────────────────────────────────
    def _status_callback() -> str:
        equity = broker.get_equity()
        balance = broker.get_balance()
        open_count = len(trade_manager.get_open_trades())
        return (
            f"💰 Balance: {balance:.2f} | Equity: {equity:.2f}\n"
            f"📊 Open trades: {open_count}\n"
            f"⏱ Loop interval: {settings.LOOP_INTERVAL_SECONDS}s\n"
            f"🎛 Demo: {settings.DEMO_MODE}"
        )

    def _graph_callback() -> tuple[str, bytes] | None:
        return build_pnl_curve_png(db, days=settings.TELEGRAM_CHART_DAYS)

    telegram_bot.register_callbacks(None, _status_callback, _graph_callback)
    telegram_bot.start_polling()
    telegram_bot.send_message("🤖 Trading bot started (DEMO)", priority="high", force=True)

    # ── 8. Signal handlers for graceful shutdown ────────────────────────
    def _sig_handler(signum: int, frame: object) -> None:
        logger.info("Signal %d received — shutting down", signum)
        _request_shutdown()

    signal.signal(signal.SIGINT, _sig_handler)
    signal.signal(signal.SIGTERM, _sig_handler)

    # ── 9. Main loop ────────────────────────────────────────────────────
    loop_count = 0
    last_summary_date = ""

    logger.info("Entering main loop (interval=%ds)", settings.LOOP_INTERVAL_SECONDS)

    _market_closed_logged = False
    _last_scan_ts: dict[str, float] = {}  # symbol → monotonic time of last analysis
    _deferred_entries: list[dict[str, object]] = []
    _metrics: dict[str, float] = {
        "loops": 0,
        "scanned_symbols": 0,
        "raw_signals": 0,
        "ranked_signals": 0,
        "council_rejections": 0,
        "risk_rejections": 0,
        "fast_lane_attempts": 0,
        "fast_lane_fills": 0,
        "fast_lane_closed": 0,
        "full_lane_fills": 0,
        "deferred_added": 0,
        "deferred_promoted": 0,
        "last_scan_latency_ms": 0.0,
        "last_rank_latency_ms": 0.0,
        "last_execution_latency_ms": 0.0,
        "last_signal_to_order_ms": -1.0,
    }
    profiler = OrchestrationProfiler(
        OrchestrationTargets(
            scan_ms=settings.ORCHESTRATION_TARGET_SCAN_MS,
            rank_ms=settings.ORCHESTRATION_TARGET_RANK_MS,
            exec_ms=settings.ORCHESTRATION_TARGET_EXEC_MS,
            total_ms=settings.ORCHESTRATION_TARGET_TOTAL_MS,
        )
    )
    scan_workers = max(
        settings.ORCHESTRATION_SCAN_WORKERS_MIN,
        min(
            settings.ORCHESTRATION_SCAN_WORKERS_DEFAULT,
            settings.ORCHESTRATION_SCAN_WORKERS_MAX,
        ),
    )

    # ── Symbol fault tracking ────────────────────────────────────────────
    # Symbols with repeated IPC / data errors are temporarily disabled to
    # avoid wasting time on each loop iteration.
    _symbol_fail_count:     dict[str, int]   = {}   # consecutive failures
    _symbol_disabled_until: dict[str, float] = {}   # monotonic re-enable time
    _SYMBOL_MAX_FAILS      = settings.SYMBOL_MAX_FAIL_COUNT
    _SYMBOL_DISABLE_SECS   = float(settings.SYMBOL_DISABLE_SECONDS)

    # Restore fault state persisted from the previous run
    try:
        _now_utc = datetime.now(UTC)
        _now_mono = time.monotonic()
        for _sym, _fault in db.load_symbol_faults().items():
            _symbol_fail_count[_sym] = _fault["fail_count"]
            if _fault["disabled_until"] is not None:
                _remaining = (_fault["disabled_until"] - _now_utc).total_seconds()
                if _remaining > 0:
                    _symbol_disabled_until[_sym] = _now_mono + _remaining
                    logger.info("Restored fault state for %s — disabled for %.0fs more", _sym, _remaining)
    except Exception:
        logger.warning("Could not load symbol fault state from DB — starting fresh")

    while not _shutdown:
        loop_start = time.monotonic()
        loop_count += 1
        scanned_before = _metrics.get("scanned_symbols", 0)
        _active_session = current_session(datetime.now(UTC))
        if _active_session in {"london", "newyork", "overlap"}:
            _active_scan_cooldown = float(settings.SCAN_COOLDOWN_SECONDS_LONDON_NY)
        else:
            _active_scan_cooldown = float(settings.SCAN_COOLDOWN_SECONDS_ASIA)

        # ── Market hours: if ALL markets are closed, sleep longer ────────
        if not is_any_market_open(_active_symbols):
            if not _market_closed_logged:
                logger.info("All markets closed — sleeping (still processing commands & heartbeat)")
                _market_closed_logged = True
            # Still process commands and heartbeat
            try:
                _update_heartbeat(db, broker, trade_manager, learning)
            except Exception:
                logger.warning("Heartbeat update failed — continuing")
            _process_commands(db, trade_manager, tool_system)
            # Sleep in short bursts so kill/commands are picked up quickly
            for _ in range(30):  # 30 × 10s = 5 min total
                if _shutdown or telegram_bot.is_kill_requested():
                    break
                time.sleep(10)
            continue
        elif _market_closed_logged:
            logger.info("Markets reopened — resuming normal operation")
            _market_closed_logged = False

        try:
            _weekend = is_weekend()
            _run_iteration(
                loop_count=loop_count,
                db=db,
                broker=broker,
                crucix_agent=crucix_agent,
                market_agent=market_agent,
                analysis_agent=analysis_agent,
                strategy_agent=weekend_strategy_agent if _weekend else strategy_agent,
                risk_agent=risk_agent,
                execution_agent=execution_agent,
                trade_manager=trade_manager,
                learning=learning,
                log_agent=log_agent,
                council=council,
                symbol_event_tracker=symbol_event_tracker,
                last_scan_ts=_last_scan_ts,
                scan_cooldown=_active_scan_cooldown,
                deferred_entries=_deferred_entries,
                metrics=_metrics,
                symbol_fail_count=_symbol_fail_count,
                symbol_disabled_until=_symbol_disabled_until,
                symbol_max_fails=_SYMBOL_MAX_FAILS,
                symbol_disable_secs=_SYMBOL_DISABLE_SECS,
                session_profile=_active_session,
                weekend_symbols=_weekend_symbols if _weekend else None,
                scan_workers=scan_workers,
            )
        except Exception:
            logger.exception("Unhandled error in main loop iteration %d", loop_count)

        loop_elapsed_ms = (time.monotonic() - loop_start) * 1000.0
        profiler.record(
            scan_ms=_metrics.get("last_scan_latency_ms", 0.0),
            rank_ms=_metrics.get("last_rank_latency_ms", 0.0),
            exec_ms=_metrics.get("last_execution_latency_ms", 0.0),
            total_ms=loop_elapsed_ms,
        )
        if settings.ORCHESTRATION_ADAPTIVE_WORKERS_ENABLED:
            scanned_this_loop = int(_metrics.get("scanned_symbols", 0) - scanned_before)
            suggested = profiler.recommend_workers(
                current_workers=scan_workers,
                min_workers=settings.ORCHESTRATION_SCAN_WORKERS_MIN,
                max_workers=settings.ORCHESTRATION_SCAN_WORKERS_MAX,
                scanned_symbol_count=max(0, scanned_this_loop),
            )
            if suggested != scan_workers:
                logger.info(
                    "Adaptive scan workers: %d -> %d (scanned=%d, avg_scan=%.1fms, target=%.1fms)",
                    scan_workers,
                    suggested,
                    max(0, scanned_this_loop),
                    profiler.snapshot()["avg_scan_ms"],
                    settings.ORCHESTRATION_TARGET_SCAN_MS,
                )
                scan_workers = suggested

        # ── Periodic reconciliation ──────────────────────────────────────
        if loop_count % settings.RECONCILE_EVERY_N_LOOPS == 0:
            trade_manager.reconcile()
            log_agent.record("RECONCILE", f"Periodic reconciliation (loop {loop_count})")

        # ── Bot status heartbeat ─────────────────────────────────────────
        try:
            _update_heartbeat(db, broker, trade_manager, learning)
        except Exception:
            logger.warning("Heartbeat update failed — continuing")

        if settings.METRICS_LOG_EVERY_N_LOOPS > 0 and loop_count % settings.METRICS_LOG_EVERY_N_LOOPS == 0:
            profile = profiler.snapshot()
            bottleneck = profiler.primary_bottleneck()
            logger.info(
                "KPI snapshot @loop %d | scanned=%d raw=%d ranked=%d council_rej=%d risk_rej=%d "
                "fast_attempts=%d fast_fills=%d fast_closed=%d full_fills=%d deferred_added=%d deferred_promoted=%d "
                "session=%s cooldown=%.0fs scan_ms=%.1f rank_ms=%.1f exec_ms=%.1f signal_to_order_ms=%.1f "
                "avg_scan=%.1f avg_rank=%.1f avg_exec=%.1f avg_total=%.1f workers=%d bottleneck=%s",
                loop_count,
                _metrics["scanned_symbols"],
                _metrics["raw_signals"],
                _metrics["ranked_signals"],
                _metrics["council_rejections"],
                _metrics["risk_rejections"],
                _metrics["fast_lane_attempts"],
                _metrics["fast_lane_fills"],
                _metrics["fast_lane_closed"],
                _metrics["full_lane_fills"],
                _metrics["deferred_added"],
                _metrics["deferred_promoted"],
                _active_session,
                _active_scan_cooldown,
                _metrics["last_scan_latency_ms"],
                _metrics["last_rank_latency_ms"],
                _metrics["last_execution_latency_ms"],
                _metrics["last_signal_to_order_ms"],
                profile["avg_scan_ms"],
                profile["avg_rank_ms"],
                profile["avg_exec_ms"],
                profile["avg_total_ms"],
                scan_workers,
                bottleneck,
            )
            db.log_agent_event(
                "logging",
                "info",
                (
                    f"Loop telemetry: session={_active_session} cooldown={_active_scan_cooldown:.0f}s "
                    f"scan={_metrics['last_scan_latency_ms']:.1f}ms "
                    f"rank={_metrics['last_rank_latency_ms']:.1f}ms "
                    f"exec={_metrics['last_execution_latency_ms']:.1f}ms "
                    f"signal_to_order={_metrics['last_signal_to_order_ms']:.1f}ms "
                    f"avg_total={profile['avg_total_ms']:.1f}ms workers={scan_workers} "
                    f"bottleneck={bottleneck}"
                ),
                {
                    "loop": loop_count,
                    "session": _active_session,
                    "scan_cooldown_s": _active_scan_cooldown,
                    "scan_latency_ms": _metrics["last_scan_latency_ms"],
                    "rank_latency_ms": _metrics["last_rank_latency_ms"],
                    "execution_latency_ms": _metrics["last_execution_latency_ms"],
                    "signal_to_order_latency_ms": _metrics["last_signal_to_order_ms"],
                    "scan_workers": scan_workers,
                    "avg_scan_latency_ms": profile["avg_scan_ms"],
                    "avg_rank_latency_ms": profile["avg_rank_ms"],
                    "avg_execution_latency_ms": profile["avg_exec_ms"],
                    "avg_total_latency_ms": profile["avg_total_ms"],
                    "bottleneck": bottleneck,
                },
            )

        if (
            settings.TOOL_SYSTEM_ENABLED
            and settings.TOOL_SYSTEM_AUTORUN_EVERY_N_LOOPS > 0
            and loop_count % settings.TOOL_SYSTEM_AUTORUN_EVERY_N_LOOPS == 0
        ):
            try:
                tool_system.run_cycle(loop_count=loop_count, metrics=_metrics)
            except Exception:
                logger.exception("Tool system cycle failed — continuing")

        # ── Process UI command queue ─────────────────────────────────────
        _process_commands(db, trade_manager, tool_system)

        # ── Daily summary (triggered at DAILY_SUMMARY_HOUR in local time) ──
        now = local_now()
        today_str = now.strftime("%Y-%m-%d")
        if (now.hour >= settings.DAILY_SUMMARY_HOUR
                and today_str != last_summary_date):
            report = learning.get_report()
            log_agent.send_daily_summary(report)
            # Save daily performance snapshot and compare to yesterday
            try:
                learning.snapshot_daily()
                if now.weekday() == 6:          # Sunday → weekly snapshot
                    learning.snapshot_weekly()
                if now.day == 1:                # 1st of month → monthly snapshot
                    learning.snapshot_monthly()
            except Exception:
                logger.exception("Performance snapshot failed — bot continues")
            last_summary_date = today_str

        # ── Time-corrected sleep ─────────────────────────────────────────
        elapsed = time.monotonic() - loop_start
        sleep_time = max(0, settings.LOOP_INTERVAL_SECONDS - elapsed)
        if sleep_time > 0:
            time.sleep(sleep_time)

    # ── 10. Shutdown ─────────────────────────────────────────────────────
    logger.info("Shutting down…")
    _ui.stop()
    candle_server.stop()
    telegram_bot.stop_polling()
    telegram_bot.send_message("🛑 Bot shutting down.")
    db.set_bot_stopped()
    broker.disconnect()
    db.close()
    log_agent.record("SHUTDOWN", "Bot stopped gracefully")
    logger.info("Goodbye.")


# ── Command queue processor ──────────────────────────────────────────────

def _process_commands(
    db: Database,
    trade_manager: TradeManagerAgent,
    tool_system: AutonomousToolSystem | None = None,
) -> None:
    """Poll the bot_commands table and Telegram kill flag for pending commands."""
    # ── Check Telegram kill flag (set by polling thread) ─────────────
    if telegram_bot.is_kill_requested():
        telegram_bot.pause()  # block new trades immediately
        trade_manager.close_all("KILL_SWITCH")
        telegram_bot.send_message("✅ All positions closed. Bot stopped.")
        _request_shutdown()
        return

    # ── Process DB command queue (web dashboard) ─────────────────────
    for cmd in db.get_pending_commands():
        cmd_name = cmd["command"]
        try:
            if cmd_name == "kill":
                telegram_bot.pause()  # block new trades during shutdown
                trade_manager.close_all("UI_KILL")
                db.update_command(cmd["id"], "done", "All trades closed, shutting down")
                telegram_bot.send_message("🛑 KILL from dashboard — all positions closed, shutting down.")
                _request_shutdown()
            elif cmd_name == "pause":
                telegram_bot.pause()
                db.update_command(cmd["id"], "done", "Bot paused")
                telegram_bot.send_message("⏸️ Bot PAUSED (from dashboard)")
            elif cmd_name == "resume":
                telegram_bot.resume()
                db.update_command(cmd["id"], "done", "Bot resumed")
                telegram_bot.send_message("▶️ Bot RESUMED (from dashboard)")
            elif cmd_name == "close_trade":
                payload = cmd.get("payload") or {}
                trade_id = payload.get("trade_id", "")
                trade_manager.close_trade(trade_id, "UI_CLOSE")
                db.update_command(cmd["id"], "done", f"Trade {trade_id} closed")
                telegram_bot.send_message(f"📤 Trade {trade_id} closed (from dashboard)")
            elif cmd_name == "skill":
                from utils.skill_manager import SkillManager
                payload = cmd.get("payload") or {}
                action = payload.get("action", "")
                skill_name = payload.get("skill", "")
                sm = SkillManager(db=db)
                if action == "list":
                    result = sm.list_skills()
                    db.log_agent_event("skill_manager", "info",
                                       f"Skills listed: {len(result)} found",
                                       {"skills": result})
                    db.update_command(cmd["id"], "done", str(result))
                elif action == "read" and skill_name:
                    content = sm.read_skill(skill_name)
                    db.log_agent_event("skill_manager", "info",
                                       f"Skill read: {skill_name}",
                                       {"content": content[:500]})
                    db.update_command(cmd["id"], "done", content[:2000])
                elif action == "apply" and skill_name:
                    argument = payload.get("argument", "")
                    rendered = sm.apply_skill(skill_name, argument)
                    db.update_command(cmd["id"], "done", rendered[:2000])
                else:
                    db.update_command(cmd["id"], "failed",
                                     f"Unknown skill action: {action}")
            elif cmd_name == "tool":
                payload = cmd.get("payload") or {}
                action = payload.get("action", "")
                if tool_system is None:
                    db.update_command(cmd["id"], "failed", "Tool system not initialized")
                elif action == "list":
                    db.update_command(
                        cmd["id"],
                        "done",
                        json.dumps({"tools": tool_system.list_tools()}, ensure_ascii=True),
                    )
                elif action == "run":
                    tool_name = str(payload.get("tool", "")).strip()
                    result = tool_system.execute_tool(tool_name, payload)
                    db.update_command(cmd["id"], "done", result_to_text(result))
                else:
                    db.update_command(
                        cmd["id"],
                        "failed",
                        f"Unknown tool action: {action}",
                    )
            else:
                db.update_command(cmd["id"], "failed", f"Unknown command: {cmd_name}")
        except Exception as exc:
            db.update_command(cmd["id"], "failed", str(exc))


# ── Heartbeat updater ────────────────────────────────────────────────────

_hb_equity: float = 0.0
_hb_balance: float = 0.0


def _broker_call_safe(fn, *args, timeout: float = 5.0, default: float = 0.0) -> float:
    """Call *fn* in a thread; return *default* if it hangs or raises."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
        fut = ex.submit(fn, *args)
        try:
            return fut.result(timeout=timeout)
        except Exception:
            return default


def _update_heartbeat(
    db: Database,
    broker: BrokerConnector,
    trade_manager: TradeManagerAgent,
    learning: LearningAgent,
) -> None:
    """Write current bot metrics to bot_status row."""
    global _hb_equity, _hb_balance
    # Call directly on the main thread — MT5 API is NOT thread-safe and
    # returns None when called from a ThreadPoolExecutor thread.
    try:
        equity = broker.get_equity()
        _hb_equity = equity
    except Exception:
        equity = _hb_equity
    try:
        balance = broker.get_balance()
        _hb_balance = balance
    except Exception:
        balance = _hb_balance
    open_count = len(trade_manager.get_open_trades())
    report = learning.get_report()
    daily_pnl = report.get("total_pnl", 0.0)
    state = "paused" if telegram_bot.is_paused() else "running"

    # Broker connection metadata
    broker_account = ""
    broker_server = ""
    broker_name = ""
    leverage = 0
    info = getattr(broker, "account_info_cache", None)
    if info:
        broker_account = str(info.get("login", ""))
        broker_server = info.get("server", "")
        broker_name = info.get("name", "")
        leverage = info.get("leverage", 0)

    db.update_bot_status(
        state, equity, open_count, daily_pnl,
        broker_account=broker_account,
        broker_server=broker_server,
        broker_name=broker_name,
        balance=balance,
        leverage=leverage,
    )

    ui = tui.get_ui()
    if ui is not None:
        ui.set_bot_status(
            state.upper(), equity=equity, balance=balance,
            daily_pnl=daily_pnl, open_trades=open_count,
        )
        for t in trade_manager.get_open_trades():
            ui.set_trade(t)


def _run_iteration(
    *,
    loop_count: int,
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
    council: CouncilAgent | None,
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
    weekend_symbols: list[str] | None = None,
    scan_workers: int = 6,
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

    metrics["loops"] = metrics.get("loops", 0) + 1

    # ── Skip new signals if paused ───────────────────────────────────────
    if telegram_bot.is_paused():
        logger.warning("Bot is PAUSED — skipping signal detection (loop %d). "
                       "Use /resume or the dashboard to resume.", loop_count)
        return

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 1: Scan ALL symbols — collect every signal
    # ══════════════════════════════════════════════════════════════════════
    all_signals: list[Signal] = []
    # Map signal → its MarketContext so the council has candles + indicators
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
    scan_symbols = _active_symbols[:]
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

        is_cooldown = False
        if now_mono - last_scan_ts.get(symbol, 0.0) < symbol_cooldown:
            if settings.EVENT_DRIVEN_RESCAN_ON_NEW_CANDLE:
                last_candle_ts = symbol_event_tracker.get(symbol, "last_candle")
                if last_candle_ts <= 0 or time.time() - last_candle_ts > symbol_cooldown:
                    is_cooldown = True
            else:
                is_cooldown = True
        
        if is_cooldown:
            return (symbol, "cooldown", is_re_enabled, None, None, None, False)

        try:
            if _tui:
                _tui.set_agent_status("market", f"fetching {symbol}")
            data = market_agent.get_data(symbol)
        except DataValidationError as e:
            err_str = str(e)
            is_ipc = "IPC" in err_str or "No tick data" in err_str or "-10004" in err_str
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
                        from datetime import timedelta
                        db.save_symbol_fault(
                            symbol, count,
                            datetime.now(UTC) + timedelta(seconds=symbol_disable_secs),
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

    metrics["ranked_signals"] = metrics.get("ranked_signals", 0) + len(ranked)
    metrics["last_rank_latency_ms"] = (time.monotonic() - rank_phase_start) * 1000.0
    signal_ready_ts = time.monotonic()
    first_fill_signal_to_order_ms = -1.0
    execution_phase_start = signal_ready_ts

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 3: Execute best signals that pass risk validation
    #
    # Instant-entry mode (INSTANT_ENTRY_ENABLED=true, default):
    #   Top signal → hard risk only → execute immediately → council advisory
    #   post-entry (non-blocking) → full risk post-entry.
    #
    # Classic mode (INSTANT_ENTRY_ENABLED=false):
    #   All signals → council gate (blocking) → risk → execute.
    # ══════════════════════════════════════════════════════════════════════
    for i, signal_obj in enumerate(ranked):

        is_instant = (
            settings.INSTANT_ENTRY_ENABLED
            and i == 0
            and signal_obj.confidence >= settings.INSTANT_ENTRY_MIN_CONFIDENCE
        )
        is_fast_lane = settings.FAST_LANE_ENABLED and i < settings.FAST_LANE_MAX_SIGNALS

        # ── Trading Council gate ─────────────────────────────────────────
        # In instant-entry mode the top signal skips this gate entirely.
        # Council still runs for i>0 signals as a blocking quality filter.
        if council is not None and not is_instant:
            ctx = signal_contexts.get(id(signal_obj))
            if ctx is not None:
                if _tui:
                    _tui.set_agent_status(
                        "council",
                        f"debating {signal_obj.symbol} {signal_obj.direction}",
                    )
                verdict = council.review(signal_obj, ctx)
                if not verdict.approved:
                    msg = (
                        f"Council REJECTED {signal_obj.symbol} {signal_obj.direction} "
                        f"({verdict.confidence:.0%} < {settings.COUNCIL_MIN_CONFIDENCE:.0%}) — "
                        f"{verdict.reasoning}"
                    )
                    logger.info(msg)
                    log_agent.log_risk_rejection(
                        signal_obj.symbol, signal_obj.direction,
                        signal_obj.strategy, f"Council: {verdict.reasoning}",
                    )
                    if _tui:
                        _tui.add_event(
                            "council", "warn",
                            f"REJECT {signal_obj.symbol} {verdict.confidence:.0%}",
                        )
                    from utils import telegram_bot as _tg
                    _tg.send_message(
                        f"🏛️ Council REJECTED {signal_obj.direction} {signal_obj.symbol} "
                        f"— {verdict.confidence:.0%} confidence\n{verdict.reasoning}",
                        dedupe_key=f"council-reject:{signal_obj.symbol}:{signal_obj.direction}",
                    )
                    metrics["council_rejections"] = metrics.get("council_rejections", 0) + 1
                    continue
                else:
                    logger.info(
                        "Council APPROVED %s %s (%.0f%%)",
                        signal_obj.symbol, signal_obj.direction,
                        verdict.confidence * 100,
                    )
                    if _tui:
                        _tui.add_event(
                            "council", "info",
                            f"APPROVED {signal_obj.symbol} {verdict.confidence:.0%}",
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
            log_agent.log_risk_rejection(
                signal_obj.symbol, signal_obj.direction,
                signal_obj.strategy, f"Failed {validation_mode} risk validation")
            if _tui:
                _tui.add_event("risk", "warn",
                               f"REJECT {signal_obj.symbol} {signal_obj.direction}")

            if (
                settings.DEFERRED_ENTRY_ENABLED
                and signal_obj.confidence >= settings.DEFERRED_ENTRY_MIN_CONF
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
            log_agent.log_trade(trade.id, "OPENED",
                                f"{trade.direction} {trade.symbol} {trade.lot_size} lots")
            log_agent.log_trade_to_csv(trade)
            if _tui:
                _tui.set_trade(trade)
                _tui.add_event("execution", "info",
                               f"OPENED {trade.direction} {trade.symbol} @ {trade.entry_price:.5f}")

            if first_fill_signal_to_order_ms < 0.0:
                first_fill_signal_to_order_ms = (time.monotonic() - signal_ready_ts) * 1000.0

            # ── Post-entry council (advisory, instant-entry mode) ────────
            # Runs in a daemon thread — verdict never blocks or closes the trade.
            if is_instant and council is not None:
                ctx = signal_contexts.get(id(signal_obj))
                if ctx is not None:
                    def _run_advisory(
                        _council=council, _sig=signal_obj, _ctx=ctx, _tui=_tui
                    ) -> None:
                        try:
                            verdict = _council.review(_sig, _ctx)
                            conf_str = f"{verdict.confidence:.0%}"
                            if verdict.approved:
                                logger.info(
                                    "Council ADVISORY (post-entry) APPROVED %s %s (%s)",
                                    _sig.symbol, _sig.direction, conf_str,
                                )
                                if _tui:
                                    _tui.add_event(
                                        "council", "info",
                                        f"ADVISORY approved {_sig.symbol} {conf_str}",
                                    )
                            else:
                                logger.warning(
                                    "Council ADVISORY (post-entry) flagged %s %s (%s) — %s",
                                    _sig.symbol, _sig.direction,
                                    conf_str, verdict.reasoning,
                                )
                                if _tui:
                                    _tui.add_event(
                                        "council", "warn",
                                        f"ADVISORY flag {_sig.symbol} {conf_str}",
                                    )
                                from utils import telegram_bot as _tg
                                _tg.send_message(
                                    f"⚠️ Council advisory (post-entry): {_sig.direction} "
                                    f"{_sig.symbol} — {conf_str} confidence\n"
                                    f"{verdict.reasoning}",
                                    dedupe_key=f"council-advisory:{_sig.symbol}:{_sig.direction}",
                                )
                        except Exception:
                            logger.exception("Advisory council thread failed")

                    threading.Thread(target=_run_advisory, daemon=True).start()

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


if __name__ == "__main__":
    main()
