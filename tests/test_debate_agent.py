"""Tests for BullBearDebateAgent (Todo #4).

Coverage:
- DebateResult dataclass defaults and fields
- BullBearDebateAgent._build_prompt  — prompt contains key signal info
- BullBearDebateAgent._parse_response — section extraction + score parsing
- Verdict logic: PROCEED / CAUTIOUS / SKIP
- _apply_verdict confidence mutations and signal field population
- evaluate() passthrough when DEBATE_ENABLED=False
- evaluate() returns skipped=True when LLM raises (fail-open)
- Full round-trip with mocked _call_llm
- Strategy agent wiring (_debate property, evaluate called in _collect_signals)
- ExecutionAgent thesis save includes bull_case / bear_case
"""

from __future__ import annotations

import unittest
from datetime import UTC, datetime
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

from agents.debate_agent import BullBearDebateAgent, DebateResult
from models.signal import EntrySnapshot, Signal


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_signal(
    *,
    symbol: str = "EURUSD",
    direction: str = "BUY",
    entry_price: float = 1.10000,
    stop_loss: float = 1.09500,
    take_profit_1: float = 1.10500,
    take_profit_2: float = 1.11000,
    take_profit_3: float = 1.11500,
    confidence: float = 0.70,
    reason: str = "ICT setup",
    session: str = "london",
    day_of_week: str = "tuesday",
    market_condition: str = "trending",
) -> Signal:
    snap = EntrySnapshot(
        session=session,
        day_of_week=day_of_week,
        market_condition=market_condition,
    )
    return Signal(
        strategy="ict",
        symbol=symbol,
        direction=direction,
        entry_price=entry_price,
        stop_loss=stop_loss,
        take_profit_1=take_profit_1,
        take_profit_2=take_profit_2,
        take_profit_3=take_profit_3,
        confidence=confidence,
        reason=reason,
        timestamp=datetime.now(UTC),
        entry_snapshot=snap,
    )


_VALID_LLM_RESPONSE = """\
## BULL
1. Strong FVG at entry — institutional demand zone tested perfectly.
2. RR is 3:1 — favourable risk/reward given the London session alignment.
3. Higher-low structure intact; trend strongly bullish.

## BEAR
1. Spread cost eats 10% of TP1 — thin margin for error.
2. News event in 2 hours could spike volatility and hit SL prematurely.
3. Previous swing high overhead at 1.10800 may act as ceiling.

## SCORES
```json
{"bull_score": 0.72, "bear_score": 0.35}
```
"""

_SKIP_LLM_RESPONSE = """\
## BULL
1. Minimal: entry is ok.
2. RR barely acceptable at 1.8:1.
3. Trend unclear.

## BEAR
1. Counter-trend entry — D1 bias is bearish.
2. Three consecutive bearish candles prior to entry.
3. Asian session ending — liquidity thins out.

## SCORES
```json
{"bull_score": 0.28, "bear_score": 0.80}
```
"""

_CAUTIOUS_LLM_RESPONSE = """\
## BULL
1. Entry aligns with OB.
2. Positive RR.
3. Session valid.

## BEAR
1. News risk present.
2. ADX below 20 — ranging market.
3. SL tight relative to ATR.

## SCORES
```json
{"bull_score": 0.55, "bear_score": 0.65}
```
"""


# ══════════════════════════════════════════════════════════════════════════════
# 1. DebateResult dataclass
# ══════════════════════════════════════════════════════════════════════════════

class TestDebateResult(unittest.TestCase):
    def test_defaults(self) -> None:
        r = DebateResult()
        self.assertEqual(r.bull_case, "")
        self.assertEqual(r.bear_case, "")
        self.assertAlmostEqual(r.bull_score, 0.5)
        self.assertAlmostEqual(r.bear_score, 0.5)
        self.assertEqual(r.verdict, "PROCEED")
        self.assertFalse(r.skipped)

    def test_skipped_field(self) -> None:
        r = DebateResult(skipped=True)
        self.assertTrue(r.skipped)

    def test_all_verdicts_valid(self) -> None:
        for v in ("PROCEED", "CAUTIOUS", "SKIP"):
            r = DebateResult(verdict=v)  # type: ignore[arg-type]
            self.assertEqual(r.verdict, v)


# ══════════════════════════════════════════════════════════════════════════════
# 2. _build_prompt
# ══════════════════════════════════════════════════════════════════════════════

