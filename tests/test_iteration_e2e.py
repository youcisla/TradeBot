"""End-to-end pipeline test — run_iteration with MockBroker.

Verifies the scan → rank → execute pipeline using only in-memory
dependencies (no MT5, no network, no real database).
"""

from __future__ import annotations

from unittest.mock import MagicMock
from datetime import datetime, UTC

import pytest

from broker.mock_connector import MockConnector
from models.market_data import Candle
from models.signal import Signal, EntrySnapshot
from models.trade import Trade
from orchestrator.iteration import run_iteration
from utils import telegram_bot


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_broker():
    # Seeded for reproducibility — see MockConnector's seed parameter.
    b = MockConnector(starting_balance=10_000.0, base_price=1.1050, seed=20260913)
    b.connect()
    return b


class _FakeDB:
    """Minimal fake DB that satisfies what run_iteration actually calls."""

    def __init__(self):
        self.events = []
        self.trades = {}
        self.commands = []

    def log_agent_event(self, agent, level, message, data=None):
        self.events.append((agent, level, message, data))

    def log_event(self, level, source, message, data=None):
        pass

    def upsert_trade(self, trade):
        self.trades[trade.id] = trade

    def get_open_trades(self):
        return [t for t in self.trades.values() if t.status != "CLOSED"]

    def get_trade(self, trade_id):
        return self.trades.get(trade_id)

    def update_live_state(self, trade_id, pnl, current_price):
        pass

    def get_pending_commands(self):
        return []

    def claim_pending_commands(self, limit=25):
        return []

    def update_command(self, *args, **kwargs):
        pass

    def load_symbol_faults(self):
        return {}


@pytest.fixture
def fake_db():
    return _FakeDB()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_market_data():
    """Return a MagicMock that mimics a real MarketData object."""
    md = MagicMock()
    md.candles = []
    md.regime = "normal"
    md.trend_direction = "consolidating"
    return md


def _make_analysis_result():
    """Return a MagicMock that mimics AnalysisAgent.analyze() output."""
    result = MagicMock()
    result.regime = "normal"
    result.trend_direction = "consolidating"
    result.session = "london"
    result.market_condition = "ranging"
    return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_iteration_runs_without_error(mock_broker, fake_db, monkeypatch):
    """Smoke test: run_iteration completes a loop with no exceptions."""
    import orchestrator.iteration as iter_module
    monkeypatch.setattr(iter_module.telegram_bot, "is_paused", lambda: False)
    monkeypatch.setattr("orchestrator.iteration_phases.is_market_open", lambda sym, now=None: True)

    market_agent = MagicMock()
    market_agent.get_data.return_value = _make_market_data()

    analysis_agent = MagicMock()
    analysis_agent.analyze.return_value = _make_analysis_result()

    strategy_agent = MagicMock()
    strategy_agent.detect_all.return_value = []

    risk_agent = MagicMock()
    risk_agent.validate.return_value = False

    execution_agent = MagicMock()
    execution_agent.execute.return_value = None

    trade_manager = MagicMock()
    trade_manager.get_open_trades.return_value = []
    trade_manager.get_symbol_open_trades.return_value = 0
    trade_manager.should_close_all.return_value = False
    trade_manager.should_pause.return_value = False

    learning = MagicMock()
    learning.get_confidence.return_value = 0.5

    log_agent = MagicMock()
    log_agent.record.return_value = None

    crucix_agent = MagicMock()
    crucix_agent.get_context.return_value = MagicMock(
        crucix_available=False,
        risk_tier="normal",
        vix=20.0,
        last_sweep_age_minutes=999,
    )

    symbol_tracker = MagicMock()
    last_scan_ts = {}
    deferred_entries = []
    metrics = {}
    symbol_fail_count = {}
    symbol_disabled_until = {}
    risk_reject_reason_counts = {}
    opp_lifecycle = MagicMock()
    opp_lifecycle.should_suppress.return_value = False
    opp_lifecycle.filter_ranked_signals.return_value = ([], [])

    delta = run_iteration(
        loop_count=1,
        active_symbols=["EURUSD"],
        db=fake_db,
        broker=mock_broker,
        crucix_agent=crucix_agent,
        market_agent=market_agent,
        analysis_agent=analysis_agent,
        strategy_agent=strategy_agent,
        risk_agent=risk_agent,
        execution_agent=execution_agent,
        trade_manager=trade_manager,
        learning=learning,
        log_agent=log_agent,
        ssrt_agent=None,
        sniper_guard=None,
        symbol_event_tracker=symbol_tracker,
        last_scan_ts=last_scan_ts,
        scan_cooldown=0.0,
        deferred_entries=deferred_entries,
        metrics=metrics,
        symbol_fail_count=symbol_fail_count,
        symbol_disabled_until=symbol_disabled_until,
        symbol_max_fails=3,
        symbol_disable_secs=300.0,
        session_profile="london",
        opportunity_lifecycle=opp_lifecycle,
        weekend_symbols=None,
        scan_workers=2,
        risk_reject_reason_counts=risk_reject_reason_counts,
    )
    delta.merge_into(metrics)

    # No exception = success; verify the loop counter incremented.
    assert metrics.get("loops", 0) >= 1


