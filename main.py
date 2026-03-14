"""Trading Bot — main entry point.

Wires all agents, runs the time-corrected main loop, handles startup
reconciliation and graceful shutdown.

Phase 1 uses MockConnector + DEMO_MODE = True — fully runnable end-to-end.
"""

from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import UTC, date, datetime

from broker.connector import BrokerConnector
from broker.mock_connector import MockConnector
from config import settings
from config.symbols import SYMBOLS

# ── Filter symbols to only those available on the broker ────────────────
_active_symbols = SYMBOLS[:]
from database.db import Database
from filters.data_validator import DataValidationError
from filters.news_filter import NewsFilter
from state.persistence import StatePersistence
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

from utils import telegram_bot
from utils.helpers import is_market_open, is_any_market_open

logger = logging.getLogger(__name__)

# ── Global shutdown flag ────────────────────────────────────────────────
_shutdown = False


def _request_shutdown() -> None:
    global _shutdown
    _shutdown = True


def main() -> None:
    global _shutdown

    # ── 1. Core infrastructure ──────────────────────────────────────────
    broker: BrokerConnector
    if settings.BROKER_ACCOUNT and settings.BROKER_PASSWORD and settings.BROKER_SERVER:
        try:
            from broker.mt5_connector import MT5Connector
            broker = MT5Connector()
            if not broker.connect():
                logger.critical("MT5 connection failed — aborting")
                sys.exit(1)
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

    db = Database()
    state = StatePersistence(db, broker)
    news_filter = NewsFilter(db=db)

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

    # ── 3. Learning agent ───────────────────────────────────────────────
    learning = LearningAgent(db)

    # ── 4. Strategies ───────────────────────────────────────────────────
    strategies = [
        ICTStrategy(broker=broker, db=db, min_confidence=55.0),
        SmaCrossoverStrategy(),  # fallback
    ]

    # ── 5. Agents (db passed for persona events) ────────────────────────
    market_agent = MarketAgent(broker, db=db)
    analysis_agent = AnalysisAgent(news_filter, db=db)
    trade_manager = TradeManagerAgent(broker, state, db)
    risk_agent = RiskAgent(broker, trade_manager.get_open_trades, news_filter, db=db)
    strategy_agent = StrategyAgent(strategies, learning.get_confidence, db=db)
    execution_agent = ExecutionAgent(broker, state, risk_agent.calculate_position_size, db=db)

    # ── 6. Startup reconciliation ───────────────────────────────────────
    trade_manager.load_open_trades()
    trade_manager.reconcile()
    log_agent.record("STARTUP", f"Reconciliation done — {len(trade_manager.get_open_trades())} open trades")
    db.set_bot_uptime_start()

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

    telegram_bot.register_callbacks(None, _status_callback)
    telegram_bot.start_polling()
    telegram_bot.send_message("🤖 Trading bot started (DEMO)")

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

    while not _shutdown:
        loop_start = time.monotonic()
        loop_count += 1

        # ── Market hours: if ALL markets are closed, sleep longer ────────
        if not is_any_market_open(_active_symbols):
            if not _market_closed_logged:
                logger.info("All markets closed — sleeping (still processing commands & heartbeat)")
                _market_closed_logged = True
            # Still process commands and heartbeat
            _update_heartbeat(db, broker, trade_manager, learning)
            _process_commands(db, trade_manager)
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
            _run_iteration(
                loop_count=loop_count,
                market_agent=market_agent,
                analysis_agent=analysis_agent,
                strategy_agent=strategy_agent,
                risk_agent=risk_agent,
                execution_agent=execution_agent,
                trade_manager=trade_manager,
                learning=learning,
                log_agent=log_agent,
            )
        except Exception:
            logger.exception("Unhandled error in main loop iteration %d", loop_count)

        # ── Periodic reconciliation ──────────────────────────────────────
        if loop_count % settings.RECONCILE_EVERY_N_LOOPS == 0:
            trade_manager.reconcile()
            log_agent.record("RECONCILE", f"Periodic reconciliation (loop {loop_count})")

        # ── Bot status heartbeat ─────────────────────────────────────────
        _update_heartbeat(db, broker, trade_manager, learning)

        # ── Process UI command queue ─────────────────────────────────────
        _process_commands(db, trade_manager)

        # ── Daily summary ────────────────────────────────────────────────
        now = datetime.now(UTC)
        today_str = now.strftime("%Y-%m-%d")
        if (now.hour >= settings.DAILY_SUMMARY_HOUR
                and today_str != last_summary_date):
            report = learning.get_report()
            log_agent.send_daily_summary(report)
            last_summary_date = today_str

        # ── Time-corrected sleep ─────────────────────────────────────────
        elapsed = time.monotonic() - loop_start
        sleep_time = max(0, settings.LOOP_INTERVAL_SECONDS - elapsed)
        if sleep_time > 0:
            time.sleep(sleep_time)

    # ── 10. Shutdown ─────────────────────────────────────────────────────
    logger.info("Shutting down…")
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
            else:
                db.update_command(cmd["id"], "failed", f"Unknown command: {cmd_name}")
        except Exception as exc:
            db.update_command(cmd["id"], "failed", str(exc))


