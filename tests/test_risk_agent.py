"""Tests for RiskAgent."""

from datetime import UTC, datetime, timedelta
from unittest.mock import patch

from agents.risk_agent import RiskAgent
from tests.conftest import make_trade


class _ProtectionDb:
    def __init__(self, trades):
        self._trades = trades

    def log_agent_event(self, *a, **kw):
        pass

    def get_closed_trades_since(self, since, limit=1000):
        filtered = [
            t for t in self._trades
            if t.close_time is not None and t.close_time >= since
        ]
        return filtered[:limit]


class TestRiskAgent:
    @staticmethod
    def _signal(**kwargs):
        from tests.conftest import make_signal

        sig = make_signal(**kwargs)
        sig.entry_snapshot.session = "london"
        return sig

    def _make_agent(self, broker, open_trades=None, crucix_agent=None, db=None):
        trades = open_trades or []
        return RiskAgent(
            broker=broker,
            get_open_trades=lambda: trades,
            crucix_agent=crucix_agent,
            db=db,
        )

    def test_validate_passes_clean_signal(self, broker, crucix_agent):
        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = self._signal()
        assert agent.validate(signal) is True

    def test_rejects_duplicate(self, broker, crucix_agent):
        existing = make_trade(symbol="EURUSD", direction="BUY", strategy="sma_crossover")
        agent = self._make_agent(broker, open_trades=[existing], crucix_agent=crucix_agent)
        signal = self._signal(symbol="EURUSD", direction="BUY", strategy="sma_crossover")
        assert agent.validate(signal) is False

    def test_allows_different_direction(self, broker, crucix_agent):
        existing = make_trade(symbol="EURUSD", direction="SELL", strategy="sma_crossover")
        agent = self._make_agent(broker, open_trades=[existing], crucix_agent=crucix_agent)
        signal = self._signal(symbol="EURUSD", direction="BUY", strategy="sma_crossover")
        assert agent.validate(signal) is True

    def test_rejects_correlation(self, broker, crucix_agent):
        existing = make_trade(symbol="EURUSD", direction="BUY", strategy="other_strategy")
        agent = self._make_agent(broker, open_trades=[existing], crucix_agent=crucix_agent)
        signal = self._signal(symbol="EURUSD", direction="BUY", strategy="sma_crossover")
        assert agent.validate(signal) is False

    def test_rejects_max_trades(self, broker, crucix_agent, monkeypatch):
        from config import settings as _settings

        monkeypatch.setattr(_settings, "MAX_OPEN_TRADES", 3)
        trades = [
            make_trade(symbol="EURUSD", direction="BUY", broker_ticket=100_001),
            make_trade(symbol="GBPUSD", direction="SELL", broker_ticket=100_002),
            make_trade(symbol="USDJPY", direction="BUY", broker_ticket=100_003),
        ]
        agent = self._make_agent(broker, open_trades=trades, crucix_agent=crucix_agent)
        signal = self._signal(symbol="XAUUSD", direction="BUY")
        assert agent.validate(signal) is False

    def test_rejects_high_spread(self, broker, crucix_agent, monkeypatch):
        from config import settings as _settings

        monkeypatch.setattr(_settings, "MAX_SPREAD_PIPS", 3.0)
        monkeypatch.setattr(
            broker,
            "get_tick",
            lambda sym: {"bid": 1.1050, "ask": 1.1055, "spread": 0.0005, "volume": 1000},
        )
        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = self._signal(spread=0.0005)
        assert agent._check_spread(signal) is False

    def test_spread_reject_sets_symbol_cooldown(self, broker, crucix_agent, monkeypatch):
        from config import settings as _settings

        monkeypatch.setattr(_settings, "MAX_SPREAD_PIPS", 3.0)
        monkeypatch.setattr(_settings, "SPREAD_REJECT_COOLDOWN_HITS", 2)
        monkeypatch.setattr(_settings, "SPREAD_REJECT_COOLDOWN_SECONDS", 120)
        monkeypatch.setattr(
            broker,
            "get_tick",
            lambda sym: {"bid": 1.1050, "ask": 1.1055, "spread": 0.0005, "volume": 1000},
        )

        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = self._signal(symbol="EURUSD", spread=0.0005)

        assert agent._check_spread(signal) is False
        assert signal.symbol not in agent._spread_reject_until

        assert agent._check_spread(signal) is False
        assert signal.symbol in agent._spread_reject_until

    def test_position_size_positive(self, broker, crucix_agent):
        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = self._signal()
        size = agent.calculate_position_size(signal)
        assert size >= 0.01

    def test_time_phase_confidence_gate_rejects_low_confidence(
        self, broker, crucix_agent, monkeypatch
    ):
        from config import settings as _settings

        monkeypatch.setattr(_settings, "TIME_PHASE_CONFIDENCE_ENABLED", True)
        monkeypatch.setattr(_settings, "TIME_PHASE_BUCKET_MINUTES", 15)
        monkeypatch.setattr(_settings, "TIME_PHASE_EARLY_MAX_MINUTE", 3)
        monkeypatch.setattr(_settings, "TIME_PHASE_MID_MAX_MINUTE", 11)
        monkeypatch.setattr(_settings, "TIME_PHASE_MIN_CONF_EARLY", 0.70)

        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = self._signal()
        signal.timestamp = datetime(2026, 1, 1, 10, 1, tzinfo=UTC)
        signal.confidence = 0.60

        assert agent.validate(signal) is False

    def test_time_phase_confidence_gate_accepts_when_disabled(
        self, broker, crucix_agent, monkeypatch
    ):
        from config import settings as _settings

        monkeypatch.setattr(_settings, "TIME_PHASE_CONFIDENCE_ENABLED", False)

        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = self._signal()
        signal.timestamp = datetime(2026, 1, 1, 10, 1, tzinfo=UTC)
        signal.confidence = 0.40

        assert agent.validate(signal) is True

    def test_protection_cooldown_blocks_reentry(self, broker, crucix_agent, monkeypatch):
        from config import settings as _settings

        monkeypatch.setattr(_settings, "PROTECTIONS_ENABLED", True)
        monkeypatch.setattr(_settings, "PROTECTION_COOLDOWN_MINUTES", 15)
        monkeypatch.setattr(_settings, "PROTECTION_STOPLOSS_GUARD_TRADE_LIMIT", 99)
        monkeypatch.setattr(_settings, "PROTECTION_GLOBAL_LOSS_GUARD_MAX_LOSSES", 99)

        recent = make_trade(symbol="EURUSD", direction="BUY")
        recent.status = "CLOSED"
        recent.close_time = datetime.now(UTC) - timedelta(minutes=5)
        recent.close_reason = "TP1"

        db = _ProtectionDb([recent])
        agent = self._make_agent(broker, crucix_agent=crucix_agent, db=db)
        signal = self._signal(symbol="EURUSD", direction="BUY")

        assert agent.validate(signal) is False

    def test_protection_stoploss_guard_locks_symbol(self, broker, crucix_agent, monkeypatch):
        from config import settings as _settings

        monkeypatch.setattr(_settings, "PROTECTIONS_ENABLED", True)
        monkeypatch.setattr(_settings, "PROTECTION_COOLDOWN_MINUTES", 0)
        monkeypatch.setattr(_settings, "PROTECTION_STOPLOSS_GUARD_LOOKBACK_MINUTES", 180)
        monkeypatch.setattr(_settings, "PROTECTION_STOPLOSS_GUARD_TRADE_LIMIT", 2)
        monkeypatch.setattr(_settings, "PROTECTION_STOPLOSS_GUARD_LOCK_MINUTES", 60)
        monkeypatch.setattr(_settings, "PROTECTION_GLOBAL_LOSS_GUARD_MAX_LOSSES", 99)

        t1 = make_trade(symbol="EURUSD", direction="BUY")
        t1.status = "CLOSED"
        t1.close_reason = "SL"
        t1.pnl = -10.0
        t1.close_time = datetime.now(UTC) - timedelta(minutes=20)

        t2 = make_trade(symbol="EURUSD", direction="BUY", broker_ticket=200_002)
        t2.status = "CLOSED"
        t2.close_reason = "SL"
        t2.pnl = -8.0
        t2.close_time = datetime.now(UTC) - timedelta(minutes=10)

        db = _ProtectionDb([t1, t2])
        agent = self._make_agent(broker, crucix_agent=crucix_agent, db=db)
        signal = self._signal(symbol="EURUSD", direction="BUY")

        assert agent.validate(signal) is False

    def test_position_size_mode_fixed_lot(self, broker, crucix_agent, monkeypatch):
        from config import settings as _settings

        monkeypatch.setattr(_settings, "POSITION_SIZE_MODE", "fixed_lot")
        monkeypatch.setattr(_settings, "POSITION_SIZE_FIXED_LOT", 0.23)

        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = self._signal()
        assert agent.calculate_position_size(signal) == 0.23

    def test_position_size_mode_balance_pct_uses_balance(self, broker, crucix_agent, monkeypatch):
        from config import settings as _settings

        monkeypatch.setattr(_settings, "POSITION_SIZE_MODE", "balance_pct")
        monkeypatch.setattr(_settings, "MAX_RISK_PER_TRADE", 0.01)
        monkeypatch.setattr(broker, "get_balance", lambda: 10_000.0)
        monkeypatch.setattr(broker, "get_equity", lambda: 5_000.0)

        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = self._signal(entry=1.1050, sl=1.1000)
        size = agent.calculate_position_size(signal)
        assert size > 0.01

    def test_position_size_mode_fixed_risk_amount(self, broker, crucix_agent, monkeypatch):
        from config import settings as _settings

        monkeypatch.setattr(_settings, "POSITION_SIZE_MODE", "fixed_risk_amount")
        monkeypatch.setattr(_settings, "POSITION_SIZE_FIXED_RISK_AMOUNT", 50.0)

        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = self._signal(entry=1.1050, sl=1.1000)
        size = agent.calculate_position_size(signal)
        assert size >= 0.01

    def test_confidence_scaling_reduces_size(self, broker, crucix_agent):
        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal_high = self._signal()
        signal_high.confidence = 0.9
        size_high = agent.calculate_position_size(signal_high)

        signal_low = self._signal()
        signal_low.confidence = 0.3
        size_low = agent.calculate_position_size(signal_low)

        assert size_low <= size_high

    @patch("utils.telegram_bot.send_message")
    def test_drawdown_circuit_breaker(self, mock_tg, broker, crucix_agent, monkeypatch):
        from config import settings as _settings

        monkeypatch.setattr(_settings, "MAX_DAILY_LOSS", 0.05)
        agent = self._make_agent(broker, crucix_agent=crucix_agent)
        signal = self._signal()
        agent.validate(signal)

        agent._day_start_equity = 10_000.0
        monkeypatch.setattr(broker, "get_equity", lambda: 9_400.0)
        agent._equity_cache = (0.0, 0.0)

        assert agent._check_drawdown() is True
        assert agent._circuit_breaker_active is True

    # ── Daily / Monthly loss gate tests ──────────────────────────────────────

    def test_daily_loss_gate_blocks_when_limit_reached(self, broker, crucix_agent, monkeypatch):
        """Daily gate fires when today's closed-trade loss >= MAX_DAILY_LOSS."""
        from config import settings as _settings

        monkeypatch.setattr(_settings, "MAX_DAILY_LOSS", 0.05)
        now = datetime.now(UTC)
        trade = make_trade(symbol="EURUSD", direction="BUY")
        trade.pnl = -500.0  # -500 / 10,000 equity = 5% >= 5% threshold
        trade.close_time = now
        trade.status = "CLOSED"

        db = _ProtectionDb([trade])
        agent = self._make_agent(broker, crucix_agent=crucix_agent, db=db)
        agent._daily_cache_ts = 0.0  # force cache expiry

        assert agent._check_daily_loss() is True

    def test_daily_loss_gate_allows_when_profitable(self, broker, crucix_agent, monkeypatch):
        """Daily gate does not block when today's realised PnL is positive."""
        from config import settings as _settings

        monkeypatch.setattr(_settings, "MAX_DAILY_LOSS", 0.05)
        now = datetime.now(UTC)
        trade = make_trade(symbol="EURUSD", direction="BUY")
        trade.pnl = 200.0
        trade.close_time = now
        trade.status = "CLOSED"

        db = _ProtectionDb([trade])
        agent = self._make_agent(broker, crucix_agent=crucix_agent, db=db)
        agent._daily_cache_ts = 0.0

        assert agent._check_daily_loss() is False

    def test_daily_loss_gate_blocks_validate(self, broker, crucix_agent, monkeypatch):
        """validate() returns False when day's closed-trade loss >= MAX_DAILY_LOSS."""
        from config import settings as _settings

        monkeypatch.setattr(_settings, "MAX_DAILY_LOSS", 0.05)
        now = datetime.now(UTC)
        trade = make_trade(symbol="EURUSD", direction="BUY")
        trade.pnl = -500.0
        trade.close_time = now
        trade.status = "CLOSED"

        db = _ProtectionDb([trade])
        agent = self._make_agent(broker, crucix_agent=crucix_agent, db=db)
        agent._daily_cache_ts = 0.0

        assert agent.validate(self._signal()) is False

    def test_monthly_loss_gate_blocks_when_limit_reached(self, broker, crucix_agent, monkeypatch):
        """Monthly gate fires when MTD closed-trade loss >= MAX_MONTHLY_LOSS."""
        from config import settings as _settings

        monkeypatch.setattr(_settings, "MAX_MONTHLY_LOSS", 0.10)
        now = datetime.now(UTC)
        trade = make_trade(symbol="EURUSD", direction="BUY")
        trade.pnl = -1000.0  # -1000 / 10,000 equity = 10% >= 10% threshold
        trade.close_time = now
        trade.status = "CLOSED"

        db = _ProtectionDb([trade])
        agent = self._make_agent(broker, crucix_agent=crucix_agent, db=db)
        agent._monthly_cache_ts = 0.0  # force cache expiry

        assert agent._check_monthly_loss() is True