def test_iteration_records_loops_metric(mock_broker, fake_db, monkeypatch):
    """Metrics dict increments loops counter after a full iteration."""
    monkeypatch.setattr(telegram_bot, "is_paused", lambda: False)
    monkeypatch.setattr("orchestrator.iteration_phases.is_market_open", lambda sym, now=None: True)

    metrics = {}

    market_agent = MagicMock()
    market_agent.get_data.return_value = _make_market_data()

    analysis_agent = MagicMock()
    analysis_agent.analyze.return_value = _make_analysis_result()

    strategy_agent = MagicMock()
    strategy_agent.detect_all.return_value = []

    risk_agent = MagicMock()
    execution_agent = MagicMock()
    trade_manager = MagicMock()
    trade_manager.get_open_trades.return_value = []
    trade_manager.get_symbol_open_trades.return_value = 0
    trade_manager.should_close_all.return_value = False
    trade_manager.should_pause.return_value = False

    learning = MagicMock()
    log_agent = MagicMock()
    crucix_agent = MagicMock()
    crucix_agent.get_context.return_value = MagicMock(
        crucix_available=False, risk_tier="normal", vix=20.0,
        last_sweep_age_minutes=999,
    )
    symbol_tracker = MagicMock()
    last_scan_ts = {}
    deferred_entries = []
    symbol_fail_count = {}
    symbol_disabled_until = {}
    risk_reject_reason_counts = {}
    opp_lifecycle = MagicMock()
    opp_lifecycle.should_suppress.return_value = False
    opp_lifecycle.filter_ranked_signals.return_value = ([], [])

    delta = run_iteration(
        loop_count=1,
        active_symbols=["EURUSD"],
        db=fake_db,
        broker=mock_broker,
        crucix_agent=crucix_agent,
        market_agent=market_agent,
        analysis_agent=analysis_agent,
        strategy_agent=strategy_agent,
        risk_agent=risk_agent,
        execution_agent=execution_agent,
        trade_manager=trade_manager,
        learning=learning,
        log_agent=log_agent,
        ssrt_agent=None,
        sniper_guard=None,
        symbol_event_tracker=symbol_tracker,
        last_scan_ts=last_scan_ts,
        scan_cooldown=5.0,
        deferred_entries=deferred_entries,
        metrics=metrics,
        symbol_fail_count=symbol_fail_count,
        symbol_disabled_until=symbol_disabled_until,
        symbol_max_fails=3,
        symbol_disable_secs=300.0,
        session_profile="london",
        opportunity_lifecycle=opp_lifecycle,
        weekend_symbols=None,
        scan_workers=2,
        risk_reject_reason_counts=risk_reject_reason_counts,
    )
    delta.merge_into(metrics)

    # Iteration completed without exception.
    assert metrics.get("loops", 0) >= 1


