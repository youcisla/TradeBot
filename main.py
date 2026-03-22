"""Trading Bot — main entry point.

Wires all agents, runs the time-corrected main loop, handles startup
reconciliation and graceful shutdown.

Phase 1 uses MockConnector + DEMO_MODE = True — fully runnable end-to-end.
"""

from __future__ import annotations

import concurrent.futures
import logging
import os
import signal
import sys
import time

# Enable ANSI colour codes on Windows CMD / PowerShell
if sys.platform == "win32":
    os.system("")  # activates VT100 processing for the current console
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
from models.market_data import MarketContext
from models.signal import Signal
# Rule-based strategies kept for Council confirmation logic (not used as primary generators)
# from strategies.sma_crossover import SmaCrossoverStrategy
# from strategies.ict_strategy import ICTStrategy

from agents.market_agent import MarketAgent
from agents.analysis_agent import AnalysisAgent
from agents.strategy_agent import StrategyAgent
from agents.risk_agent import RiskAgent
from agents.execution_agent import ExecutionAgent
from agents.trade_manager import TradeManagerAgent
from agents.learning_agent import LearningAgent
from agents.logging_agent import LoggingAgent
from agents.council_agent import CouncilAgent   # stays: confirms neural signals
from agents.model_manager import ModelManager
from agents.neural_strategy import NeuralStrategy

