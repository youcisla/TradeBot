"""Tests for agents/exposure_agent.py — ExposureCoach and ExposureDecision.

All external dependencies (DB, CrucixAgent, settings) are mocked so the
suite is fast and deterministic.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agents.exposure_agent import (
    ExposureCoach,
    ExposureDecision,
    _SESSION_SCORE_DEFAULT,
    _SESSION_SCORES,
)
from config import settings
from models.signal import Signal


# ── Helpers ───────────────────────────────────────────────────────────────

def _signal(**kwargs) -> Signal:
    defaults = dict(symbol="EURUSD", direction="BUY", confidence=0.70)
    defaults.update(kwargs)
    return Signal(**defaults)


def _trade(pnl: float = 100.0, symbol: str = "EURUSD", direction: str = "BUY"):
    t = MagicMock()
    t.pnl = pnl
    t.symbol = symbol
    t.direction = direction
    return t


# ── TestExposureDecision ──────────────────────────────────────────────────

class TestExposureDecision:
    def test_default_directive_is_new_entry_allowed(self):
        d = ExposureDecision()
        assert d.directive == "NEW_ENTRY_ALLOWED"

    def test_default_ceiling_is_one(self):
        d = ExposureDecision()
        assert d.exposure_ceiling_pct == 1.0

    def test_skipped_defaults_to_false(self):
        d = ExposureDecision()
        assert d.skipped is False

    def test_all_directives_are_valid(self):
        for directive in ("NEW_ENTRY_ALLOWED", "REDUCE_ONLY", "CASH_PRIORITY"):
            d = ExposureDecision(directive=directive)
            assert d.directive == directive


# ── TestExposureCoachInit ─────────────────────────────────────────────────

class TestExposureCoachInit:
    def test_init_no_args(self):
        coach = ExposureCoach()
        assert coach._db is None
        assert coach._crucix is None

    def test_init_with_dependencies(self):
        db = MagicMock()
        crucix = MagicMock()
        coach = ExposureCoach(db=db, crucix_agent=crucix)
        assert coach._db is db
        assert coach._crucix is crucix


# ── TestScorePnl ──────────────────────────────────────────────────────────

class TestScorePnl:
    def test_no_db_returns_neutral(self):
        coach = ExposureCoach()
        assert coach._score_pnl(account_equity=10_000.0) == 0.5

    def test_no_trades_today_returns_one(self):
        db = MagicMock()
        db.get_trades_closed_today.return_value = []
        coach = ExposureCoach(db=db)
        assert coach._score_pnl(account_equity=10_000.0) == 1.0

    def test_only_winning_trades_returns_one(self):
        db = MagicMock()
        db.get_trades_closed_today.return_value = [_trade(pnl=200.0)]
        coach = ExposureCoach(db=db)
        assert coach._score_pnl(account_equity=10_000.0) == 1.0

    def test_loss_reduces_score_linearly(self):
        db = MagicMock()
        db.get_trades_closed_today.return_value = [_trade(pnl=-100.0)]
        coach = ExposureCoach(db=db)
        with patch.object(settings, "MAX_DAILY_LOSS", 0.02):
            # loss_pct = 100/10000 = 0.01; limit = 0.02 → score = 0.5
            score = coach._score_pnl(account_equity=10_000.0)
            assert 0.0 < score < 1.0


# ── TestScoreOpenCount ────────────────────────────────────────────────────

class TestScoreOpenCount:
    def test_zero_trades_returns_one(self):
        coach = ExposureCoach()
        with patch.object(settings, "MAX_OPEN_TRADES", 5):
            assert coach._score_open_count([]) == 1.0

    def test_at_max_returns_zero(self):
        coach = ExposureCoach()
        trades = [MagicMock() for _ in range(5)]
        with patch.object(settings, "MAX_OPEN_TRADES", 5):
            assert coach._score_open_count(trades) == 0.0

    def test_half_max_returns_half(self):
        coach = ExposureCoach()
        trades = [MagicMock() for _ in range(3)]
        with patch.object(settings, "MAX_OPEN_TRADES", 6):
            score = coach._score_open_count(trades)
            assert round(score, 4) == 0.5


# ── TestScoreGarchVol ─────────────────────────────────────────────────────

class TestScoreGarchVol:
    def test_none_ratio_returns_neutral(self):
        coach = ExposureCoach()
        assert coach._score_garch_vol(None) == 0.5

    def test_ratio_at_one_returns_one(self):
        coach = ExposureCoach()
        with patch.object(settings, "GARCH_HIGH_VOL_THRESHOLD", 2.0):
            assert coach._score_garch_vol(1.0) == 1.0

    def test_ratio_below_one_returns_one(self):
        coach = ExposureCoach()
        with patch.object(settings, "GARCH_HIGH_VOL_THRESHOLD", 2.0):
            assert coach._score_garch_vol(0.5) == 1.0

    def test_ratio_at_threshold_returns_zero(self):
        coach = ExposureCoach()
        with patch.object(settings, "GARCH_HIGH_VOL_THRESHOLD", 2.0):
            assert coach._score_garch_vol(2.0) == 0.0

    def test_ratio_halfway_interpolates(self):
        coach = ExposureCoach()
        with patch.object(settings, "GARCH_HIGH_VOL_THRESHOLD", 2.0):
            # ratio=1.5 is halfway between 1.0 and 2.0 → score ≈ 0.5
            score = coach._score_garch_vol(1.5)
            assert 0.4 < score < 0.6


# ── TestScoreCrucix ───────────────────────────────────────────────────────

class TestScoreCrucix:
    def test_no_crucix_returns_neutral(self):
        coach = ExposureCoach()
        assert coach._score_crucix(_signal()) == 0.5

    def test_low_tier_returns_one(self):
        macro = MagicMock()
        macro.risk_tier = "low"
        crucix = MagicMock()
        crucix.get_context.return_value = macro
        coach = ExposureCoach(crucix_agent=crucix)
        assert coach._score_crucix(_signal()) == 1.0

    def test_high_tier_returns_low_score(self):
        macro = MagicMock()
        macro.risk_tier = "high"
        crucix = MagicMock()
        crucix.get_context.return_value = macro
        coach = ExposureCoach(crucix_agent=crucix)
        assert coach._score_crucix(_signal()) == 0.30

    def test_blackout_tier_returns_zero(self):
        macro = MagicMock()
        macro.risk_tier = "blackout"
        crucix = MagicMock()
        crucix.get_context.return_value = macro
        coach = ExposureCoach(crucix_agent=crucix)
        assert coach._score_crucix(_signal()) == 0.0


# ── TestScoreSession ──────────────────────────────────────────────────────

class TestScoreSession:
    def test_london_ny_overlap_returns_one(self):
        sig = _signal()
        sig.entry_snapshot.session = "London-NY"
        coach = ExposureCoach()
        assert coach._score_session(sig) == 1.0

    def test_asian_session_returns_050(self):
        sig = _signal()
        sig.entry_snapshot.session = "Asian"
        coach = ExposureCoach()
        assert coach._score_session(sig) == 0.50

    def test_unknown_session_returns_default(self):
        sig = _signal()
        sig.entry_snapshot.session = "OffHours"
        coach = ExposureCoach()
        assert coach._score_session(sig) == _SESSION_SCORE_DEFAULT


# ── TestScoreWinRate ──────────────────────────────────────────────────────

class TestScoreWinRate:
    def test_no_db_returns_neutral(self):
        coach = ExposureCoach()
        assert coach._score_win_rate() == 0.5

    def test_no_trades_returns_neutral(self):
        db = MagicMock()
        db.get_closed_trades_since.return_value = []
        coach = ExposureCoach(db=db)
        with patch.object(settings, "EXPOSURE_WIN_RATE_LOOKBACK", 10):
            assert coach._score_win_rate() == 0.5

    def test_good_win_rate_returns_high_score(self):
        # 8 wins, 2 losses → 80 % win rate → score = 1.0
        db = MagicMock()
        db.get_closed_trades_since.return_value = (
            [_trade(pnl=100.0) for _ in range(8)]
            + [_trade(pnl=-50.0) for _ in range(2)]
        )
        coach = ExposureCoach(db=db)
        with patch.object(settings, "EXPOSURE_WIN_RATE_LOOKBACK", 10):
            score = coach._score_win_rate()
            assert score > 0.7

    def test_poor_win_rate_returns_zero(self):
        # 2 wins, 8 losses → 20 % win rate → below 30 % floor → 0.0
        db = MagicMock()
        db.get_closed_trades_since.return_value = (
            [_trade(pnl=-50.0) for _ in range(8)]
            + [_trade(pnl=100.0) for _ in range(2)]
        )
        coach = ExposureCoach(db=db)
        with patch.object(settings, "EXPOSURE_WIN_RATE_LOOKBACK", 10):
            assert coach._score_win_rate() == 0.0


# ── TestScoreLgbmConfidence ───────────────────────────────────────────────

class TestScoreLgbmConfidence:
    def test_high_confidence(self):
        coach = ExposureCoach()
        assert coach._score_lgbm_confidence(_signal(confidence=0.9)) == 0.9

    def test_low_confidence(self):
        coach = ExposureCoach()
        assert coach._score_lgbm_confidence(_signal(confidence=0.3)) == 0.3


# ── TestComputeDirective ──────────────────────────────────────────────────

class TestComputeDirective:
    _KEYS = ["pnl", "open_count", "garch_vol", "crucix",
             "correlation", "session", "win_rate", "lgbm_conf"]

    def test_high_scores_produce_new_entry_allowed(self):
        coach = ExposureCoach()
        scores = {k: 0.9 for k in self._KEYS}
        with patch.object(settings, "EXPOSURE_REDUCE_THRESHOLD", 0.40), \
             patch.object(settings, "EXPOSURE_CASH_THRESHOLD", 0.20):
            d = coach._compute_directive(scores)
            assert d.directive == "NEW_ENTRY_ALLOWED"

    def test_moderate_scores_produce_reduce_only(self):
        coach = ExposureCoach()
        scores = {k: 0.30 for k in self._KEYS}
        with patch.object(settings, "EXPOSURE_REDUCE_THRESHOLD", 0.40), \
             patch.object(settings, "EXPOSURE_CASH_THRESHOLD", 0.20):
            d = coach._compute_directive(scores)
            assert d.directive == "REDUCE_ONLY"

    def test_low_scores_produce_cash_priority(self):
        coach = ExposureCoach()
        scores = {k: 0.05 for k in self._KEYS}
        with patch.object(settings, "EXPOSURE_REDUCE_THRESHOLD", 0.40), \
             patch.object(settings, "EXPOSURE_CASH_THRESHOLD", 0.20):
            d = coach._compute_directive(scores)
            assert d.directive == "CASH_PRIORITY"


# ── TestEvaluate ──────────────────────────────────────────────────────────

class TestEvaluate:
    _COMMON_PATCHES = dict(
        EXPOSURE_ENABLED=True,
        EXPOSURE_REDUCE_THRESHOLD=0.40,
        EXPOSURE_CASH_THRESHOLD=0.20,
        MAX_OPEN_TRADES=5,
        MAX_DAILY_LOSS=0.02,
        GARCH_HIGH_VOL_THRESHOLD=2.0,
        EXPOSURE_WIN_RATE_LOOKBACK=10,
    )

    def test_disabled_returns_skipped(self):
        coach = ExposureCoach()
        with patch.object(settings, "EXPOSURE_ENABLED", False):
            d = coach.evaluate(_signal())
            assert d.skipped is True

    def test_evaluate_never_raises(self):
        db = MagicMock()
        db.get_trades_closed_today.side_effect = RuntimeError("DB down")
        db.get_closed_trades_since.side_effect = RuntimeError("DB down")
        coach = ExposureCoach(db=db)
        patches = {k: v for k, v in self._COMMON_PATCHES.items()}
        with patch.multiple(settings, **patches):
            result = coach.evaluate(_signal())
            assert isinstance(result, ExposureDecision)

    def test_open_trades_none_defaults_to_empty(self):
        coach = ExposureCoach()
        with patch.multiple(settings, **self._COMMON_PATCHES):
            result = coach.evaluate(_signal(), open_trades=None)
            assert isinstance(result, ExposureDecision)

    def test_full_round_trip_high_confidence_no_open_trades(self):
        """High confidence with empty positions → NEW_ENTRY_ALLOWED regardless of session."""
        coach = ExposureCoach()
        with patch.multiple(settings, **self._COMMON_PATCHES):
            # When DB is None: pnl=0.5, win_rate=0.5, and other scores
            # are neutral/good.  Composite stays well above 0.40.
            result = coach.evaluate(_signal(confidence=0.9), open_trades=[])
            assert result.directive == "NEW_ENTRY_ALLOWED"
            assert result.skipped is False

    def test_scorer_exception_returns_skipped(self):
        """If a scorer throws, the outer try/except catches it → skipped=True."""
        coach = ExposureCoach()
        with patch.object(coach, "_score_pnl", side_effect=Exception("boom")), \
             patch.object(settings, "EXPOSURE_ENABLED", True):
            result = coach.evaluate(_signal())
            assert result.skipped is True


# ── TestExposureSettings ──────────────────────────────────────────────────

class TestExposureSettings:
    def test_exposure_enabled_is_bool(self):
        assert isinstance(settings.EXPOSURE_ENABLED, bool)

    def test_thresholds_in_valid_range(self):
        assert 0.0 < settings.EXPOSURE_CASH_THRESHOLD < 1.0
        assert 0.0 < settings.EXPOSURE_REDUCE_THRESHOLD < 1.0

    def test_cash_threshold_less_than_reduce_threshold(self):
        assert settings.EXPOSURE_CASH_THRESHOLD < settings.EXPOSURE_REDUCE_THRESHOLD

    def test_win_rate_lookback_is_positive(self):
        assert settings.EXPOSURE_WIN_RATE_LOOKBACK > 0