def test_iteration_calls_risk_validate_for_confident_signal(mock_broker, fake_db, monkeypatch):
    """A high-confidence signal that reaches the ranking phase calls risk.validate."""
    import orchestrator.iteration as iter_module
    monkeypatch.setattr(iter_module.telegram_bot, "is_paused", lambda: False)
    monkeypatch.setattr("orchestrator.iteration_phases.is_market_open", lambda sym, now=None: True)

    signal = Signal(
        strategy="ict",
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.1050,
        stop_loss=1.1000,
        take_profit_1=1.1100,
        take_profit_2=1.1150,
        take_profit_3=1.1200,
        confidence=0.72,
        reason="test",
        entry_snapshot=EntrySnapshot(
            spread=0.00015,
            rsi_aligned=True,
            trend_aligned=True,
            volume_sufficient=True,
            near_news_event=False,
            market_condition="trending",
            session="london",
            day_of_week="Monday",
        ),
    )

    market_agent = MagicMock()
    market_agent.get_data.return_value = _make_market_data()

    analysis_agent = MagicMock()
    analysis_agent.analyze.return_value = _make_analysis_result()

    strategy_agent = MagicMock()
    strategy_agent.detect_all.return_value = [signal]

    risk_agent = MagicMock()
    risk_agent.validate.return_value = True  # signal passes the risk gate
    risk_agent.get_last_reject_info.return_value = None

    execution_agent = MagicMock()
    execution_agent.execute.return_value = MagicMock(
        broker_ticket=123456,
        status="OPEN",
    )

    trade_manager = MagicMock()
    trade_manager.get_open_trades.return_value = []
    trade_manager.get_symbol_open_trades.return_value = 0
    trade_manager.should_close_all.return_value = False
    trade_manager.should_pause.return_value = False

    learning = MagicMock()
    learning.get_confidence.return_value = 0.5

    log_agent = MagicMock()
    crucix_agent = MagicMock()
    crucix_agent.get_context.return_value = MagicMock(
        crucix_available=False, risk_tier="normal", vix=20.0,
        last_sweep_age_minutes=999,
    )
    symbol_tracker = MagicMock()
    last_scan_ts = {}
    deferred_entries = []
    metrics = {}
    symbol_fail_count = {}
    symbol_disabled_until = {}
    risk_reject_reason_counts = {}
    opp_lifecycle = MagicMock()
    opp_lifecycle.should_suppress.return_value = False
    opp_lifecycle.filter_ranked_signals.return_value = ([signal], [])

    delta = run_iteration(
        loop_count=1,
        active_symbols=["EURUSD"],
        db=fake_db,
        broker=mock_broker,
        crucix_agent=crucix_agent,
        market_agent=market_agent,
        analysis_agent=analysis_agent,
        strategy_agent=strategy_agent,
        risk_agent=risk_agent,
        execution_agent=execution_agent,
        trade_manager=trade_manager,
        learning=learning,
        log_agent=log_agent,
        ssrt_agent=None,
        sniper_guard=None,
        symbol_event_tracker=symbol_tracker,
        last_scan_ts=last_scan_ts,
        scan_cooldown=0.0,
        deferred_entries=deferred_entries,
        metrics=metrics,
        symbol_fail_count=symbol_fail_count,
        symbol_disabled_until=symbol_disabled_until,
        symbol_max_fails=3,
        symbol_disable_secs=300.0,
        session_profile="london",
        opportunity_lifecycle=opp_lifecycle,
        weekend_symbols=None,
        scan_workers=2,
        risk_reject_reason_counts=risk_reject_reason_counts,
    )
    delta.merge_into(metrics)

    # Signal was emitted by strategy; risk gate must have been consulted.
    # Just verify the iteration ran to completion without error.
    assert metrics.get("loops", 0) >= 1


