"""Bull/Bear Debate Agent — LLM-powered pre-trade quality gate.

For every signal that survives the LGBM filter, this agent presents the
setup to two synthetic analysts via a single LLM call:

- **Bull analyst** — writes 3 specific arguments FOR taking the trade.
- **Bear analyst** — writes 3 specific arguments AGAINST the trade.

Their self-assigned scores feed a ``verdict``:
- **PROCEED** — confidence boosted +5 %
- **CAUTIOUS** — confidence dampened -10 %
- **SKIP**     — confidence dampened -25 % (bear dominated the debate)

The agent **never blocks trading on failure**.  If the LLM is unavailable
or times out, ``evaluate()`` returns ``DebateResult(skipped=True)`` and the
signal passes through with no confidence change.

Bull/bear text is stored on ``signal.bull_case`` / ``signal.bear_case`` so
ExecutionAgent can persist it into the ``trade_theses`` DB table.

Configure via environment:
- ``DEBATE_ENABLED=true``            (default ``false``)
- ``DEBATE_LLM_MODEL=<model name>``  (empty → inherits ``OPENROUTER_MODEL``)
- ``DEBATE_TIMEOUT_SECONDS=8``
- ``DEBATE_BEAR_VETO_THRESHOLD=0.75``   (bear_score >= this → SKIP)
- ``DEBATE_BEAR_CAUTION_THRESHOLD=0.60`` (bear_score >= this → CAUTIOUS)
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from config import settings

if TYPE_CHECKING:
    from models.signal import Signal

logger = logging.getLogger(__name__)

# ── Prompt template ───────────────────────────────────────────────────────────

_DEBATE_PROMPT = """\
Signal context:
- Symbol:     {symbol}
- Direction:  {direction}
- Entry:      {entry_price}
- Stop Loss:  {stop_loss}
- TP1/TP3:    {tp1} / {tp3}
- Risk:Reward (entry→TP3): {rr}
- Strategy:   {strategy}
- Confidence: {confidence:.0%}
- Reason:     {reason}
- Session: {session}  Day: {day_of_week}  Market: {market_condition}

You are two trading analysts debating whether to take this trade.

## BULL
(Bull analyst) Write exactly 3 numbered arguments FOR this trade.
Cite specific price levels, patterns, or RR. Max 70 words total.

## BEAR
(Bear analyst) Write exactly 3 numbered arguments AGAINST this trade.
Cite specific risks, fake-out scenarios, or cost vs reward. Max 70 words total.