# ── Heartbeat updater ────────────────────────────────────────────────────

def _update_heartbeat(
    db: Database,
    broker: BrokerConnector,
    trade_manager: TradeManagerAgent,
    learning: LearningAgent,
) -> None:
    """Write current bot metrics to bot_status row."""
    equity = broker.get_equity()
    open_count = len(trade_manager.get_open_trades())
    report = learning.get_report()
    daily_pnl = report.get("total_pnl", 0.0)
    state = "paused" if telegram_bot.is_paused() else "running"
    db.update_bot_status(state, equity, open_count, daily_pnl)


def _run_iteration(
    *,
    loop_count: int,
    market_agent: MarketAgent,
    analysis_agent: AnalysisAgent,
    strategy_agent: StrategyAgent,
    risk_agent: RiskAgent,
    execution_agent: ExecutionAgent,
    trade_manager: TradeManagerAgent,
    learning: LearningAgent,
    log_agent: LoggingAgent,
) -> None:
    """Single iteration of the trading loop.

    Uses a **scan-all → rank → execute-best** pipeline:
    1. Scan every symbol and collect ALL signals from ALL strategies
    2. Rank by confidence (highest first)
    3. Execute top signals that pass risk validation (up to available slots)

    This ensures we never miss a high-confidence setup just because another
    symbol happened to be checked first in the list.
    """

    # ── Monitor existing trades first ────────────────────────────────────
    open_before = {t.id for t in trade_manager.get_open_trades()}
    trade_manager.monitor()
    open_after = {t.id for t in trade_manager.get_open_trades()}

    # ── Log newly closed trades to CSV + learning ────────────────────────
    just_closed_ids = open_before - open_after
    for trade_id in just_closed_ids:
        closed_trade = learning._db.get_trade(trade_id)
        if closed_trade:
            learning.review_trade(closed_trade)
            log_agent.log_trade_to_csv(closed_trade)
            log_agent.log_trade(closed_trade.id, "CLOSED",
                                f"{closed_trade.close_reason} PnL={closed_trade.pnl:.2f}")

    # ── Review any just-closed trades ────────────────────────────────────
    today_str = date.today().isoformat()
    all_closed_today = learning._db.get_trades_closed_today()
    # We only score trades that haven't been scored yet (score check in DB)
    # For simplicity, just score any closed trades from this iteration
    # The learning agent is idempotent per trade_id via DB constraint

    # ── Skip new signals if paused ───────────────────────────────────────
    if telegram_bot.is_paused():
        logger.debug("Bot paused — skipping signal detection (loop %d)", loop_count)
        return

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 1: Scan ALL symbols — collect every signal
    # ══════════════════════════════════════════════════════════════════════
    all_signals: list[Signal] = []

    for symbol in _active_symbols:
        # Skip symbols whose market is currently closed
        if not is_market_open(symbol):
            continue

        try:
            # Step 1: Fetch market data
            data = market_agent.get_data(symbol)
        except DataValidationError as e:
            logger.warning("Data validation failed for %s: %s — skipping", symbol, e)
            continue

        # Step 2: Analyse
        context = analysis_agent.analyze(data)

        # Step 3: Collect ALL signals from ALL strategies for this symbol
        signals = strategy_agent.detect_all(context)
        all_signals.extend(signals)

    if not all_signals:
        return

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 2: Rank by confidence (highest first) and deduplicate
    # ══════════════════════════════════════════════════════════════════════
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

    logger.info(
        "Signal scan: %d raw → %d ranked  [%s]",
        len(all_signals), len(ranked),
        ", ".join(f"{s.symbol} {s.direction} conf={s.confidence:.2f}" for s in ranked[:5]),
    )

    # ══════════════════════════════════════════════════════════════════════
    # PHASE 3: Execute best signals that pass risk validation
    # ══════════════════════════════════════════════════════════════════════
    for signal_obj in ranked:
        # Risk check (includes MAX_OPEN_TRADES — will naturally stop)
        if not risk_agent.validate(signal_obj):
            log_agent.log_risk_rejection(
                signal_obj.symbol, signal_obj.direction,
                signal_obj.strategy, "Failed risk validation")
            continue

        # Execute
        trade = execution_agent.open_trade(signal_obj)
        if trade is not None:
            trade_manager.add_trade(trade)
            log_agent.log_trade(trade.id, "OPENED",
                                f"{trade.direction} {trade.symbol} {trade.lot_size} lots")
            log_agent.log_trade_to_csv(trade)

            # Score will happen when trade closes (in trade_manager.monitor)


if __name__ == "__main__":
    main()
