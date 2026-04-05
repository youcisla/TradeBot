"""Tests for LearningAgent."""

from agents.learning_agent import LearningAgent
from tests.conftest import make_trade


class TestLearningAgent:
    def test_review_clean_win(self, db):
        agent = LearningAgent(db)
        trade = make_trade(entry=1.1050, sl=1.1000)
        trade.status = "CLOSED"
        trade.pnl = 20.0  # large profit → ≥ 2R → clean win
        score = agent.review_trade(trade)
        # Clean win base = 3, plus bonuses for rsi + trend + volume + no news
        assert score >= 3.0

    def test_review_messy_win(self, db):
        agent = LearningAgent(db)
        trade = make_trade(entry=1.1050, sl=1.1000)
        trade.status = "CLOSED"
        trade.pnl = 0.5  # tiny profit → messy win
        score = agent.review_trade(trade)
        assert score >= 1.0

    def test_review_normal_loss(self, db):
        agent = LearningAgent(db)
        trade = make_trade(entry=1.1050, sl=1.1000)
        trade.status = "CLOSED"
        trade.snap_rsi_aligned = False
        trade.snap_trend_aligned = False
        trade.snap_volume_sufficient = False
        trade.snap_near_news_event = True
        trade.pnl = -3.0  # small loss, no bonuses
        score = agent.review_trade(trade)
        assert score < 0

    def test_review_bad_loss(self, db):
        agent = LearningAgent(db)
        trade = make_trade(entry=1.1050, sl=1.1000)
        trade.status = "CLOSED"
        trade.snap_rsi_aligned = False
        trade.snap_trend_aligned = False
        trade.snap_volume_sufficient = False
        trade.snap_near_news_event = True
        trade.pnl = -100.0  # very large loss → well exceeds 1.5× initial risk (50)
        score = agent.review_trade(trade)
        assert score <= -3.0  # BAD_LOSS(-5) with no bonuses = -5

    def test_confidence_increases_after_win(self, db):
        agent = LearningAgent(db)
        initial = agent.get_confidence("sma_crossover")

        trade = make_trade(entry=1.1050, sl=1.1000)
        trade.status = "CLOSED"
        trade.pnl = 20.0
        agent.review_trade(trade)

        after = agent.get_confidence("sma_crossover")
        assert after > initial

    def test_confidence_decreases_after_loss(self, db):
        agent = LearningAgent(db)
        initial = agent.get_confidence("sma_crossover")

        trade = make_trade(entry=1.1050, sl=1.1000)
        trade.status = "CLOSED"
        trade.snap_rsi_aligned = False
        trade.snap_trend_aligned = False
        trade.snap_volume_sufficient = False
        trade.snap_near_news_event = True
        trade.pnl = -100.0  # large enough for bad-loss with no bonuses
        agent.review_trade(trade)

        after = agent.get_confidence("sma_crossover")
        assert after < initial

    def test_confidence_clamped_min(self, db):
        agent = LearningAgent(db)
        # Force confidence very low
        db.upsert_confidence("sma_crossover", 0.1, 0, 0)

        trade = make_trade(entry=1.1050, sl=1.1000)
        trade.status = "CLOSED"
        trade.pnl = -50.0
        agent.review_trade(trade)

        after = agent.get_confidence("sma_crossover")
        assert after >= LearningAgent.CONFIDENCE_MIN

    def test_confidence_clamped_max(self, db):
        agent = LearningAgent(db)
        db.upsert_confidence("sma_crossover", 0.99, 0, 0)

        trade = make_trade(entry=1.1050, sl=1.1000)
        trade.status = "CLOSED"
        trade.pnl = 50.0
        agent.review_trade(trade)

        after = agent.get_confidence("sma_crossover")
        assert after <= LearningAgent.CONFIDENCE_MAX

    def test_is_strategy_enabled(self, db):
        agent = LearningAgent(db)
        db.upsert_confidence("sma_crossover", 0.5, 0, 0)
        assert agent.is_strategy_enabled("sma_crossover") is True

        db.upsert_confidence("sma_crossover", 0.1, 0, 0)
        assert agent.is_strategy_enabled("sma_crossover") is False

    def test_get_report_no_trades(self, db):
        agent = LearningAgent(db)
        report = agent.get_report()
        assert report["trades_today"] == 0

    def test_context_memory_can_boost_multiplier(self, db):
        agent = LearningAgent(db)
        mult = agent._reward_multiplier(
            "sma_crossover",
            2.0,
            0,
            {"trades": 6, "avg_score": 1.4, "avg_pnl": 12.0, "win_rate": 0.68},
        )
        assert mult > 1.0

    def test_context_memory_caps_multiplier_when_context_is_weak(self, db):
        agent = LearningAgent(db)
        mult = agent._reward_multiplier(
            "sma_crossover",
            2.0,
            5,
            {"trades": 7, "avg_score": -1.1, "avg_pnl": -8.0, "win_rate": 0.25},
        )
        assert mult <= 1.25