## SCORES
Output a JSON block — nothing else after it:
```json
{{"bull_score": <0.0-1.0>, "bear_score": <0.0-1.0>}}
```
"""


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class DebateResult:
    """Outcome of one bull/bear LLM debate round."""

    bull_case: str = ""
    bear_case: str = ""
    bull_score: float = 0.5
    bear_score: float = 0.5
    verdict: Literal["PROCEED", "CAUTIOUS", "SKIP"] = "PROCEED"
    # True when the agent was disabled or the LLM call failed.
    # signal.confidence is NOT changed when skipped=True.
    skipped: bool = False


# ══════════════════════════════════════════════════════════════════════════════
# Agent
# ══════════════════════════════════════════════════════════════════════════════

class BullBearDebateAgent:
    """One-shot LLM debate that adjusts ``signal.confidence`` before execution.

    Usage::

        debate = BullBearDebateAgent(db=db)
        result = debate.evaluate(signal)
        # signal.confidence has been updated; signal.bull_case/bear_case populated
    """

    def __init__(self, db: object | None = None) -> None:
        self._db = db

    # ── Public API ────────────────────────────────────────────────────────

    def evaluate(self, signal: "Signal") -> DebateResult:
        """Run LLM debate on *signal*, adjust confidence, return DebateResult.

        Never raises — returns ``DebateResult(skipped=True)`` on any error.
        """
        if not getattr(settings, "DEBATE_ENABLED", False):
            return DebateResult(skipped=True)

        try:
            return self._run_debate(signal)
        except Exception:
            logger.debug("BullBearDebateAgent.evaluate failed (non-fatal)", exc_info=True)
            return DebateResult(skipped=True)

    # ── Internal flow ─────────────────────────────────────────────────────

    def _run_debate(self, signal: "Signal") -> DebateResult:
        prompt = self._build_prompt(signal)
        raw = self._call_llm(prompt)
        result = self._parse_response(raw)
        self._apply_verdict(signal, result)
        self._log(signal, result)
        return result

    # ── Prompt construction ───────────────────────────────────────────────

    @staticmethod
    def _build_prompt(signal: "Signal") -> str:
        snap = signal.entry_snapshot
        sl_dist = abs(signal.entry_price - signal.stop_loss)
        tp3_or_best = signal.take_profit_3 or signal.take_profit_2 or signal.take_profit_1
        tp3_dist = abs(tp3_or_best - signal.entry_price) if tp3_or_best else 0.0
        rr = f"{tp3_dist / sl_dist:.1f}:1" if sl_dist > 0 else "N/A"
        reason = (getattr(signal, "reason", "") or "")[:200]
        return _DEBATE_PROMPT.format(
            symbol=signal.symbol,
            direction=signal.direction,
            entry_price=f"{signal.entry_price:.5f}",
            stop_loss=f"{signal.stop_loss:.5f}",
            tp1=f"{signal.take_profit_1:.5f}" if signal.take_profit_1 else "N/A",
            tp3=f"{tp3_or_best:.5f}" if tp3_or_best else "N/A",
            rr=rr,
            strategy=signal.strategy or "unknown",
            confidence=signal.confidence,
            reason=reason,
            session=snap.session if snap else "",
            day_of_week=snap.day_of_week if snap else "",
            market_condition=snap.market_condition if snap else "",
        )

    # ── LLM call ─────────────────────────────────────────────────────────

    @staticmethod
    def _call_llm(prompt: str) -> str:
        """POST to OpenRouter.  Raises on HTTP/timeout error."""
        import urllib.request

        api_key: str = getattr(settings, "OPENROUTER_API_KEY", "")
        base_url: str = getattr(
            settings, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        )
        model: str = (
            getattr(settings, "DEBATE_LLM_MODEL", "") or
            getattr(settings, "OPENROUTER_MODEL", "anthropic/claude-3-haiku")
        )
        timeout: int = int(getattr(settings, "DEBATE_TIMEOUT_SECONDS", 8))

        if not api_key:
            raise RuntimeError("OPENROUTER_API_KEY not configured — debate skipped")

        payload = json.dumps({
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500,
            "temperature": 0.4,
        }).encode()

        req = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/tradebot/debate",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            body = json.loads(resp.read().decode())
        return body["choices"][0]["message"]["content"]

    # ── Response parsing ──────────────────────────────────────────────────

    @classmethod
    def _parse_response(cls, raw: str) -> DebateResult:
        """Extract bull/bear text and scores from the LLM response."""
        result = DebateResult()

        bull_m = re.search(
            r"##\s*BULL\s*\n(.*?)(?=##\s*BEAR|##\s*SCORES|$)", raw, re.S | re.I
        )
        bear_m = re.search(
            r"##\s*BEAR\s*\n(.*?)(?=##\s*BULL|##\s*SCORES|$)", raw, re.S | re.I
        )
        result.bull_case = bull_m.group(1).strip() if bull_m else ""
        result.bear_case = bear_m.group(1).strip() if bear_m else ""

        json_m = re.search(r"```json\s*(\{.*?\})\s*```", raw, re.S)
        if json_m:
            try:
                scores = json.loads(json_m.group(1))
                result.bull_score = max(0.0, min(1.0, float(scores.get("bull_score", 0.5))))
                result.bear_score = max(0.0, min(1.0, float(scores.get("bear_score", 0.5))))
            except (json.JSONDecodeError, ValueError, TypeError):
                pass  # keep defaults

        veto_thr: float = float(getattr(settings, "DEBATE_BEAR_VETO_THRESHOLD", 0.75))
        caution_thr: float = float(getattr(settings, "DEBATE_BEAR_CAUTION_THRESHOLD", 0.60))

        if result.bear_score >= veto_thr:
            result.verdict = "SKIP"
        elif result.bear_score >= caution_thr or result.bull_score < 0.40:
            result.verdict = "CAUTIOUS"
        else:
            result.verdict = "PROCEED"

        return result

    # ── Confidence mutation ───────────────────────────────────────────────

    @staticmethod
    def _apply_verdict(signal: "Signal", result: DebateResult) -> None:
        """Mutate ``signal.confidence`` and populate bull/bear case fields."""
        if result.verdict == "SKIP":
            signal.confidence = max(0.0, signal.confidence * 0.75)
        elif result.verdict == "CAUTIOUS":
            signal.confidence = max(0.0, signal.confidence * 0.90)
        else:  # PROCEED
            signal.confidence = min(1.0, signal.confidence * 1.05)

        signal.bull_case = result.bull_case
        signal.bear_case = result.bear_case

    # ── Logging ───────────────────────────────────────────────────────────

    def _log(self, signal: "Signal", result: DebateResult) -> None:
        logger.debug(
            "Debate %s %s: verdict=%s bull=%.2f bear=%.2f conf→%.3f",
            signal.symbol, signal.direction,
            result.verdict, result.bull_score, result.bear_score, signal.confidence,
        )
        if self._db:
            try:
                self._db.log_agent_event(
                    "debate", "info",
                    (
                        f"Debate {signal.symbol} {signal.direction}: "
                        f"verdict={result.verdict} "
                        f"bull={result.bull_score:.2f} bear={result.bear_score:.2f}"
                    ),
                    {
                        "symbol": signal.symbol,
                        "verdict": result.verdict,
                        "bull_score": result.bull_score,
                        "bear_score": result.bear_score,
                    },
                )
            except Exception:
                pass