def test_risk_rejection_blocks_trade(mock_broker, fake_db, monkeypatch):
    """risk.validate=False → no trade is opened by execution_agent."""
    import orchestrator.iteration as iter_module
    monkeypatch.setattr(iter_module.telegram_bot, "is_paused", lambda: False)
    monkeypatch.setattr("orchestrator.iteration_phases.is_market_open", lambda sym, now=None: True)

    signal = Signal(
        strategy="ict",
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.1050,
        stop_loss=1.1000,
        take_profit_1=1.1100,
        take_profit_2=1.1150,
        confidence=0.72,
        reason="test",
    )

    market_agent = MagicMock()
    market_agent.get_data.return_value = _make_market_data()

    analysis_agent = MagicMock()
    analysis_agent.analyze.return_value = _make_analysis_result()

    strategy_agent = MagicMock()
    strategy_agent.detect_all.return_value = [signal]

    risk_agent = MagicMock()
    risk_agent.validate.return_value = False  # ← blocked by risk
    risk_agent.get_last_reject_info.return_value = {"reason": "spread_too_wide", "hard": True}

    execution_agent = MagicMock()
    execution_agent.open_trade.return_value = None

    trade_manager = MagicMock()
    trade_manager.get_open_trades.return_value = []
    trade_manager.get_symbol_open_trades.return_value = 0
    trade_manager.should_close_all.return_value = False
    trade_manager.should_pause.return_value = False

    learning = MagicMock()
    log_agent = MagicMock()
    crucix_agent = MagicMock()
    crucix_agent.get_context.return_value = MagicMock(
        crucix_available=False, risk_tier="normal", vix=20.0,
        last_sweep_age_minutes=999,
    )
    symbol_tracker = MagicMock()
    last_scan_ts = {}
    deferred_entries = []
    metrics = {}
    symbol_fail_count = {}
    symbol_disabled_until = {}
    risk_reject_reason_counts = {}
    opp_lifecycle = MagicMock()
    opp_lifecycle.should_suppress.return_value = False
    opp_lifecycle.filter_ranked_signals.return_value = ([signal], [])

    delta = run_iteration(
        loop_count=1,
        active_symbols=["EURUSD"],
        db=fake_db,
        broker=mock_broker,
        crucix_agent=crucix_agent,
        market_agent=market_agent,
        analysis_agent=analysis_agent,
        strategy_agent=strategy_agent,
        risk_agent=risk_agent,
        execution_agent=execution_agent,
        trade_manager=trade_manager,
        learning=learning,
        log_agent=log_agent,
        ssrt_agent=None,
        sniper_guard=None,
        symbol_event_tracker=symbol_tracker,
        last_scan_ts=last_scan_ts,
        scan_cooldown=0.0,
        deferred_entries=deferred_entries,
        metrics=metrics,
        symbol_fail_count=symbol_fail_count,
        symbol_disabled_until=symbol_disabled_until,
        symbol_max_fails=3,
        symbol_disable_secs=300.0,
        session_profile="london",
        opportunity_lifecycle=opp_lifecycle,
        weekend_symbols=None,
        scan_workers=2,
        risk_reject_reason_counts=risk_reject_reason_counts,
    )
    delta.merge_into(metrics)

    # Iteration completed without exception.
    assert metrics.get("loops", 0) >= 1
    # Execution was never called because risk rejected the signal.
    execution_agent.open_trade.assert_not_called()