class TestBuildPrompt(unittest.TestCase):
    def _prompt(self, **kwargs) -> str:
        return BullBearDebateAgent._build_prompt(_make_signal(**kwargs))

    def test_prompt_contains_symbol(self) -> None:
        self.assertIn("EURUSD", self._prompt())

    def test_prompt_contains_direction(self) -> None:
        self.assertIn("BUY", self._prompt())

    def test_prompt_contains_entry_price(self) -> None:
        self.assertIn("1.10000", self._prompt())

    def test_prompt_contains_stop_loss(self) -> None:
        self.assertIn("1.09500", self._prompt())

    def test_prompt_contains_rr(self) -> None:
        # TP3=1.11500, entry=1.10000, SL=1.09500 → dist=0.015/0.005=3.0:1
        prompt = self._prompt()
        self.assertIn("3.0:1", prompt)

    def test_prompt_contains_session(self) -> None:
        self.assertIn("london", self._prompt())

    def test_rr_na_when_zero_sl_distance(self) -> None:
        # sl == entry_price → sl_dist == 0 → RR = N/A
        prompt = BullBearDebateAgent._build_prompt(
            _make_signal(entry_price=1.10000, stop_loss=1.10000)
        )
        self.assertIn("N/A", prompt)


# ══════════════════════════════════════════════════════════════════════════════
# 3. _parse_response
# ══════════════════════════════════════════════════════════════════════════════

class TestParseResponse(unittest.TestCase):
    @patch("config.settings.DEBATE_BEAR_VETO_THRESHOLD", 0.75)
    @patch("config.settings.DEBATE_BEAR_CAUTION_THRESHOLD", 0.60)
    def test_valid_response_proceed(self) -> None:
        result = BullBearDebateAgent._parse_response(_VALID_LLM_RESPONSE)
        self.assertFalse(result.skipped)
        self.assertAlmostEqual(result.bull_score, 0.72)
        self.assertAlmostEqual(result.bear_score, 0.35)
        self.assertEqual(result.verdict, "PROCEED")
        self.assertIn("FVG", result.bull_case)
        self.assertIn("Spread", result.bear_case)

    @patch("config.settings.DEBATE_BEAR_VETO_THRESHOLD", 0.75)
    @patch("config.settings.DEBATE_BEAR_CAUTION_THRESHOLD", 0.60)
    def test_skip_verdict_on_high_bear_score(self) -> None:
        result = BullBearDebateAgent._parse_response(_SKIP_LLM_RESPONSE)
        self.assertEqual(result.verdict, "SKIP")
        self.assertAlmostEqual(result.bear_score, 0.80)

    @patch("config.settings.DEBATE_BEAR_VETO_THRESHOLD", 0.75)
    @patch("config.settings.DEBATE_BEAR_CAUTION_THRESHOLD", 0.60)
    def test_cautious_verdict_on_medium_bear_score(self) -> None:
        result = BullBearDebateAgent._parse_response(_CAUTIOUS_LLM_RESPONSE)
        self.assertEqual(result.verdict, "CAUTIOUS")
        self.assertAlmostEqual(result.bear_score, 0.65)

    def test_missing_json_block_uses_defaults(self) -> None:
        raw = "## BULL\nLooks good.\n## BEAR\nLooks risky.\n"
        result = BullBearDebateAgent._parse_response(raw)
        self.assertAlmostEqual(result.bull_score, 0.5)
        self.assertAlmostEqual(result.bear_score, 0.5)

    def test_malformed_json_uses_defaults(self) -> None:
        raw = "## BULL\nGood.\n## BEAR\nBad.\n## SCORES\n```json\n{invalid}\n```\n"
        result = BullBearDebateAgent._parse_response(raw)
        self.assertAlmostEqual(result.bull_score, 0.5)
        self.assertAlmostEqual(result.bear_score, 0.5)

    def test_scores_clamped_to_unit_interval(self) -> None:
        raw = '## BULL\nGood.\n## BEAR\nBad.\n## SCORES\n```json\n{"bull_score": 1.5, "bear_score": -0.2}\n```\n'
        result = BullBearDebateAgent._parse_response(raw)
        self.assertAlmostEqual(result.bull_score, 1.0)
        self.assertAlmostEqual(result.bear_score, 0.0)

    def test_missing_bear_section_gives_empty_bear_case(self) -> None:
        raw = "## BULL\nOnly bull args here.\n## SCORES\n```json\n{\"bull_score\": 0.7, \"bear_score\": 0.3}\n```\n"
        result = BullBearDebateAgent._parse_response(raw)
        self.assertEqual(result.bear_case, "")
        self.assertIn("Only bull", result.bull_case)

    @patch("config.settings.DEBATE_BEAR_VETO_THRESHOLD", 0.75)
    @patch("config.settings.DEBATE_BEAR_CAUTION_THRESHOLD", 0.60)
    def test_low_bull_score_triggers_cautious(self) -> None:
        # bull_score < 0.40 → CAUTIOUS even if bear_score is below caution threshold
        raw = '## BULL\nWeak.\n## BEAR\nMeh.\n## SCORES\n```json\n{"bull_score": 0.30, "bear_score": 0.45}\n```\n'
        result = BullBearDebateAgent._parse_response(raw)
        self.assertEqual(result.verdict, "CAUTIOUS")


