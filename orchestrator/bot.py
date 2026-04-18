"""TradingBot — extracted from main.py's main() loop."""

from __future__ import annotations

import logging
import signal
import sys
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from broker.connector import BrokerConnector
from config import settings
from config.symbols import SYMBOLS

from database.db import Database
from state.persistence import StatePersistence
from strategies.ict_strategy import ICTStrategy
from strategies.unified_strategy import UnifiedStrategy
from strategies.plugin_loader import load_strategy_plugins

from agents.market_agent import MarketAgent
from agents.analysis_agent import AnalysisAgent
from agents.strategy_agent import StrategyAgent
from agents.risk_agent import RiskAgent
from agents.execution_agent import ExecutionAgent
from agents.trade_manager import TradeManagerAgent
from agents.learning_agent import LearningAgent
from agents.logging_agent import LoggingAgent
from agents.reflector import Reflector
from agents.crucix_agent import CrucixAgent
from agents.sniper_entry_guard import SniperEntryGuard
from agents.hku_client import HKUClient
from agents.hku_copy_trader import HKUCopyTradingService, CopyTradeConfig
from agents.ssrt_agent import SSRTAgent

from utils import telegram_bot
from utils import candle_server
from utils import terminal_ui as tui
from utils.helpers import (
    current_session,
    is_any_market_open,
    is_weekend,
    local_now,
)
from utils.spread_monitor import SpreadMonitor
from utils.orchestration_profiler import OrchestrationProfiler, OrchestrationTargets
from utils.symbol_event_tracker import SymbolEventTracker
from utils.opportunity_lifecycle import OpportunityLifecycleManager
from utils.telegram_reports import build_pnl_curve_png
from utils.tool_system import AutonomousToolSystem

from orchestrator.heartbeat import HeartbeatManager
from orchestrator.commands import process_commands
from orchestrator.iteration import run_iteration

logger = logging.getLogger(__name__)


