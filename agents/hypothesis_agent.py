"""HypothesisAgent — proposes, tests, and validates parameter hypotheses (DeepSeek)."""

from __future__ import annotations

import json
import logging
import subprocess
import tempfile
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)

_PROPOSE_SYSTEM = """\
You are a quantitative strategy researcher. Given recent trade learning data,
propose ONE specific, testable hypothesis about a parameter change that could
improve performance. Output ONLY valid JSON with keys:
  hypothesis (str), parameter (str), current_value (float),
  proposed_value (float), symbols (list[str]), rationale (str).
No preamble. No markdown fences.\
"""

_VERDICT_SYSTEM = """\
You are a quantitative analyst reviewing a backtest result.
Write 3 sentences: (1) confirmed or rejected, (2) key metric change,
(3) recommended action. No markdown.\
"""


class HypothesisAgent:
    def __init__(self, db) -> None:
        self._db = db

    def run_cycle(self) -> str:
        """Full cycle: propose -> backtest -> verdict. Returns plain-text result."""
        if not settings.DEEPSEEK_API_KEY:
            return "HypothesisAgent unavailable: DEEPSEEK_API_KEY not set."

        regime_stats = self._db.learning.get_recent_strategy_regime_stats(
            lookback_hours=48, min_trades=3
        )
        learning_data = {
            "regime_stats": regime_stats,
            "symbols": ["BTCUSD", "ETHUSD", "EURUSD"],
        }

        try:
            from openai import OpenAI
        except ImportError:
            return "HypothesisAgent: 'openai' package not installed."

        client = OpenAI(
            api_key=settings.DEEPSEEK_API_KEY,
            base_url="https://api.deepseek.com",
        )

        # 1. Propose hypothesis
        try:
            response = client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": _PROPOSE_SYSTEM},
                    {"role": "user",   "content": json.dumps(learning_data, default=str)},
                ],
                max_tokens=300,
            )
            proposal_raw = response.choices[0].message.content.strip()
        except Exception as exc:
            return f"HypothesisAgent: DeepSeek proposal failed: {exc}"

        try:
            proposal = json.loads(proposal_raw)
        except json.JSONDecodeError:
            return f"HypothesisAgent: malformed proposal JSON:\n{proposal_raw}"

        logger.info("Hypothesis proposed: %s", proposal.get("hypothesis"))

        # 2. Run backtest
        result_path = self._run_backtest(proposal)
        if result_path is None:
            return f"Hypothesis: {proposal['hypothesis']}\nBacktest failed to run."

        with open(result_path) as f:
            artifact = json.load(f)

        # 3. Get verdict
        try:
            verdict = client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=[
                    {"role": "system", "content": _VERDICT_SYSTEM},
                    {"role": "user",   "content": json.dumps({
                        "hypothesis": proposal,
                        "backtest_result": artifact,
                    }, default=str)},
                ],
                max_tokens=200,
            )
            verdict_text = verdict.choices[0].message.content.strip()
        except Exception as exc:
            return f"HypothesisAgent: DeepSeek verdict failed: {exc}"

        return f"🔬 *Hypothesis*: {proposal['hypothesis']}\n\n{verdict_text}"

    def _run_backtest(self, proposal: dict) -> Path | None:
        symbols = proposal.get("symbols", ["EURUSD"])
        symbols_str = ",".join(symbols[:5])

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as cfg_file:
            json.dump({"proposal": proposal}, cfg_file)
            cfg_path = cfg_file.name

        out_path = Path(cfg_path).with_suffix(".result.json")
        try:
            subprocess.run(
                ["python", "scripts/backtest.py",
                 "--symbols", symbols_str,
                 "--benchmark-out", str(out_path)],
                timeout=120,
                capture_output=True,
            )
            return out_path if out_path.exists() else None
        except subprocess.TimeoutExpired:
            logger.warning("Hypothesis backtest timed out after 120s")
            return None
        except subprocess.CalledProcessError as exc:
            logger.warning("Backtest subprocess failed: %s", exc.stderr)
            return None