from utils import telegram_bot
from utils import candle_server
from utils import terminal_ui as tui
from utils.helpers import is_market_open, is_any_market_open
from utils.symbol_event_tracker import SymbolEventTracker

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

    # ── 1a. Symbol event tracker (global) ───────────────────────────────
    global symbol_event_tracker
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

    # ── 1b. Candle HTTP server for dashboard charts ──────────────────────
    candle_server.start(broker, db)

    # ── 2. Logging agent first (sets up Python logging) ─────────────────
    log_agent = LoggingAgent(db)
    log_agent.record("STARTUP", f"Bot started — DEMO_MODE={settings.DEMO_MODE}")

    # ── 3. Neural model manager (trains per-symbol LSTMs in background) ─
    model_manager = ModelManager(broker=broker)

    # ── 4. Learning agent ───────────────────────────────────────────────
    learning = LearningAgent(db, model_manager=model_manager)

    # ── 5. Strategies — Neural LSTM is the sole primary signal generator.
    #       ICT / SMA crossover are kept as files; the Council (below) still
    #       uses their logic via ICTExpert / TraditionalExpert for confirmation.
    neural_strategy = NeuralStrategy(model_manager)
    strategies = [neural_strategy]

    # ── 6. Agents (db passed for persona events) ────────────────────────
    market_agent = MarketAgent(broker, db=db)
    analysis_agent = AnalysisAgent(news_filter, db=db)
    trade_manager = TradeManagerAgent(broker, state, db)
    risk_agent = RiskAgent(broker, trade_manager.get_open_trades, news_filter, db=db)
    strategy_agent = StrategyAgent(strategies, learning.get_confidence, db=db)
    execution_agent = ExecutionAgent(broker, state, risk_agent.calculate_position_size, db=db)

    # ── Trading Council (optional algorithmic quality gate) ──────────────
    council: CouncilAgent | None = None
    if settings.COUNCIL_ENABLED:
        council = CouncilAgent()
        logger.info(
            "Trading Council ENABLED (min confidence: %.0f%%)",
            settings.COUNCIL_MIN_CONFIDENCE * 100,
        )
        log_agent.record(
            "STARTUP",
            "Trading Council is active — 3-expert algorithmic gate ON",
        )

    # ── 7. Startup reconciliation ───────────────────────────────────────
    trade_manager.load_open_trades()
    trade_manager.reconcile()
    log_agent.record("STARTUP", f"Reconciliation done — {len(trade_manager.get_open_trades())} open trades")
    db.set_bot_uptime_start()

    # ── 7b. Kick off neural model training / loading (background) ────────
    model_manager.initialize(_active_symbols)
    log_agent.record(
        "STARTUP",
        f"Neural LSTM training started for {len(_active_symbols)} symbols "
        f"(existing models load instantly; new ones train in background)",
    )

    # ── 7c. Terminal UI (Rich live dashboard) ───────────────────────────
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
    # Minimum wall-clock seconds between re-scanning the same symbol.
    # Set to 15 min so the ICT engine (which internally uses M15 candles)
    # gets fresh data every bar rather than being blocked until the next H1 close.
    _SCAN_COOLDOWN_S: float = 15 * 60  # 15 minutes
    _last_scan_ts: dict[str, float] = {}  # symbol → monotonic time of last analysis

    while not _shutdown:
        loop_start = time.monotonic()
        loop_count += 1

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
                council=council,
                last_scan_ts=_last_scan_ts,
                scan_cooldown=_SCAN_COOLDOWN_S,
            )
        except Exception:
            logger.exception("Unhandled error in main loop iteration %d", loop_count)

        # ── Periodic reconciliation ──────────────────────────────────────
        if loop_count % settings.RECONCILE_EVERY_N_LOOPS == 0:
            trade_manager.reconcile()
            log_agent.record("RECONCILE", f"Periodic reconciliation (loop {loop_count})")

        # ── Bot status heartbeat ─────────────────────────────────────────
        try:
            _update_heartbeat(db, broker, trade_manager, learning)
        except Exception:
            logger.warning("Heartbeat update failed — continuing")

        # ── Process UI command queue ─────────────────────────────────────
        _process_commands(db, trade_manager)

        # ── Daily summary ────────────────────────────────────────────────
        now = datetime.now(UTC)
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
    model_manager.shutdown()
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
    equity = _broker_call_safe(broker.get_equity, default=_hb_equity)
    balance = _broker_call_safe(broker.get_balance, default=_hb_balance)
    _hb_equity = equity
    _hb_balance = balance
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
    market_agent: MarketAgent,
    analysis_agent: AnalysisAgent,
    strategy_agent: StrategyAgent,
    risk_agent: RiskAgent,
    execution_agent: ExecutionAgent,
    trade_manager: TradeManagerAgent,
    learning: LearningAgent,
    log_agent: LoggingAgent,
    council: CouncilAgent | None,
    last_scan_ts: dict[str, float],
    scan_cooldown: float,
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
        closed_trade = learning._db.get_trade(trade_id)
        if closed_trade:
            close_time = getattr(closed_trade, 'close_time', None)
            ts = close_time.timestamp() if close_time and hasattr(close_time, 'timestamp') else time.time()
            symbol_event_tracker.update(closed_trade.symbol, "last_trade_close", ts)
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
    scanned: list[str] = []
    skipped_cooldown: list[str] = []

    for symbol in _active_symbols:
        if not is_market_open(symbol):
            continue
        if symbol in open_symbols:
            continue

        # Per-symbol cooldown — re-scan every 15 min (aligns with M15 bar)
        if now_mono - last_scan_ts.get(symbol, 0.0) < scan_cooldown:
            skipped_cooldown.append(symbol)
            continue
        last_scan_ts[symbol] = now_mono

        try:
            if _tui:
                _tui.set_agent_status("market", f"fetching {symbol}")
            data = market_agent.get_data(symbol)
        except DataValidationError as e:
            logger.warning("Data validation failed for %s: %s — skipping", symbol, e)
            continue

        if data.candles:
            symbol_event_tracker.update(symbol, "last_candle",
                                        data.candles[-1].timestamp.timestamp())
        scanned.append(symbol)

        if _tui:
            _tui.set_agent_status("analysis", f"analyzing {symbol}")
        context = analysis_agent.analyze(data)
        if _tui:
            _tui.set_agent_status("strategy", f"scanning {symbol}")
        signals = strategy_agent.detect_all(context)
        # Track last signal event per symbol
        if signals:
            symbol_event_tracker.update(symbol, "last_signal", time.time())
            if _tui:
                for sig in signals:
                    _tui.add_event("strategy", "info",
                                   f"{sig.direction} {sig.symbol} conf={sig.confidence:.0%}")
            # Store context keyed by signal id for council review later
            for sig in signals:
                signal_contexts[id(sig)] = context
        all_signals.extend(signals)

    if skipped_cooldown:
        logger.debug("Cooldown active for: %s", ", ".join(skipped_cooldown))
    if not scanned:
        logger.debug("Loop %d: all symbols on cooldown or skipped", loop_count)
        return
    if not all_signals:
        logger.info("Loop %d: scanned %s — no signals generated", loop_count, ", ".join(scanned))
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
    # PHASE 3: Execute best signals that pass council + risk validation
    # ══════════════════════════════════════════════════════════════════════
    for signal_obj in ranked:

        # ── Trading Council gate (3-expert algorithmic debate) ──────────
        if council is not None:
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
                        f"— {verdict.confidence:.0%} confidence\n{verdict.reasoning}"
                    )
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
        if not risk_agent.validate(signal_obj):
            log_agent.log_risk_rejection(
                signal_obj.symbol, signal_obj.direction,
                signal_obj.strategy, "Failed risk validation")
            if _tui:
                _tui.add_event("risk", "warn",
                               f"REJECT {signal_obj.symbol} {signal_obj.direction}")
            continue

        # Execute
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

            # Score will happen when trade closes (in trade_manager.monitor)

    if _tui:
        for name in ("market", "analysis", "strategy", "risk", "execution", "trade_mgr"):
            _tui.set_agent_idle(name)


if __name__ == "__main__":
    main()
