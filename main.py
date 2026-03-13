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

from broker.mock_connector import MockConnector
from config import settings
from config.symbols import SYMBOLS
from database.db import Database
from filters.data_validator import DataValidationError
from filters.news_filter import NewsFilter
from state.persistence import StatePersistence
from strategies.sma_crossover import SmaCrossoverStrategy

from agents.market_agent import MarketAgent
from agents.analysis_agent import AnalysisAgent
from agents.strategy_agent import StrategyAgent
from agents.risk_agent import RiskAgent
from agents.execution_agent import ExecutionAgent
from agents.trade_manager import TradeManagerAgent
from agents.learning_agent import LearningAgent
from agents.logging_agent import LoggingAgent

from utils import telegram_bot

logger = logging.getLogger(__name__)

# ── Global shutdown flag ────────────────────────────────────────────────
_shutdown = False


def _request_shutdown() -> None:
    global _shutdown
    _shutdown = True


def main() -> None:
    global _shutdown

    # ── 1. Core infrastructure ──────────────────────────────────────────
    broker = MockConnector()
    broker.connect()

    db = Database()
    state = StatePersistence(db, broker)
    news_filter = NewsFilter()

    # ── 2. Logging agent first (sets up Python logging) ─────────────────
    log_agent = LoggingAgent(db)
    log_agent.record("STARTUP", f"Bot started — DEMO_MODE={settings.DEMO_MODE}")

    # ── 3. Learning agent ───────────────────────────────────────────────
    learning = LearningAgent(db)

    # ── 4. Strategies ───────────────────────────────────────────────────
    strategies = [SmaCrossoverStrategy()]

    # ── 5. Agents ───────────────────────────────────────────────────────
    market_agent = MarketAgent(broker)
    analysis_agent = AnalysisAgent(news_filter)
    trade_manager = TradeManagerAgent(broker, state, db)
    risk_agent = RiskAgent(broker, trade_manager.get_open_trades, news_filter)
    strategy_agent = StrategyAgent(strategies, learning.get_confidence)
    execution_agent = ExecutionAgent(broker, state, risk_agent.calculate_position_size)

    # ── 6. Startup reconciliation ───────────────────────────────────────
    trade_manager.load_open_trades()
    trade_manager.reconcile()
    log_agent.record("STARTUP", f"Reconciliation done — {len(trade_manager.get_open_trades())} open trades")

    # ── 7. Telegram ─────────────────────────────────────────────────────
    def _kill_callback() -> None:
        trade_manager.close_all("KILL_SWITCH")
        _request_shutdown()

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

    telegram_bot.register_callbacks(_kill_callback, _status_callback)
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

    while not _shutdown:
        loop_start = time.monotonic()
        loop_count += 1

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
    broker.disconnect()
    db.close()
    log_agent.record("SHUTDOWN", "Bot stopped gracefully")
    logger.info("Goodbye.")


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
    """Single iteration of the trading loop."""

    # ── Monitor existing trades first ────────────────────────────────────
    trade_manager.monitor()

    # ── Review any just-closed trades ────────────────────────────────────
    closed = [t for t in trade_manager._open_trades if not t.is_open()]
    # (trade_manager already removed them, so check DB)
    today_str = date.today().isoformat()
    all_closed_today = learning._db.get_trades_closed_today()
    # We only score trades that haven't been scored yet (score check in DB)
    # For simplicity, just score any closed trades from this iteration
    # The learning agent is idempotent per trade_id via DB constraint

    # ── Skip new signals if paused ───────────────────────────────────────
    if telegram_bot.is_paused():
        logger.debug("Bot paused — skipping signal detection (loop %d)", loop_count)
        return

    # ── Per-symbol pipeline ──────────────────────────────────────────────
    for symbol in SYMBOLS:
        try:
            # Step 1: Fetch market data
            data = market_agent.get_data(symbol)
        except DataValidationError as e:
            logger.warning("Data validation failed for %s: %s — skipping", symbol, e)
            continue

        # Step 2: Analyse
        context = analysis_agent.analyze(data)

        # Step 3: Detect signal
        signal_obj = strategy_agent.detect(context)
        if signal_obj is None:
            continue

        # Step 4: Risk check
        if not risk_agent.validate(signal_obj):
            continue

        # Step 5: Execute
        trade = execution_agent.open_trade(signal_obj)
        if trade is not None:
            trade_manager.add_trade(trade)
            log_agent.log_trade(trade.id, "OPENED",
                                f"{trade.direction} {trade.symbol} {trade.lot_size} lots")

            # Score will happen when trade closes (in trade_manager.monitor)


if __name__ == "__main__":
    main()