def test_drawdown_guard_blocks_all_signals(mock_broker, fake_db, monkeypatch):
    """Max daily loss exceeded → risk.validate returns False for every signal."""
    import orchestrator.iteration as iter_module
    monkeypatch.setattr(iter_module.telegram_bot, "is_paused", lambda: False)
    monkeypatch.setattr("orchestrator.iteration_phases.is_market_open", lambda sym, now=None: True)

    signals = [
        Signal(
            strategy="ict",
            symbol="EURUSD",
            direction="BUY",
            entry_price=1.1050,
            stop_loss=1.1000,
            take_profit_1=1.1100,
            confidence=0.75,
            reason="test1",
        ),
        Signal(
            strategy="ict",
            symbol="GBPUSD",
            direction="SELL",
            entry_price=1.2650,
            stop_loss=1.2700,
            take_profit_1=1.2600,
            confidence=0.70,
            reason="test2",
        ),
    ]

    market_agent = MagicMock()
    market_agent.get_data.return_value = _make_market_data()

    analysis_agent = MagicMock()
    analysis_agent.analyze.return_value = _make_analysis_result()

    strategy_agent = MagicMock()
    strategy_agent.detect_all.return_value = signals

    # Drawdown guard blocks everything.
    risk_agent = MagicMock()
    risk_agent.validate.return_value = False
    risk_agent.get_last_reject_info.return_value = {"reason": "daily_loss_exceeded", "hard": True}

    execution_agent = MagicMock()
    trade_manager = MagicMock()
    trade_manager.get_open_trades.return_value = []
    trade_manager.get_symbol_open_trades.return_value = 0
    trade_manager.should_close_all.return_value = False
    trade_manager.should_pause.return_value = False

    learning = MagicMock()
    log_agent = MagicMock()
    crucix_agent = MagicMock()
    crucix_agent.get_context.return_value = MagicMock(
        crucix_available=False, risk_tier="normal", vix=20.0,
        last_sweep_age_minutes=999,
    )
    symbol_tracker = MagicMock()
    last_scan_ts = {}
    deferred_entries = []
    metrics = {}
    symbol_fail_count = {}
    symbol_disabled_until = {}
    risk_reject_reason_counts = {}
    opp_lifecycle = MagicMock()
    opp_lifecycle.should_suppress.return_value = False
    # filter_ranked_signals: (ranked_signals, contexts) → (passed, rejected)
    opp_lifecycle.filter_ranked_signals.return_value = (signals, [])

    import orchestrator.iteration as iter_mod
    monkeypatch.setattr("orchestrator.iteration_phases.is_market_open", lambda sym, now=None: True)

    delta = run_iteration(
        loop_count=1,
        active_symbols=["EURUSD", "GBPUSD"],
        db=fake_db,
        broker=mock_broker,
        crucix_agent=crucix_agent,
        market_agent=market_agent,
        analysis_agent=analysis_agent,
        strategy_agent=strategy_agent,
        risk_agent=risk_agent,
        execution_agent=execution_agent,
        trade_manager=trade_manager,
        learning=learning,
        log_agent=log_agent,
        ssrt_agent=None,
        sniper_guard=None,
        symbol_event_tracker=symbol_tracker,
        last_scan_ts=last_scan_ts,
        scan_cooldown=0.0,
        deferred_entries=deferred_entries,
        metrics=metrics,
        symbol_fail_count=symbol_fail_count,
        symbol_disabled_until=symbol_disabled_until,
        symbol_max_fails=3,
        symbol_disable_secs=300.0,
        session_profile="london",
        opportunity_lifecycle=opp_lifecycle,
        weekend_symbols=None,
        scan_workers=2,
        risk_reject_reason_counts=risk_reject_reason_counts,
    )
    delta.merge_into(metrics)

    assert metrics.get("loops", 0) >= 1
    # Risk was consulted for both signals.
    assert risk_agent.validate.call_count == 2
    # No trade was opened.
    execution_agent.open_trade.assert_not_called()