class TradingBot:
    """Wires all agents and runs the time-corrected main loop."""

    def __init__(self) -> None:
        self._shutdown = False
        self._session_id: int = 0
        self._spread_monitor: SpreadMonitor | None = None

        # ── Initialized in startup() ──────────────────────────────────────
        self.db: Database | None = None
        self.broker: BrokerConnector | None = None
        self.state: StatePersistence | None = None
        self.crucix_agent: CrucixAgent | None = None
        self.market_agent: MarketAgent | None = None
        self.analysis_agent: AnalysisAgent | None = None
        self.risk_agent: RiskAgent | None = None
        self.execution_agent: ExecutionAgent | None = None
        self.trade_manager: TradeManagerAgent | None = None
        self.strategy_agent: StrategyAgent | None = None
        self.weekend_strategy_agent: StrategyAgent | None = None
        self.learning: LearningAgent | None = None
        self.log_agent: LoggingAgent | None = None
        self.reflector: Reflector | None = None
        self.sniper_guard: SniperEntryGuard | None = None
        self.tool_system: AutonomousToolSystem | None = None
        self.opportunity_lifecycle: OpportunityLifecycleManager | None = None
        self.symbol_event_tracker: SymbolEventTracker | None = None
        self.heartbeat: HeartbeatManager | None = None
        self.hku_client: "HKUClient | None" = None
        self.ssrt_agent: SSRTAgent | None = None
        self._active_symbols: list[str] = []
        self._weekend_symbols: list[str] = []

    def _request_shutdown(self) -> None:
        self._shutdown = True

    # ── Lifecycle ───────────────────────────────────────────────────────

    def startup(self) -> None:
        """Everything in main() before the while loop."""
        # ── Core infrastructure ──────────────────────────────────────────
        db = Database()
        self.db = db
        self.symbol_event_tracker = SymbolEventTracker()

        # Resolve broker credentials: DB active account → .env fallback
        acct_id: int | None = None
        db_account = db.get_active_broker_account()
        if db_account:
            acct_num = db_account["account_number"]
            acct_pwd = db_account["password"]
            acct_srv = db_account["server"]
            acct_id = db_account["id"]
            logger.info("Using DB broker account: %s @ %s (id=%d)",
                        acct_num, acct_srv, acct_id)
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
                if acct_id:
                    db.mark_broker_connected(acct_id)
            except ImportError as exc:
                logger.critical(
                    "MetaTrader5 package not available — cannot run with real data. "
                    "Install it or ensure your Python environment supports MT5. Error: %s",
                    exc,
                )
                sys.exit(1)
        else:
            logger.critical(
                "Missing broker credentials — set BROKER_ACCOUNT, BROKER_PASSWORD, "
                "and BROKER_SERVER (or configure an active account in the database). "
                "Cannot run with real data."
            )
            sys.exit(1)

        self.broker = broker
        self.state = StatePersistence(db, broker)
        self.crucix_agent = CrucixAgent(db=db)

        self._spread_monitor = SpreadMonitor(
            threshold_low=1.0,
            threshold_normal=2.0,
            threshold_high=5.0,
            pip_size=0.0001,
        )

        # ── Filter symbols to those available on the broker ─────────────────
        if hasattr(broker, "get_available_symbols"):
            self._active_symbols = broker.get_available_symbols(SYMBOLS)
            removed = set(SYMBOLS) - set(self._active_symbols)
            if removed:
                logger.warning("Symbols not available on broker (removed): %s", ", ".join(sorted(removed)))
        else:
            self._active_symbols = SYMBOLS[:]
        logger.info("Active symbols: %s", ", ".join(self._active_symbols))

    def _write_symbols_manifest(self) -> None:
        """Export active symbols + categories to data/symbols.json.

        Consumed by the Next.js GET /api/symbols endpoint.
        """
        import json
        import pathlib

        from config.symbols import (
            FOREX_MAJORS, FOREX_CROSSES, FOREX_S_SUFFIX,
            COMMODITIES, INDICES,
        )

        categories = [
            {"id": "forex-majors",  "label": "Forex Majors",   "symbols": FOREX_MAJORS},
            {"id": "forex-crosses", "label": "Forex Crosses",  "symbols": FOREX_CROSSES},
            {"id": "forex-s",       "label": "Forex (.s)",     "symbols": FOREX_S_SUFFIX},
            {"id": "commodities",    "label": "Commodities",    "symbols": COMMODITIES},
            {"id": "indices",        "label": "Indices",        "symbols": INDICES},
        ]

        payload = {
            "categories": categories,
            "all": self._active_symbols,
        }

        path = Path(__file__).resolve().parent.parent / "data" / "symbols.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            logger.info("symbols.json written: %d symbols", len(self._active_symbols))
        except Exception as exc:
            logger.warning("Failed to write symbols.json: %s", exc)

        # ── Logging agent first (sets up Python logging) ─────────────────
        log_agent = LoggingAgent(self.db)
        self.log_agent = log_agent
        log_agent.record("STARTUP", f"Bot started — DEMO_MODE={settings.DEMO_MODE}")

        # ── Crucix intelligence layer ────────────────────────────────────
        _startup_macro = self.crucix_agent.get_context()
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

        # ── Candle HTTP server for dashboard charts ──────────────────────
        candle_server.start(self.broker, self.db)

        # ── Learning agent + post-trade Reflector ─────────────────────────
        learning = LearningAgent(self.db, hku_client=None)
        self.learning = learning
        self.ssrt_agent = SSRTAgent(self.db)
        reflector = Reflector()
        self.reflector = reflector
        learning.set_reflector(reflector)

        # ── ICT-only unified strategy ────────────────────────────────────
        ict_strategy = ICTStrategy(broker=self.broker, db=self.db, min_confidence=35.0)
        plugin_strategies = load_strategy_plugins(db=self.db, broker=self.broker)
        base_strategies = [ict_strategy]
        unified_strategy = UnifiedStrategy(base_strategies + plugin_strategies)
        strategies = [unified_strategy]
        if plugin_strategies:
            logger.info(
                "Unified strategy mode: ICT-only + %d plugin(s)",
                len(plugin_strategies),
            )
        else:
            logger.info("Unified strategy mode: ICT-only")

        # ── Weekend crypto strategies ────────────────────────────────────
        ict_btc_h1d1 = ICTStrategy(
            broker=self.broker, db=self.db, min_confidence=35.0,
            htf_timeframe="D1", htf_candle_count=100,
            entry_timeframe="H1", entry_candle_count=200,
        )
        ict_btc_h4w1 = ICTStrategy(
            broker=self.broker, db=self.db, min_confidence=35.0,
            htf_timeframe="W1", htf_candle_count=52,
            entry_timeframe="H4", entry_candle_count=150,
        )
        weekend_unified_strategy = UnifiedStrategy([
            ict_btc_h4w1,
            ict_strategy,
            ict_btc_h1d1,
            *plugin_strategies,
        ])
        weekend_strategies = [weekend_unified_strategy]

        self._weekend_symbols = [
            s.strip() for s in settings.WEEKEND_SYMBOLS.split(",") if s.strip()
        ]

        # ── Agents ────────────────────────────────────────────────────────
        market_agent = MarketAgent(self.broker, db=self.db)
        self.market_agent = market_agent
        analysis_agent = AnalysisAgent(self.crucix_agent, db=self.db)
        self.analysis_agent = analysis_agent

        # trade_manager must be created BEFORE risk_agent so that
        # risk_agent.calculate_position_size binds to the real get_open_trades
        trade_manager = TradeManagerAgent(self.broker, self.state, self.db, guard_pipeline=None)
        risk_agent = RiskAgent(self.broker, trade_manager.get_open_trades, self.crucix_agent, db=self.db)
        execution_agent = ExecutionAgent(self.broker, self.state, risk_agent.calculate_position_size, db=self.db)
        # Now wire guard_pipeline (guards need execution_agent's guard_pipeline)
        trade_manager = TradeManagerAgent(self.broker, self.state, self.db, guard_pipeline=execution_agent.guard_pipeline)
        self.risk_agent = risk_agent
        self.execution_agent = execution_agent
        self.trade_manager = trade_manager
        self.strategy_agent = StrategyAgent(strategies, learning.get_confidence, db=self.db)
        self.weekend_strategy_agent = StrategyAgent(weekend_strategies, learning.get_confidence, db=self.db)

        # ── Warmup ML models ───────────────────────────────────────────────
        self._warmup_models(learning)

        # ── Tool system ───────────────────────────────────────────────────
        def _get_active_symbols_local() -> list[str]:
            return self._active_symbols[:]

        def _set_active_symbols_local(new_symbols: list[str]) -> None:
            self._active_symbols = new_symbols[:]
            logger.warning("Tool system updated active symbols: %s", ", ".join(self._active_symbols))
            self._write_symbols_manifest()

        tool_system = AutonomousToolSystem(
            repo_root=Path(__file__).resolve().parent.parent,
            db=self.db,
            broker=self.broker,
            trade_manager=trade_manager,
            risk_agent=risk_agent,
            get_active_symbols=_get_active_symbols_local,
            set_active_symbols=_set_active_symbols_local,
            base_symbols=self._active_symbols[:],
        )
        self.tool_system = tool_system
        self.opportunity_lifecycle = OpportunityLifecycleManager()

        # ── Sniper Entry Guard ────────────────────────────────────────────
        sniper_guard: SniperEntryGuard | None = None
        if settings.SNIPER_ENTRY_ENABLED:
            sniper_guard = SniperEntryGuard(
                broker=self.broker,
                db=self.db,
                threshold=settings.SNIPER_CONF_THRESHOLD,
                timeout_minutes=settings.SNIPER_TIMEOUT_MINUTES,
                max_entry_atr_distance=settings.SNIPER_MAX_ENTRY_ATR_DISTANCE,
                fib_min_depth=settings.SNIPER_FIB_MIN_DEPTH,
                fib_max_depth=settings.SNIPER_FIB_MAX_DEPTH,
            )
            logger.info(
                "SniperEntryGuard ENABLED (threshold=%.0f%%, timeout=%.0fmin, "
                "fib_depth=[%s–%s])",
                settings.SNIPER_CONF_THRESHOLD * 100,
                settings.SNIPER_TIMEOUT_MINUTES,
                settings.SNIPER_FIB_MIN_DEPTH,
                settings.SNIPER_FIB_MAX_DEPTH,
            )
            log_agent.record(
                "STARTUP",
                f"SniperEntryGuard ENABLED — threshold={settings.SNIPER_CONF_THRESHOLD:.0%} "
                f"timeout={settings.SNIPER_TIMEOUT_MINUTES:.0f}min "
                f"fib=[{settings.SNIPER_FIB_MIN_DEPTH},{settings.SNIPER_FIB_MAX_DEPTH}]",
            )
        else:
            logger.info("SniperEntryGuard DISABLED")
            log_agent.record("STARTUP", "SniperEntryGuard DISABLED")
        self.sniper_guard = sniper_guard

        # ── HKU Marketplace client ───────────────────────────────────────
        self.hku_client: HKUClient | None = None
        self.copy_trader: HKUCopyTradingService | None = None
        if settings.HKU_ENABLED:
            self.hku_client = HKUClient(
                base_url=settings.HKU_API_URL,
                api_key=settings.HKU_API_KEY,
                db=self.db,
            )
            if self.hku_client.register_if_needed():
                logger.info("HKU agent registered: agent_id=%s", self.hku_client._agent_id)
                learning.set_hku_client(self.hku_client)
                # Start heartbeat (keeps registration alive + maintains WebSocket)
                self.hku_client.start_heartbeat()
                # Wire up copy trading if enabled
                if settings.HKU_COPY_TRADING_ENABLED:
                    self.copy_trader = HKUCopyTradingService(
                        hku_client=self.hku_client,
                        broker=self.broker,
                        config=CopyTradeConfig(
                            enabled=True,
                            margin_fraction_per_trade=settings.HKU_COPY_MARGIN_FRACTION,
                            max_copy_trades=settings.HKU_COPY_MAX_TRADES,
                            min_leader_winrate=settings.HKU_COPY_MIN_WINRATE,
                            sl_atr_multiples=settings.HKU_COPY_SL_ATR,
                            tp_atr_multiples=settings.HKU_COPY_TP_ATR,
                        ),
                    )
                    self.copy_trader.start()
                    # Follow configured leader agents
                    for leader_id in settings.HKU_COPY_LEADER_IDS:
                        if self.hku_client.follow_agent(leader_id):
                            logger.info("HKU following leader: %s", leader_id)
                    log_agent.record("STARTUP", f"HKU copy trading ENABLED ({len(settings.HKU_COPY_LEADER_IDS)} leaders)")
            else:
                logger.warning("HKU registration failed — marketplace features disabled")
                self.hku_client = None
        else:
            logger.info("HKU marketplace integration disabled")

        # ── Startup reconciliation ──────────────────────────────────────
        trade_manager.load_open_trades()
        trade_manager.reconcile()
        log_agent.record("STARTUP", f"Reconciliation done — {len(trade_manager.get_open_trades())} open trades")
        self.db.set_bot_uptime_start()
        self._session_id = self.db.start_session(version=getattr(settings, "VERSION", ""))
        log_agent.record("STARTUP", f"Session started — id={self._session_id}")

        # ── Heartbeat manager ─────────────────────────────────────────────
        self.heartbeat = HeartbeatManager(
            db=self.db,
            broker=self.broker,
            spread_monitor=self._spread_monitor,
            guard_pipeline=execution_agent.guard_pipeline,
        )

        # ── Terminal UI ──────────────────────────────────────────────────
        _ui = tui.init(refresh_per_second=4)
        _ui.set_bot_status("STARTING", open_trades=len(trade_manager.get_open_trades()))

        # ── Telegram ─────────────────────────────────────────────────────
        def _status_callback() -> str:
            equity = broker.get_equity()
            balance = broker.get_balance()
            open_count = len(trade_manager.get_open_trades())
            mt5_restarts = getattr(broker, "connection_count", 0)
            return (
                "📡 Live Bot Status\n"
                f"Balance: {balance:.2f} | Equity: {equity:.2f}\n"
                f"Open trades: {open_count}\n"
                f"MT5 restarts: {mt5_restarts}\n"
                f"Loop interval: {settings.LOOP_INTERVAL_SECONDS}s\n"
                f"Demo mode: {settings.DEMO_MODE}"
            )

        def _graph_callback() -> tuple[str, bytes] | None:
            return build_pnl_curve_png(db, days=settings.TELEGRAM_CHART_DAYS)

        telegram_bot.register_callbacks(None, _status_callback, _graph_callback)
        telegram_bot.start_polling()
        telegram_bot.send_message(
            "🚀 Bot startup complete\n"
            "Mode: DEMO\n"
            f"Active symbols: {len(self._active_symbols)}\n"
            "Type /status or /graph any time.",
            priority="high",
            force=True,
        )

        # ── Signal handlers ───────────────────────────────────────────────
        signal.signal(signal.SIGINT, self._sig_handler)
        signal.signal(signal.SIGTERM, self._sig_handler)

    def _sig_handler(self, signum: int, frame: object) -> None:
        logger.info("Signal %d received — shutting down", signum)
        self._request_shutdown()

    def _log_status(
        self,
        loop_count: int,
        metrics: dict[str, float],
        scan_workers: int,
        session: str,
        profiler: OrchestrationProfiler,
    ) -> None:
        """Structured periodic status dump (gabagool pattern)."""
        open_trades = len(self.trade_manager.get_open_trades()) if self.trade_manager else 0
        equity = self.broker.get_equity() if self.broker else 0.0
        balance = self.broker.get_balance() if self.broker else 0.0
        profile = profiler.snapshot()
        win_rate = 0.0
        total_trades = 0
        try:
            stats = self.db.get_performance_stats() if self.db else {}
            total_trades = stats.get("total_trades", 0)
            win_rate = stats.get("win_rate", 0.0)
        except Exception:
            pass
        logger.info("-" * 50)
        logger.info("STATUS UPDATE @loop %d", loop_count)
        logger.info(
            "  Trades: %d open | %d total | %.1f%% win rate",
            open_trades,
            total_trades,
            win_rate * 100,
        )
        logger.info(
            "  Balance: $%.2f | Equity: $%.2f",
            balance,
            equity,
        )
        logger.info(
            "  Session: %s | Cooldown: %.0fs | Workers: %d",
            session,
            0,  # placeholder — available from closure if needed
            scan_workers,
        )
        logger.info(
            "  Latency: scan=%.1fms rank=%.1fms exec=%.1fms total=%.1fms",
            metrics.get("last_scan_latency_ms", 0),
            metrics.get("last_rank_latency_ms", 0),
            metrics.get("last_execution_latency_ms", 0),
            profile.get("avg_total_ms", 0),
        )
        logger.info("-" * 50)

    def _warmup_models(self, learning: LearningAgent) -> None:
        """Eagerly load all ML/prediction models at startup."""
        _t0 = time.monotonic()
        _loaded: list[str] = []
        _skipped: list[str] = []

        if settings.LGBM_ENSEMBLE_ENABLED:
            from models.lgbm_ensemble import LGBMEnsemble
            _ens = LGBMEnsemble()
            if _ens.is_ready:
                _loaded.append(f"lgbm_ensemble (trained)")
                logger.info("LGBM ensemble ready at startup (shap features: %d)",
                            len(_ens.get_shap_importance()))
            else:
                _skipped.append("lgbm_ensemble (not trained)")
                logger.warning("LGBM ensemble not ready at startup — will train on demand")

            from models.lgbm_price_model import LGBMPriceModel
            _price = LGBMPriceModel()
            _trained_syms = _price.symbols_trained()
            if _trained_syms:
                _loaded.append(f"lgbm_price ({len(_trained_syms)} symbols: {', '.join(_trained_syms[:8])}{'...' if len(_trained_syms) > 8 else ''})")
                logger.info("LGBM price models ready at startup: %d symbols", len(_trained_syms))
            else:
                _skipped.append("lgbm_price (no trained symbols)")
                logger.info("No LGBM price models at startup — will train on demand")

            # Pre-initialize the StrategyAgent lazy singleton
            _ = self.strategy_agent._lgbm   # noqa: F841 — triggers lazy init
            _loaded.append("strategy_agent.lgbm_singleton")
            logger.info("StrategyAgent LGBM singleton initialized")
        else:
            logger.info("LGBM models skipped at startup (LGBM_ENSEMBLE_ENABLED=false)")
            _skipped.append("lgbm (disabled)")

        if settings.KALMAN_ENABLED:
            _loaded.append("kalman (stateless)")
            logger.info("Kalman filter enabled (stateless, no warmup needed)")

        if settings.GARCH_ENABLED:
            _loaded.append("garch_regime (on-demand per symbol)")
            logger.info("GARCH regime detection enabled (initializes on first candle)")

        _elapsed = time.monotonic() - _t0
        _msg = f"Model warmup complete in {_elapsed*1000:.1f}ms — loaded: {', '.join(_loaded) if _loaded else 'none'}"
        if _skipped:
            _msg += f" | skipped: {', '.join(_skipped)}"
            # Surface degraded ML readiness to operator via Telegram
            try:
                telegram_bot.send_message(
                    f"⚠️ Model warmup incomplete\n"
                    f"Failed to load: {', '.join(_skipped)}\n"
                    f"Bot continues but ML accuracy may be reduced.",
                    priority="high",
                    force=False,
                )
            except Exception:
                pass
            self.log_agent.record("STARTUP", _msg, level="WARNING")
            logger.warning(_msg)
        else:
            logger.info(_msg)
            self.log_agent.record("STARTUP", _msg)

    def run(self) -> None:
        """Main loop — everything after startup() before shutdown()."""
        if self.db is None or self.broker is None:
            raise RuntimeError("TradingBot.startup() must be called before run()")

        # ── Write symbols manifest for Next.js dashboard ─────────────────────
        self._write_symbols_manifest()

        loop_count = 0
        last_summary_date = ""
        logger.info("Entering main loop (interval=%ds)", settings.LOOP_INTERVAL_SECONDS)

        _market_closed_logged = False
        _last_mt5_sync_ts: float = 0.0
        _last_scan_ts: dict[str, float] = {}
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
            "risk_soft_rejections": 0,
            "budget_scan_hits": 0,
            "budget_rank_hits": 0,
            "budget_exec_hits": 0,
            "budget_iteration_hits": 0,
            "budget_council_skips": 0,
            "last_scan_latency_ms": 0.0,
            "last_rank_latency_ms": 0.0,
            "last_execution_latency_ms": 0.0,
            "last_signal_to_order_ms": -1.0,
        }
        _risk_reject_reason_counts: dict[str, int] = {}
        profiler = OrchestrationProfiler(
            OrchestrationTargets(
                scan_ms=settings.ORCHESTRATION_TARGET_SCAN_MS,
                rank_ms=settings.ORCHESTRATION_TARGET_RANK_MS,
                exec_ms=settings.ORCHESTRATION_TARGET_EXEC_MS,
                total_ms=settings.ORCHESTRATION_TARGET_TOTAL_MS,
            )
        )
        scan_workers = settings.ORCHESTRATION_SCAN_WORKERS_DEFAULT
        _base_cooldown = 0  # set each loop before passing to run_iteration
        _active_scan_cooldown = 0.0  # computed from base cooldown + worker ratio

        # ── Symbol fault tracking ────────────────────────────────────────
        _symbol_fail_count: dict[str, int] = {}
        _symbol_disabled_until: dict[str, float] = {}

        # ── Session brief tracking ─────────────────────────────────────────
        _brief_sent_minutes: set[str] = set()   # "session:YYYYMMDDHHMM" deduplication

        try:
            _now_utc = datetime.now(UTC)
            _now_mono = time.monotonic()
            _stale_cleared = 0
            for _sym, _fault in self.db.load_symbol_faults().items():
                _disabled_until = _fault["disabled_until"]
                if _disabled_until is not None:
                    _remaining = (_disabled_until - _now_utc).total_seconds()
                    if _remaining > 0:
                        # cooldown still active — carry both fail_count and remaining time
                        _symbol_fail_count[_sym] = _fault["fail_count"]
                        _symbol_disabled_until[_sym] = _now_mono + _remaining
                        logger.info("Restored fault state for %s — disabled for %.0fs more", _sym, _remaining)
                    else:
                        # cooldown expired — give symbol a clean slate, don't carry fail_count forward
                        _stale_cleared += 1
                else:
                    # no disable record — preserve the historical fail_count
                    _symbol_fail_count[_sym] = _fault["fail_count"]
            if _stale_cleared:
                logger.info("Cleared %d stale symbol_fault row(s) with expired cooldown — fail counters reset", _stale_cleared)
        except Exception:
            logger.warning("Could not load symbol fault state from DB — starting fresh")

        def _should_send_brief(now_utc: datetime, session: str) -> bool:
            """Fire once per session open, 5 minutes before."""
            triggers = {"london": (7, 55), "newyork": (12, 55)}
            target = triggers.get(session.lower())
            if not target:
                return False
            key = f"{session}:{now_utc.strftime('%Y%m%d%H%M')}"
            if now_utc.hour == target[0] and now_utc.minute == target[1] and key not in _brief_sent_minutes:
                _brief_sent_minutes.add(key)
                return True
            return False

        def _send_session_brief(session: str) -> None:
            try:
                from agents.briefing_agent import generate_brief
                brief = generate_brief(session)
                telegram_bot.send_message(
                    f"📊 *{session.upper()} SESSION BRIEF*\n\n{brief}",
                    priority="high",
                    dedupe_key=f"brief:{session}",
                )
            except Exception as exc:
                logger.warning("BriefingAgent failed: %s", exc)

        while not self._shutdown:
            # ── KILL file sentinel — emergency stop ───────────────────────────
            _kill_file = Path(__file__).resolve().parent.parent / "KILL"
            if _kill_file.exists():
                logger.critical("KILL file detected — emergency shutdown")
                try:
                    _kill_file.unlink()
                except Exception:
                    pass
                self.trade_manager.close_all("KILL_FILE")
                try:
                    telegram_bot.send_message("KILL file — all positions closed, shutting down.")
                except Exception:
                    pass
                self._request_shutdown()
                continue

            loop_start = time.monotonic()
            loop_count += 1
            scanned_before = _metrics.get("scanned_symbols", 0)
            _active_session = current_session(datetime.now(UTC))
            if _should_send_brief(datetime.now(UTC), _active_session):
                threading.Thread(
                    target=_send_session_brief,
                    args=(_active_session,),
                    daemon=True,
                    name="session-brief",
                ).start()
            if _active_session in {"london", "newyork", "overlap"}:
                _base_cooldown = float(settings.SCAN_COOLDOWN_SECONDS_LONDON_NY)
            else:
                _base_cooldown = float(settings.SCAN_COOLDOWN_SECONDS_ASIA)

            # ── Market hours: if ALL markets are closed, sleep longer ────────
            if not is_any_market_open(self._active_symbols):
                if not _market_closed_logged:
                    logger.info("All markets closed — sleeping (still processing commands & heartbeat)")
                    _market_closed_logged = True
                process_commands(
                    self.db, self.trade_manager,
                    self._request_shutdown, self.tool_system, self.state,
                )
                _intervals = settings.MARKET_CLOSED_SLEEP_TOTAL_SECONDS // settings.MARKET_CLOSED_SLEEP_INTERVAL_SECONDS
                for _ in range(_intervals):
                    if self._shutdown or telegram_bot.is_kill_requested():
                        break
                    time.sleep(settings.MARKET_CLOSED_SLEEP_INTERVAL_SECONDS)
                continue
            elif _market_closed_logged:
                logger.info("Markets reopened — resuming normal operation")
                _market_closed_logged = False

            try:
                _weekend = is_weekend()
                delta = run_iteration(
                    loop_count=loop_count,
                    active_symbols=self._active_symbols,
                    db=self.db,
                    broker=self.broker,
                    crucix_agent=self.crucix_agent,
                    market_agent=self.market_agent,
                    analysis_agent=self.analysis_agent,
                    strategy_agent=self.weekend_strategy_agent if _weekend else self.strategy_agent,
                    risk_agent=self.risk_agent,
                    execution_agent=self.execution_agent,
                    trade_manager=self.trade_manager,
                    learning=self.learning,
                    log_agent=self.log_agent,
                    sniper_guard=self.sniper_guard,
                    ssrt_agent=self.ssrt_agent,
                    symbol_event_tracker=self.symbol_event_tracker,
                    hku_client=self.hku_client,
                    last_scan_ts=_last_scan_ts,
                    scan_cooldown=_active_scan_cooldown,
                    deferred_entries=_deferred_entries,
                    metrics=_metrics,
                    symbol_fail_count=_symbol_fail_count,
                    symbol_disabled_until=_symbol_disabled_until,
                    symbol_max_fails=settings.SYMBOL_MAX_FAIL_COUNT,
                    symbol_disable_secs=float(settings.SYMBOL_DISABLE_SECONDS),
                    session_profile=_active_session,
                    opportunity_lifecycle=self.opportunity_lifecycle,
                    weekend_symbols=self._weekend_symbols if _weekend else None,
                    scan_workers=settings.ORCHESTRATION_SCAN_WORKERS_DEFAULT,
                    risk_reject_reason_counts=_risk_reject_reason_counts,
                )
                delta.merge_into(_metrics)
                _metrics["iter_consecutive_failures"] = 0
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception:
                _metrics["iter_consecutive_failures"] = _metrics.get("iter_consecutive_failures", 0) + 1
                _fail_count = _metrics["iter_consecutive_failures"]
                logger.exception("Unhandled error in main loop iteration %d (consecutive=%d)", loop_count, _fail_count)
                if _fail_count >= 3:
                    logger.error("CRITICAL: %d consecutive main-loop failures — consider pausing the bot", _fail_count)
                    self.log_agent.record("CRITICAL", f"{_fail_count} consecutive loop failures")
                    if _fail_count >= 5:
                        logger.warning("Multiple failures, backing off 30s before retry…")
                        time.sleep(30)

            loop_elapsed_ms = time.monotonic() - loop_start
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

            # ── Cooldown scales inversely with worker count ─────────────────
            # More workers → symbols scanned faster → shorter cooldown needed
            _default_workers = settings.ORCHESTRATION_SCAN_WORKERS_DEFAULT
            _worker_ratio = _default_workers / max(scan_workers, 1)
            _active_scan_cooldown = _base_cooldown * _worker_ratio

            # ── Periodic reconciliation ──────────────────────────────────
            if loop_count % settings.RECONCILE_EVERY_N_LOOPS == 0:
                try:
                    orphan_tickets = self.state.scan_orphans()
                    if orphan_tickets:
                        logger.warning(
                            "Orphan scan: %d unknown position(s) — tickets: %s",
                            len(orphan_tickets),
                            orphan_tickets,
                        )
                        self.log_agent.record(
                            "ORPHAN_SCAN",
                            f"Detected {len(orphan_tickets)} orphan(s) — tickets: {orphan_tickets}",
                        )
                except Exception:
                    logger.warning("Orphan scan failed")
                self.trade_manager.reconcile()
                self.log_agent.record("RECONCILE", f"Periodic reconciliation (loop {loop_count})")

            # ── Bot status heartbeat ─────────────────────────────────────
            try:
                self.heartbeat.update(
                    trade_manager=self.trade_manager,
                    crucix_agent=self.crucix_agent,
                )
            except Exception as e:
                logger.warning("Heartbeat update failed — continuing: %s", e)

            # ── Periodic MT5 → DB sync ───────────────────────────────────
            if settings.MT5_DB_SYNC_INTERVAL_SECONDS > 0:
                now_mono = time.monotonic()
                if now_mono - _last_mt5_sync_ts >= settings.MT5_DB_SYNC_INTERVAL_SECONDS:
                    _last_mt5_sync_ts = now_mono
                    try:
                        self.state.sync_mt5_to_db()
                    except Exception:
                        logger.warning("MT5→DB sync failed — continuing", exc_info=True)

            if settings.METRICS_LOG_EVERY_N_LOOPS > 0 and loop_count % settings.METRICS_LOG_EVERY_N_LOOPS == 0:
                profile = profiler.snapshot()
                bottleneck = profiler.primary_bottleneck()
                logger.info(
                    "KPI snapshot @loop %d | scanned=%d raw=%d ranked=%d council_rej=%d risk_rej=%d "
                    "risk_soft_rej=%d fast_attempts=%d fast_fills=%d fast_closed=%d full_fills=%d deferred_added=%d deferred_promoted=%d "
                    "budget_scan=%d budget_rank=%d budget_exec=%d budget_iter=%d budget_council_skips=%d "
                    "session=%s cooldown=%.0fs scan_ms=%.1f rank_ms=%.1f exec_ms=%.1f signal_to_order_ms=%.1f "
                    "avg_scan=%.1f avg_rank=%.1f avg_exec=%.1f avg_total=%.1f workers=%d bottleneck=%s",
                    loop_count,
                    _metrics["scanned_symbols"],
                    _metrics["raw_signals"],
                    _metrics["ranked_signals"],
                    _metrics["council_rejections"],
                    _metrics["risk_rejections"],
                    _metrics["risk_soft_rejections"],
                    _metrics["fast_lane_attempts"],
                    _metrics["fast_lane_fills"],
                    _metrics["fast_lane_closed"],
                    _metrics["full_lane_fills"],
                    _metrics["deferred_added"],
                    _metrics["deferred_promoted"],
                    _metrics["budget_scan_hits"],
                    _metrics["budget_rank_hits"],
                    _metrics["budget_exec_hits"],
                    _metrics["budget_iteration_hits"],
                    _metrics["budget_council_skips"],
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
                self.db.log_agent_event(
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
                        "risk_reject_reason_counts": dict(_risk_reject_reason_counts),
                    },
                )

            # ── Periodic structured status (gabagool pattern every 100 loops) ──
            if loop_count > 0 and loop_count % 100 == 0:
                self._log_status(loop_count, _metrics, scan_workers, _active_session, profiler)

            if (
                settings.TOOL_SYSTEM_ENABLED
                and settings.TOOL_SYSTEM_AUTORUN_EVERY_N_LOOPS > 0
                and loop_count % settings.TOOL_SYSTEM_AUTORUN_EVERY_N_LOOPS == 0
            ):
                try:
                    self.tool_system.run_cycle(loop_count=loop_count, metrics=_metrics)
                except Exception:
                    logger.exception("Tool system cycle failed — continuing")

            # ── Process UI command queue ─────────────────────────────────
            process_commands(
                self.db, self.trade_manager,
                self._request_shutdown, self.tool_system, self.state,
            )

            # ── Daily summary ────────────────────────────────────────────
            now = local_now()
            today_str = now.strftime("%Y-%m-%d")
            if now.hour >= settings.DAILY_SUMMARY_HOUR and today_str != last_summary_date:
                report = self.learning.get_report()
                self.log_agent.send_daily_summary(report)
                try:
                    self.learning.snapshot_daily()
                    if now.weekday() == 6:  # Sunday → weekly snapshot
                        self.learning.snapshot_weekly()
                        wfo_result = self.learning.run_wfo_assessment()
                        if (
                            wfo_result.get("avg_overfitting", 0.0) > 1.5
                            or wfo_result.get("parameter_stability", 1.0) < 0.6
                        ):
                            self.risk_agent.set_emergency_caps(
                                max_risk_per_trade=0.01,
                                max_open_trades=3,
                            )
                            logger.warning(
                                "WFO risk-gating: overfitting=%.2f stability=%.2f"
                                " → emergency caps set (max_risk=1%% max_pos=3)",
                                wfo_result.get("avg_overfitting", 0.0),
                                wfo_result.get("parameter_stability", 1.0),
                            )
                    if now.day == 1:  # 1st of month → monthly snapshot
                        self.learning.snapshot_monthly()
                except Exception:
                    logger.exception("Performance snapshot failed — bot continues")
                last_summary_date = today_str

            # ── Time-corrected sleep ─────────────────────────────────────
            elapsed = time.monotonic() - loop_start
            sleep_time = max(0, settings.LOOP_INTERVAL_SECONDS - elapsed)
            if sleep_time > 0:
                time.sleep(sleep_time)

        self.shutdown()

    def shutdown(self) -> None:
        """Everything after the while loop."""
        logger.info("Shutting down…")
        _ui = tui.get_ui()
        if _ui:
            _ui.stop()
        candle_server.stop()
        telegram_bot.stop_polling()
        telegram_bot.send_message("🛑 Bot shutting down.")
        # Persist open positions before closing broker connection
        # (gabagool pattern — ensures state survives hard interrupts)
        if self.trade_manager and self.state:
            for trade in self.trade_manager.get_open_trades():
                self.state.save_trade(trade)
            logger.info("Persisted %d open trades before broker disconnect",
                        len(self.trade_manager.get_open_trades()))
        if self.db and self._session_id:
            self.db.end_session(self._session_id, exit_reason="graceful")
            self.db.set_bot_stopped()
        if self.broker:
            self.broker.disconnect()
        if self.db:
            self.db.close()
        if self.log_agent:
            self.log_agent.record("SHUTDOWN", "Bot stopped gracefully")
        logger.info("Goodbye.")