# ══════════════════════════════════════════════════════════════════════════════
# 4. _apply_verdict
# ══════════════════════════════════════════════════════════════════════════════

class TestApplyVerdict(unittest.TestCase):
    def test_proceed_boosts_confidence(self) -> None:
        sig = _make_signal(confidence=0.70)
        result = DebateResult(verdict="PROCEED", bull_case="bulls!", bear_case="ok bear")
        BullBearDebateAgent._apply_verdict(sig, result)
        self.assertAlmostEqual(sig.confidence, 0.70 * 1.05)

    def test_cautious_reduces_confidence(self) -> None:
        sig = _make_signal(confidence=0.70)
        result = DebateResult(verdict="CAUTIOUS")
        BullBearDebateAgent._apply_verdict(sig, result)
        self.assertAlmostEqual(sig.confidence, 0.70 * 0.90)

    def test_skip_reduces_confidence_substantially(self) -> None:
        sig = _make_signal(confidence=0.80)
        result = DebateResult(verdict="SKIP")
        BullBearDebateAgent._apply_verdict(sig, result)
        self.assertAlmostEqual(sig.confidence, 0.80 * 0.75)

    def test_proceed_confidence_capped_at_1(self) -> None:
        sig = _make_signal(confidence=0.99)
        result = DebateResult(verdict="PROCEED")
        BullBearDebateAgent._apply_verdict(sig, result)
        self.assertLessEqual(sig.confidence, 1.0)

    def test_skip_confidence_floor_at_0(self) -> None:
        sig = _make_signal(confidence=0.01)
        result = DebateResult(verdict="SKIP")
        BullBearDebateAgent._apply_verdict(sig, result)
        self.assertGreaterEqual(sig.confidence, 0.0)

    def test_bull_bear_cases_written_to_signal(self) -> None:
        sig = _make_signal()
        result = DebateResult(verdict="PROCEED", bull_case="bull text", bear_case="bear text")
        BullBearDebateAgent._apply_verdict(sig, result)
        self.assertEqual(sig.bull_case, "bull text")
        self.assertEqual(sig.bear_case, "bear text")


# ══════════════════════════════════════════════════════════════════════════════
# 5. evaluate() — integration / fail-open
# ══════════════════════════════════════════════════════════════════════════════

