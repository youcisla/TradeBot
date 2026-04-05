"""Tests for CouncilAgent."""

from unittest.mock import patch

import pytest

from agents.council_agent import CouncilAgent, CouncilVerdict, ExpertVerdict
from tests.conftest import make_candles, make_signal


def _make_context(candle_count: int = 60, atr: float = 0.0010):
    """Build a minimal MarketContext-like object for council tests."""
    from models.market_data import MarketContext
    candles = make_candles(candle_count)
    return MarketContext(
        symbol="EURUSD",
        timeframe="H1",
        candles=candles,
        current_price=1.1060,
        spread=0.00015,
        atr=atr,
        trend="bullish",
        rsi=55.0,
        session="London",
        is_trending=True,
    )


@pytest.fixture
def council() -> CouncilAgent:
    return CouncilAgent()


def test_review_returns_verdict(council: CouncilAgent) -> None:
    signal = make_signal()
    ctx = _make_context()
    verdict = council.review(signal, ctx)
    assert isinstance(verdict, CouncilVerdict)
    assert 0.0 <= verdict.confidence <= 1.0
    assert verdict.direction in ("BUY", "SELL")


def test_review_insufficient_candles_rejects(council: CouncilAgent) -> None:
    signal = make_signal()
    ctx = _make_context(candle_count=5)
    verdict = council.review(signal, ctx)
    assert verdict.approved is False
    assert "Insufficient" in verdict.reasoning


def test_review_fails_open_on_exception(council: CouncilAgent) -> None:
    """Council should approve (fail open) when an unexpected error occurs."""
    signal = make_signal()
    ctx = _make_context()
    with patch.object(council, "_run_council", side_effect=RuntimeError("boom")):
        verdict = council.review(signal, ctx)
    assert verdict.approved is True


def test_review_confidence_range(council: CouncilAgent) -> None:
    """Confidence must always be between 0 and 1."""
    signal = make_signal(direction="SELL")
    ctx = _make_context()
    verdict = council.review(signal, ctx)
    assert 0.0 <= verdict.confidence <= 1.0


def test_review_direction_matches_signal(council: CouncilAgent) -> None:
    signal = make_signal(direction="BUY")
    ctx = _make_context()
    verdict = council.review(signal, ctx)
    assert verdict.direction == "BUY"


def test_review_has_reasons(council: CouncilAgent) -> None:
    signal = make_signal()
    ctx = _make_context()
    verdict = council.review(signal, ctx)
    # At least one expert should produce a reason
    total_reasons = len(verdict.reasons_for) + len(verdict.reasons_against)
    assert total_reasons > 0


def test_review_risk_debate_is_deterministic(council: CouncilAgent) -> None:
    signal = make_signal()
    ctx = _make_context()

    with patch.object(council._ict, "analyse", return_value=ExpertVerdict(score=0.9)):
        with patch.object(council._danial, "analyse", return_value=ExpertVerdict(score=0.8)):
            with patch.object(council._traditional, "analyse", return_value=ExpertVerdict(score=0.7)):
                with patch.object(council._world, "analyse", return_value=ExpertVerdict(score=0.6)):
                    verdict1 = council.review(signal, ctx)
                    verdict2 = council.review(signal, ctx)

    assert verdict1.risk_recommendation == verdict2.risk_recommendation
    assert verdict1.risk_views == verdict2.risk_views
    assert verdict1.trace_id != ""