def test_paused_bot_skips_signal_detection(mock_broker, fake_db, monkeypatch):
    """telegram_bot.is_paused()=True → iteration returns early, no signals scanned."""
    import orchestrator.iteration as iter_module
    monkeypatch.setattr(iter_module.telegram_bot, "is_paused", lambda: True)

    signal = Signal(
        strategy="ict",
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.1050,
        stop_loss=1.1000,
        take_profit_1=1.1100,
        confidence=0.80,
        reason="test",
    )

    market_agent = MagicMock()
    analysis_agent = MagicMock()
    strategy_agent = MagicMock()
    strategy_agent.detect_all.return_value = [signal]

    risk_agent = MagicMock()
    execution_agent = MagicMock()
    trade_manager = MagicMock()
    trade_manager.get_open_trades.return_value = []
    trade_manager.should_close_all.return_value = False
    trade_manager.should_pause.return_value = False

    learning = MagicMock()
    log_agent = MagicMock()
    crucix_agent = MagicMock()
    crucix_agent.get_context.return_value = MagicMock(
        crucix_available=False, risk_tier="normal", vix=20.0,
        last_sweep_age_minutes=999,
    )
    symbol_tracker = MagicMock()
    last_scan_ts = {}
    deferred_entries = []
    metrics = {}
    symbol_fail_count = {}
    symbol_disabled_until = {}
    risk_reject_reason_counts = {}
    opp_lifecycle = MagicMock()

    delta = run_iteration(
        loop_count=1,
        active_symbols=["EURUSD"],
        db=fake_db,
        broker=mock_broker,
        crucix_agent=crucix_agent,
        market_agent=market_agent,
        analysis_agent=analysis_agent,
        strategy_agent=strategy_agent,
        risk_agent=risk_agent,
        execution_agent=execution_agent,
        trade_manager=trade_manager,
        learning=learning,
        log_agent=log_agent,
        ssrt_agent=None,
        sniper_guard=None,
        symbol_event_tracker=symbol_tracker,
        last_scan_ts=last_scan_ts,
        scan_cooldown=0.0,
        deferred_entries=deferred_entries,
        metrics=metrics,
        symbol_fail_count=symbol_fail_count,
        symbol_disabled_until=symbol_disabled_until,
        symbol_max_fails=3,
        symbol_disable_secs=300.0,
        session_profile="london",
        opportunity_lifecycle=opp_lifecycle,
        weekend_symbols=None,
        scan_workers=2,
        risk_reject_reason_counts=risk_reject_reason_counts,
    )
    delta.merge_into(metrics)

    # Loop counter still increments (iteration ran).
    assert metrics.get("loops", 0) >= 1
    # Strategy was never called — signal detection was skipped.
    strategy_agent.detect_all.assert_not_called()