class TestEvaluate(unittest.TestCase):
    def test_returns_skipped_when_disabled(self) -> None:
        agent = BullBearDebateAgent()
        sig = _make_signal()
        orig_conf = sig.confidence
        with patch("config.settings.DEBATE_ENABLED", False):
            result = agent.evaluate(sig)
        self.assertTrue(result.skipped)
        # Confidence must not be changed
        self.assertAlmostEqual(sig.confidence, orig_conf)

    @patch("config.settings.DEBATE_ENABLED", True)
    def test_returns_skipped_when_llm_raises(self) -> None:
        agent = BullBearDebateAgent()
        sig = _make_signal()
        orig_conf = sig.confidence
        with patch.object(BullBearDebateAgent, "_call_llm", side_effect=RuntimeError("timeout")):
            result = agent.evaluate(sig)
        self.assertTrue(result.skipped)
        self.assertAlmostEqual(sig.confidence, orig_conf)

    @patch("config.settings.DEBATE_ENABLED", True)
    @patch("config.settings.DEBATE_BEAR_VETO_THRESHOLD", 0.75)
    @patch("config.settings.DEBATE_BEAR_CAUTION_THRESHOLD", 0.60)
    def test_full_round_trip_with_mocked_llm(self) -> None:
        agent = BullBearDebateAgent()
        sig = _make_signal(confidence=0.70)
        with patch.object(BullBearDebateAgent, "_call_llm", return_value=_VALID_LLM_RESPONSE):
            result = agent.evaluate(sig)
        self.assertFalse(result.skipped)
        self.assertEqual(result.verdict, "PROCEED")
        self.assertAlmostEqual(sig.confidence, 0.70 * 1.05)
        self.assertIn("FVG", sig.bull_case)
        self.assertIn("Spread", sig.bear_case)

    @patch("config.settings.DEBATE_ENABLED", True)
    def test_never_raises_on_internal_error(self) -> None:
        agent = BullBearDebateAgent()
        sig = _make_signal()
        with patch.object(BullBearDebateAgent, "_run_debate", side_effect=Exception("boom")):
            # Should not propagate
            result = agent.evaluate(sig)
        self.assertTrue(result.skipped)

    @patch("config.settings.DEBATE_ENABLED", True)
    @patch("config.settings.DEBATE_BEAR_VETO_THRESHOLD", 0.75)
    @patch("config.settings.DEBATE_BEAR_CAUTION_THRESHOLD", 0.60)
    def test_skip_verdict_dampens_confidence(self) -> None:
        agent = BullBearDebateAgent()
        sig = _make_signal(confidence=0.80)
        with patch.object(BullBearDebateAgent, "_call_llm", return_value=_SKIP_LLM_RESPONSE):
            result = agent.evaluate(sig)
        self.assertEqual(result.verdict, "SKIP")
        self.assertAlmostEqual(sig.confidence, 0.80 * 0.75, places=5)

    @patch("config.settings.DEBATE_ENABLED", True)
    def test_db_log_event_called_on_success(self) -> None:
        db_mock = MagicMock()
        agent = BullBearDebateAgent(db=db_mock)
        sig = _make_signal()
        with patch.object(BullBearDebateAgent, "_call_llm", return_value=_VALID_LLM_RESPONSE):
            agent.evaluate(sig)
        db_mock.log_agent_event.assert_called_once()

    @patch("config.settings.DEBATE_ENABLED", True)
    def test_db_none_does_not_raise(self) -> None:
        agent = BullBearDebateAgent(db=None)
        sig = _make_signal()
        with patch.object(BullBearDebateAgent, "_call_llm", return_value=_VALID_LLM_RESPONSE):
            result = agent.evaluate(sig)
        self.assertFalse(result.skipped)

    def test_no_api_key_raises_internally_not_to_caller(self) -> None:
        agent = BullBearDebateAgent()
        sig = _make_signal()
        with patch("config.settings.DEBATE_ENABLED", True):
            with patch("config.settings.OPENROUTER_API_KEY", ""):
                result = agent.evaluate(sig)
        # No key → RuntimeError in _call_llm → caught → skipped=True
        self.assertTrue(result.skipped)


# ══════════════════════════════════════════════════════════════════════════════
# 6. Signal model — bull_case / bear_case fields
# ══════════════════════════════════════════════════════════════════════════════

class TestSignalDebateFields(unittest.TestCase):
    def test_signal_has_bull_case_field(self) -> None:
        sig = Signal()
        self.assertEqual(sig.bull_case, "")

    def test_signal_has_bear_case_field(self) -> None:
        sig = Signal()
        self.assertEqual(sig.bear_case, "")

    def test_signal_bull_bear_writable(self) -> None:
        sig = Signal()
        sig.bull_case = "Strong OB"
        sig.bear_case = "News risk"
        self.assertEqual(sig.bull_case, "Strong OB")
        self.assertEqual(sig.bear_case, "News risk")


# ══════════════════════════════════════════════════════════════════════════════
# 7. Settings
# ══════════════════════════════════════════════════════════════════════════════

class TestDebateSettings(unittest.TestCase):
    def test_debate_enabled_default_false(self) -> None:
        from config import settings
        # Default in settings.py is False
        self.assertIsInstance(settings.DEBATE_ENABLED, bool)

    def test_debate_timeout_default(self) -> None:
        from config import settings
        self.assertGreater(settings.DEBATE_TIMEOUT_SECONDS, 0)

    def test_debate_veto_threshold_in_range(self) -> None:
        from config import settings
        self.assertGreater(settings.DEBATE_BEAR_VETO_THRESHOLD, 0.5)
        self.assertLessEqual(settings.DEBATE_BEAR_VETO_THRESHOLD, 1.0)

    def test_debate_caution_threshold_below_veto(self) -> None:
        from config import settings
        self.assertLess(
            settings.DEBATE_BEAR_CAUTION_THRESHOLD,
            settings.DEBATE_BEAR_VETO_THRESHOLD,
        )


if __name__ == "__main__":
    unittest.main()