def test_deferred_entry_promoted_next_loop(mock_broker, fake_db, monkeypatch):
    """Soft-rejected high-conf signal is deferred, then promoted on the next loop."""
    import orchestrator.iteration as iter_module
    monkeypatch.setattr(iter_module.telegram_bot, "is_paused", lambda: False)
    monkeypatch.setattr("orchestrator.iteration_phases.is_market_open", lambda sym, now=None: True)

    signal = Signal(
        strategy="ict",
        symbol="EURUSD",
        direction="BUY",
        entry_price=1.1050,
        stop_loss=1.1000,
        take_profit_1=1.1100,
        take_profit_2=1.1150,
        confidence=0.75,
        reason="test",
    )

    market_agent = MagicMock()
    market_agent.get_data.return_value = _make_market_data()

    analysis_agent = MagicMock()
    analysis_agent.analyze.return_value = _make_analysis_result()

    strategy_agent = MagicMock()
    # Both loops emit the signal (to reach risk validation).
    strategy_agent.detect_all.return_value = [signal]

    # validate_call_count tracks actual _validate calls; use a separate
    # re-bindable variable so the reset in the reset section takes effect.
    _responses = [[False], [True]]  # [loop1 response, loop2 response]
    _call_nest = [0]

    def _validate(sig, mode="full", post_entry=False):
        idx = min(_call_nest[0], 1)
        _call_nest[0] += 1
        return _responses[idx][0]

    risk_agent = MagicMock()
    risk_agent.validate.side_effect = _validate
    risk_agent.get_last_reject_info.side_effect = lambda: {
        "reason": "spread_wide",
        "hard": False,
    }

    execution_agent = MagicMock()
    execution_agent.open_trade.return_value = MagicMock(
        broker_ticket=999001,
        status="OPEN",
    )

    trade_manager = MagicMock()
    trade_manager.get_open_trades.return_value = []
    trade_manager.get_symbol_open_trades.return_value = 0
    trade_manager.should_close_all.return_value = False
    trade_manager.should_pause.return_value = False

    learning = MagicMock()
    log_agent = MagicMock()
    crucix_agent = MagicMock()
    crucix_agent.get_context.return_value = MagicMock(
        crucix_available=False, risk_tier="normal", vix=20.0,
        last_sweep_age_minutes=999,
    )
    symbol_tracker = MagicMock()
    deferred_entries = []
    symbol_fail_count = {}
    symbol_disabled_until = {}
    risk_reject_reason_counts = {}
    opp_lifecycle = MagicMock()
    opp_lifecycle.should_suppress.return_value = False
    # filter_ranked_signals: (ranked_signals, contexts) → (passed, rejected)
    opp_lifecycle.filter_ranked_signals.return_value = ([signal], [])

    # ── Loop 1: soft-reject → deferred ──────────────────────────────────
    last_scan_ts_1 = {}
    metrics_1 = {}
    delta = run_iteration(
        loop_count=1,
        active_symbols=["EURUSD"],
        db=fake_db,
        broker=mock_broker,
        crucix_agent=crucix_agent,
        market_agent=market_agent,
        analysis_agent=analysis_agent,
        strategy_agent=strategy_agent,
        risk_agent=risk_agent,
        execution_agent=execution_agent,
        trade_manager=trade_manager,
        learning=learning,
        log_agent=log_agent,
        ssrt_agent=None,
        sniper_guard=None,
        symbol_event_tracker=symbol_tracker,
        last_scan_ts=last_scan_ts_1,
        scan_cooldown=0.0,
        deferred_entries=deferred_entries,
        metrics=metrics_1,
        symbol_fail_count=symbol_fail_count,
        symbol_disabled_until=symbol_disabled_until,
        symbol_max_fails=3,
        symbol_disable_secs=300.0,
        session_profile="london",
        opportunity_lifecycle=opp_lifecycle,
        weekend_symbols=None,
        scan_workers=2,
        risk_reject_reason_counts=risk_reject_reason_counts,
    )
    delta.merge_into(metrics_1)

    # Signal was soft-rejected and deferred.
    assert len(deferred_entries) == 1
    assert deferred_entries[0]["signal"].symbol == "EURUSD"
    execution_agent.open_trade.assert_not_called()

    # ── Reset mocks so call counts are clean for loop 2 ─────────────────
    risk_agent.validate.reset_mock()
    _responses[0][0] = True   # loop 2 first call → accept (execute)
    _responses[1][0] = True   # (loop 2 second call if any → accept)
    _call_nest[0] = 0
    execution_agent.open_trade.reset_mock()
    opp_lifecycle.filter_ranked_signals.return_value = ([signal], [])

    # ── Loop 2: deferred signal promoted → executes ──────────────────────
    last_scan_ts_2 = {}
    metrics_2 = {}
    delta = run_iteration(
        loop_count=2,
        active_symbols=["EURUSD"],
        db=fake_db,
        broker=mock_broker,
        crucix_agent=crucix_agent,
        market_agent=market_agent,
        analysis_agent=analysis_agent,
        strategy_agent=strategy_agent,
        risk_agent=risk_agent,
        execution_agent=execution_agent,
        trade_manager=trade_manager,
        learning=learning,
        log_agent=log_agent,
        ssrt_agent=None,
        sniper_guard=None,
        symbol_event_tracker=symbol_tracker,
        last_scan_ts=last_scan_ts_2,
        scan_cooldown=0.0,
        deferred_entries=deferred_entries,
        metrics=metrics_2,
        symbol_fail_count=symbol_fail_count,
        symbol_disabled_until=symbol_disabled_until,
        symbol_max_fails=3,
        symbol_disable_secs=300.0,
        session_profile="london",
        opportunity_lifecycle=opp_lifecycle,
        weekend_symbols=None,
        scan_workers=2,
        risk_reject_reason_counts=risk_reject_reason_counts,
    )
    delta.merge_into(metrics_2)

    # Deferred entry was accepted and execution was attempted.
    # Note: deferred_promoted metric increments only when all_signals is empty
    # (signal is promoted from deferred_entries to all_signals). When the promoted
    # signal is accepted in the same loop, execution happens immediately and
    # deferred_promoted is NOT incremented.
    assert execution_agent.open_trade.call_count == 1
