"""SSRT Agent — Sequential Strategy Retirement Testing via mSPRT.

Wraps the TradeMemory SSRT module (Johari et al. 2017 mixture SPRT) into
the TradeBot agent pipeline.  Each strategy × symbol pair gets its own
MixtureSPRT instance with regime-aware null hypothesis.

Regime mapping
─────────────
Combines AnalysisAgent trend_direction (bullish/bearish/neutral) with
GarchRegimeDetector volatility (low/normal/high/extreme) to produce the
four SSRT regimes:

  trending_up   — bullish trend  + normal/low GARCH
  trending_down — bearish trend + normal/low GARCH
  ranging       — neutral trend + normal/low GARCH
  volatile      — high/extreme GARCH volatility (any trend)

This is the Option B approach: evidence is preserved across regime changes
via shift_null(), rather than discarded via reset().

Pipeline position: runs after learning_agent.review_trade() so it receives
post-trade R-multiples with confirmed regime labels.
"""

from __future__ import annotations

import logging
import math
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from config import settings
from utils.mesh_bus import record_call

if TYPE_CHECKING:
    from database.db import Database

logger = logging.getLogger(__name__)

# ── Regime constants ──────────────────────────────────────────────────────────

VALID_REGIMES = {"trending_up", "trending_down", "ranging", "volatile"}

# ── Data models ──────────────────────────────────────────────────────────────


@dataclass
class TradeResult:
    """Single trade outcome for sequential testing."""

    pnl: float
    pnl_r: float  # R-multiple (risk-adjusted)
    regime: str
    timestamp: str
    strategy: str
    symbol: str


@dataclass
class SSRTVerdict:
    """Result of a single sequential test update."""

    decision: str  # "CONTINUE" | "RETIRE" | "INCONCLUSIVE"
    p_value: float
    lambda_n: float
    trades_analyzed: int
    regime: str
    null_mean: float


@dataclass
class RegimeBaseline:
    """Per-regime performance baseline for null hypothesis."""

    regime: str
    mean_pnl_r: float
    std_pnl_r: float
    trade_count: int
    last_updated: str


@dataclass
class RetirementReport:
    """Full report for strategy retirement analysis."""

    strategy: str
    symbol: str
    verdict: SSRTVerdict
    regime_baselines: dict = field(default_factory=dict)
    baseline_comparison: dict = field(default_factory=dict)
    history: list = field(default_factory=list)


# ── MixtureSPRT core ─────────────────────────────────────────────────────────


class MixtureSPRT:
    """Mixture Sequential Probability Ratio Test with always-valid p-values.

    Uses a Gaussian mixing distribution over the alternative hypothesis,
    yielding a closed-form likelihood ratio that can be updated incrementally.
    Reference: Johari et al. 2017, "Peeking at A/B Tests".

    Args:
        alpha: Significance level (Type I error rate).
        tau: Mixing distribution scale.  Controls sensitivity:
            small tau = detect small effects (more trades needed),
            large tau = detect large effects (fewer trades).
        sigma: Assumed observation std (estimated from history).
        null_mean: Baseline mean under H0 (regime-dependent).
        burn_in: Minimum trades before making decisions.
    """

    def __init__(
        self,
        alpha: float = 0.05,
        tau: float = 1.0,
        sigma: float = 1.5,
        null_mean: float = 0.0,
        burn_in: int = 20,
    ):
        if alpha <= 0 or alpha >= 1:
            raise ValueError("alpha must be in (0, 1)")
        if tau <= 0:
            raise ValueError("tau must be positive")
        if sigma <= 0:
            raise ValueError("sigma must be positive")
        if burn_in < 0:
            raise ValueError("burn_in must be non-negative")

        self.alpha = alpha
        self.tau = tau
        self.sigma = sigma
        self.null_mean = null_mean
        self.burn_in = burn_in

        self.n: int = 0
        self.sum_z: float = 0.0
        self.sum_z_sq: float = 0.0
        self._log_lambda: float = 0.0

    def update(self, observation: float) -> SSRTVerdict:
        """Process one trade R-multiple, update statistics, return verdict."""
        z = observation - self.null_mean
        self.n += 1
        self.sum_z += z
        self.sum_z_sq += z * z

        z_bar = self.sum_z / self.n
        sigma_sq = self.sigma ** 2
        tau_sq = self.tau ** 2
        n = self.n

        ratio = n * tau_sq / sigma_sq
        self._log_lambda = (
            -0.5 * math.log(1.0 + ratio)
            + (n * n * tau_sq * z_bar * z_bar)
            / (2.0 * sigma_sq * (sigma_sq + n * tau_sq))
        )

        lambda_n = math.exp(min(self._log_lambda, 500.0))
        p_value = 1.0 / max(1.0, lambda_n)

        # One-sided: only flag retirement when mean is BELOW null
        if z_bar >= 0:
            lambda_n = 1.0
            p_value = 1.0

        if self.n < self.burn_in:
            decision = "INCONCLUSIVE"
        elif p_value < self.alpha:
            decision = "RETIRE"
        else:
            decision = "CONTINUE"

        return SSRTVerdict(
            decision=decision,
            p_value=p_value,
            lambda_n=lambda_n,
            trades_analyzed=self.n,
            regime="unknown",
            null_mean=self.null_mean,
        )

    def shift_null(self, new_null_mean: float, new_sigma: float | None = None) -> None:
        """Adjust null hypothesis without resetting accumulated evidence (Option B).

        Shifts running statistics to account for a new baseline mean while
        preserving accumulated evidence (n, sum_z, log_lambda).
        """
        if self.n == 0:
            self.null_mean = new_null_mean
            if new_sigma is not None:
                if new_sigma <= 0:
                    raise ValueError("sigma must be positive")
                self.sigma = new_sigma
            return

        delta = self.null_mean - new_null_mean

        self.sum_z_sq += 2.0 * delta * self.sum_z + self.n * delta * delta
        self.sum_z += self.n * delta

        self.null_mean = new_null_mean
        if new_sigma is not None:
            if new_sigma <= 0:
                raise ValueError("sigma must be positive")
            self.sigma = new_sigma

        z_bar = self.sum_z / self.n
        sigma_sq = self.sigma ** 2
        tau_sq = self.tau ** 2
        n = self.n
        ratio = n * tau_sq / sigma_sq
        self._log_lambda = (
            -0.5 * math.log(1.0 + ratio)
            + (n * n * tau_sq * z_bar * z_bar)
            / (2.0 * sigma_sq * (sigma_sq + n * tau_sq))
        )

    def reset(self, null_mean: float = 0.0, sigma: float | None = None) -> None:
        """Reset all accumulated evidence (e.g. on strategy restart)."""
        self.null_mean = null_mean
        if sigma is not None:
            if sigma <= 0:
                raise ValueError("sigma must be positive")
            self.sigma = sigma
        self.n = 0
        self.sum_z = 0.0
        self.sum_z_sq = 0.0
        self._log_lambda = 0.0

    def get_state(self) -> dict[str, Any]:
        """Serialize for persistence."""
        return {
            "alpha": self.alpha,
            "tau": self.tau,
            "sigma": self.sigma,
            "null_mean": self.null_mean,
            "burn_in": self.burn_in,
            "n": self.n,
            "sum_z": self.sum_z,
            "sum_z_sq": self.sum_z_sq,
            "log_lambda": self._log_lambda,
        }

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "MixtureSPRT":
        """Restore from serialized state."""
        obj = cls(
            alpha=state["alpha"],
            tau=state["tau"],
            sigma=state["sigma"],
            null_mean=state["null_mean"],
            burn_in=state["burn_in"],
        )
        obj.n = state["n"]
        obj.sum_z = state["sum_z"]
        obj.sum_z_sq = state["sum_z_sq"]
        obj._log_lambda = state["log_lambda"]
        return obj


# ── Regime-aware null ────────────────────────────────────────────────────────


class RegimeAwareNull:
    """Maintain per-regime performance baselines via Welford's online algorithm.

    When a regime has sufficient data (>= min_trades_per_regime), its mean
    is used as the null hypothesis.  Otherwise falls back to default_null.
    """

    VALID_REGIMES = VALID_REGIMES

    def __init__(self, min_trades_per_regime: int = 10, default_null: float = 0.0):
        self.min_trades_per_regime = min_trades_per_regime
        self.default_null = default_null
        self._accumulators: dict[str, dict[str, float]] = {}
        self._last_updated: dict[str, str] = {}

    def _validate_regime(self, regime: str) -> None:
        if regime not in self.VALID_REGIMES:
            raise ValueError(f"Unknown regime '{regime}'. Valid: {sorted(self.VALID_REGIMES)}")

    def update(self, trade: TradeResult) -> None:
        """Update regime baseline with new trade using Welford's algorithm."""
        self._validate_regime(trade.regime)
        regime = trade.regime

        if regime not in self._accumulators:
            self._accumulators[regime] = {"n": 0.0, "mean": 0.0, "m2": 0.0}

        acc = self._accumulators[regime]
        acc["n"] += 1
        n = acc["n"]
        delta = trade.pnl_r - acc["mean"]
        acc["mean"] += delta / n
        delta2 = trade.pnl_r - acc["mean"]
        acc["m2"] += delta * delta2

        self._last_updated[regime] = trade.timestamp

    def get_null(self, regime: str) -> tuple[float, float]:
        """Return (null_mean, sigma) for given regime."""
        self._validate_regime(regime)

        acc = self._accumulators.get(regime)

        if acc is None or acc["n"] < self.min_trades_per_regime:
            pooled_sigma = self._pooled_sigma()
            return (self.default_null, pooled_sigma if pooled_sigma > 0 else 1.5)

        n = acc["n"]
        mean = acc["mean"]
        variance = acc["m2"] / n if n > 1 else 0.0
        sigma = variance ** 0.5 if variance > 0 else 1.5

        return (mean, sigma)

    def _pooled_sigma(self) -> float:
        """Compute pooled standard deviation across all regimes."""
        total_n = 0.0
        total_m2 = 0.0
        for acc in self._accumulators.values():
            total_n += acc["n"]
            total_m2 += acc["m2"]
        if total_n <= 1:
            return 0.0
        return (total_m2 / total_n) ** 0.5

    def get_baselines(self) -> dict[str, RegimeBaseline]:
        """Return all regime baselines."""
        baselines = {}
        for regime, acc in self._accumulators.items():
            n = int(acc["n"])
            mean = acc["mean"]
            variance = acc["m2"] / n if n > 1 else 0.0
            sigma = variance ** 0.5 if variance > 0 else 0.0
            baselines[regime] = RegimeBaseline(
                regime=regime,
                mean_pnl_r=mean,
                std_pnl_r=sigma,
                trade_count=n,
                last_updated=self._last_updated.get(regime, ""),
            )
        return baselines

    def get_state(self) -> dict[str, Any]:
        """Serialize for persistence."""
        return {
            "min_trades_per_regime": self.min_trades_per_regime,
            "default_null": self.default_null,
            "accumulators": dict(self._accumulators),
            "last_updated": dict(self._last_updated),
        }

    @classmethod
    def from_state(cls, state: dict[str, Any]) -> "RegimeAwareNull":
        """Restore from serialized state."""
        obj = cls(
            min_trades_per_regime=state["min_trades_per_regime"],
            default_null=state["default_null"],
        )
        obj._accumulators = {k: dict(v) for k, v in state["accumulators"].items()}
        obj._last_updated = dict(state["last_updated"])
        return obj


# ── Baseline comparators ─────────────────────────────────────────────────────


class MaxDDBaseline:
    """Stop when max drawdown in R-multiples exceeds threshold."""

    def __init__(self, threshold_r: float = 5.0):
        self.threshold_r = threshold_r
        self.peak: float = 0.0
        self.equity: float = 0.0

    def update(self, trade: TradeResult) -> str:
        self.equity += trade.pnl_r
        if self.equity > self.peak:
            self.peak = self.equity
        dd = self.peak - self.equity
        if dd >= self.threshold_r:
            return "RETIRE"
        return "CONTINUE"

    def reset(self) -> None:
        self.peak = 0.0
        self.equity = 0.0


class RollingSharpeBaseline:
    """Stop when N-trade rolling Sharpe stays below 0."""

    def __init__(self, window: int = 30, consecutive: int = 3):
        self.window = window
        self.consecutive = consecutive
        self._returns: deque[float] = deque(maxlen=window)
        self._below_count: int = 0

    def update(self, trade: TradeResult) -> str:
        self._returns.append(trade.pnl_r)
        if len(self._returns) < self.window:
            return "CONTINUE"

        mean = sum(self._returns) / len(self._returns)
        var = sum((x - mean) ** 2 for x in self._returns) / len(self._returns)
        std = var ** 0.5 if var > 0 else 0.0
        sharpe = mean / std if std > 0 else 0.0

        if sharpe < 0:
            self._below_count += 1
        else:
            self._below_count = 0

        if self._below_count >= self.consecutive:
            return "RETIRE"
        return "CONTINUE"

    def reset(self) -> None:
        self._returns.clear()
        self._below_count = 0


class CUSUMBaseline:
    """CUSUM drift detection on binary win/loss outcomes."""

    def __init__(self, threshold: float = 4.0, target_wr: float = 0.5):
        self.threshold = threshold
        self.target_wr = target_wr
        self._cusum: float = 0.0

    def update(self, trade: TradeResult) -> str:
        outcome = 1.0 if trade.pnl_r > 0 else 0.0
        self._cusum = max(0.0, self._cusum + (self.target_wr - outcome))
        if self._cusum >= self.threshold:
            return "RETIRE"
        return "CONTINUE"

    def reset(self) -> None:
        self._cusum = 0.0


# ── Regime mapper ─────────────────────────────────────────────────────────────


def map_market_context_to_ssrt_regime(
    garch_regime: str,
    trend_direction: str,
) -> str:
    """Map TradeBot market context to SSRT 4-regime system.

    Combines GARCH volatility regime with H1 trend direction to produce
    the four SSRT-compatible regimes.

    Args:
        garch_regime: From GarchRegimeDetector — "low", "normal", "high", "extreme"
        trend_direction: From AnalysisAgent — "bullish", "bearish", "neutral"
    """
    if garch_regime in ("high", "extreme"):
        return "volatile"

    if trend_direction == "bullish":
        return "trending_up"
    if trend_direction == "bearish":
        return "trending_down"
    return "ranging"


# ── Per-(strategy, symbol) SSRT state ──────────────────────────────────────


@dataclass
class StrategySSRTState:
    """SSRT state for one strategy × symbol pair."""

    sprt: MixtureSPRT
    regime_null: RegimeAwareNull
    history: list[SSRTVerdict] = field(default_factory=list)
    baselines: dict[str, MaxDDBaseline | RollingSharpeBaseline | CUSUMBaseline] = field(
        default_factory=dict
    )
    last_regime: str = "ranging"


# ── SSRT Agent ───────────────────────────────────────────────────────────────


class SSRTAgent:
    """Sequential Strategy Retirement Testing agent.

    Integrates the TradeMemory SSRT (mSPRT + regime-aware null) into the
    TradeBot pipeline.  Each strategy × symbol gets its own MixtureSPRT
    instance.  Retirement verdicts are returned alongside the trade record
    for consumption by learning_agent and the risk pipeline.

    Usage::

        agent = SSRTAgent(db)
        verdict = agent.update_trade(trade, garch_regime="normal", trend_direction="bullish")
        if verdict.decision == "RETIRE":
            learning_agent.adjust_confidence(trade.strategy, retired=True)
    """

    def __init__(
        self,
        db: "Database | None" = None,
        alpha: float = 0.05,
        tau: float = 1.0,
        burn_in: int = 20,
        min_regime_trades: int = 10,
    ) -> None:
        self._db = db
        self._alpha = alpha
        self._tau = tau
        self._burn_in = burn_in
        self._min_regime_trades = min_regime_trades

        # Per-(strategy, symbol) SSRT state
        self._states: dict[str, StrategySSRTState] = {}

        # Registry of retired strategies (key → retirement timestamp)
        self._retired: dict[str, str] = {}

    # ── key derivation ─────────────────────────────────────────────────────

    @staticmethod
    def _key(strategy: str, symbol: str) -> str:
        return f"{strategy}::{symbol}"

    # ── public API ─────────────────────────────────────────────────────────

    def update_trade(
        self,
        trade: "Trade",
        garch_regime: str,
        trend_direction: str,
    ) -> SSRTVerdict:
        """Process a closed trade through SSRT and return verdict.

        Args:
            trade: Closed Trade record with pnl, lot_size, entry_price, stop_loss.
            garch_regime: From GarchRegimeDetector — "low", "normal", "high", "extreme".
            trend_direction: From AnalysisAgent — "bullish", "bearish", "neutral".

        Returns:
            SSRTVerdict with decision, always-valid p-value, and diagnostics.
        """
        _t0 = datetime.now(UTC)

        # Compute R-multiple from Trade
        pnl_r = self._compute_r_multiple(trade)

        # Map to SSRT regime
        regime = map_market_context_to_ssrt_regime(garch_regime, trend_direction)

        # Build TradeResult
        ts = (trade.close_time or datetime.now(UTC)).isoformat()
        trade_result = TradeResult(
            pnl=trade.pnl or 0.0,
            pnl_r=pnl_r,
            regime=regime,
            timestamp=ts,
            strategy=trade.strategy,
            symbol=trade.symbol,
        )

        key = self._key(trade.strategy, trade.symbol)
        state = self._states.get(key)

        if state is None:
            state = self._init_state(trade.strategy, trade.symbol)
            self._states[key] = state

        # Update regime null with this trade
        state.regime_null.update(trade_result)

        # Check for regime change — shift null if regime changed (Option B)
        if regime != state.last_regime:
            self._handle_regime_shift(state, regime)

        # Get current regime parameters
        null_mean, sigma = state.regime_null.get_null(regime)
        state.sprt.null_mean = null_mean
        state.sprt.sigma = sigma

        # Update MixtureSPRT
        verdict = state.sprt.update(pnl_r)
        verdict.regime = regime

        # Update baselines
        baseline_decisions = self._update_baselines(state, trade_result)

        # Build composite decision (mSPRT + baselines)
        final_decision = self._composite_decision(verdict, baseline_decisions, state)
        verdict = SSRTVerdict(
            decision=final_decision,
            p_value=verdict.p_value,
            lambda_n=verdict.lambda_n,
            trades_analyzed=verdict.trades_analyzed,
            regime=regime,
            null_mean=null_mean,
        )

        state.history.append(verdict)
        state.last_regime = regime

        # If RETIRE, record it
        if final_decision == "RETIRE":
            self._handle_retirement(trade.strategy, trade.symbol, verdict)

        # Persist state
        self._save_state(key, state)

        # Emit event
        self._emit(
            "info",
            f"SSRT {trade.strategy}×{trade.symbol}: {final_decision} "
            f"(n={verdict.trades_analyzed}, p={verdict.p_value:.4f}, "
            f"regime={regime}, null_mean={null_mean:.3f})",
            {
                "strategy": trade.strategy,
                "symbol": trade.symbol,
                "decision": final_decision,
                "p_value": verdict.p_value,
                "lambda_n": verdict.lambda_n,
                "trades_analyzed": verdict.trades_analyzed,
                "regime": regime,
                "null_mean": null_mean,
                "baseline_decisions": baseline_decisions,
            },
        )

        record_call("ssrt", (datetime.now(UTC) - _t0).total_seconds() * 1000, True)
        return verdict

    def get_retirement_report(
        self,
        strategy: str,
        symbol: str,
    ) -> RetirementReport | None:
        """Build a full retirement report for a strategy × symbol."""
        key = self._key(strategy, symbol)
        state = self._states.get(key)
        if state is None:
            return None

        latest = state.history[-1] if state.history else None
        verdict = latest or SSRTVerdict(
            decision="INCONCLUSIVE",
            p_value=1.0,
            lambda_n=1.0,
            trades_analyzed=0,
            regime="unknown",
            null_mean=0.0,
        )

        baseline_comparison = {}
        for name, baseline in state.baselines.items():
            if hasattr(baseline, "equity"):
                baseline_comparison[name] = {
                    "equity": round(baseline.equity, 3),
                    "peak": round(baseline.peak, 3),
                }
            elif hasattr(baseline, "_returns"):
                baseline_comparison[name] = {
                    "window": getattr(baseline, "window", 0),
                    "below_count": getattr(baseline, "_below_count", 0),
                }
            elif hasattr(baseline, "_cusum"):
                baseline_comparison[name] = {"cusum": round(baseline._cusum, 3)}

        return RetirementReport(
            strategy=strategy,
            symbol=symbol,
            verdict=verdict,
            regime_baselines=state.regime_null.get_baselines(),
            baseline_comparison=baseline_comparison,
            history=list(state.history),
        )

    def is_retired(self, strategy: str, symbol: str) -> bool:
        """Check if a strategy × symbol has been retired."""
        return self._key(strategy, symbol) in self._retired

    def reset_strategy(self, strategy: str, symbol: str) -> None:
        """Reset SSRT state for a strategy × symbol (e.g. after parameter change)."""
        key = self._key(strategy, symbol)
        if key in self._states:
            del self._states[key]
        if key in self._retired:
            del self._retired[key]
        self._emit("info", f"SSRT reset for {strategy}×{symbol}")

    # ── internal ──────────────────────────────────────────────────────────

    def _init_state(self, strategy: str, symbol: str) -> StrategySSRTState:
        """Create fresh SSRT state for a new strategy × symbol pair."""
        sprt = MixtureSPRT(
            alpha=self._alpha,
            tau=self._tau,
            sigma=1.5,
            null_mean=0.0,
            burn_in=self._burn_in,
        )
        regime_null = RegimeAwareNull(
            min_trades_per_regime=self._min_regime_trades,
            default_null=0.0,
        )
        baselines = {
            "maxdd": MaxDDBaseline(threshold_r=5.0),
            "rolling_sharpe": RollingSharpeBaseline(window=30, consecutive=3),
            "cusum": CUSUMBaseline(threshold=4.0, target_wr=0.5),
        }
        return StrategySSRTState(
            sprt=sprt,
            regime_null=regime_null,
            baselines=baselines,
        )

    def _compute_r_multiple(self, trade: "Trade") -> float:
        """Convert a Trade into its R-multiple."""
        if trade.pnl is None or trade.pnl == 0:
            return 0.0
        if trade.entry_price and trade.stop_loss and trade.stop_loss != 0:
            sl_distance = abs(trade.entry_price - trade.stop_loss)
            if sl_distance > 0:
                return trade.pnl / (sl_distance * (trade.lot_size or 1.0))
        return trade.pnl  # Fallback: raw PnL

    def _handle_regime_shift(
        self,
        state: StrategySSRTState,
        new_regime: str,
    ) -> None:
        """Handle regime change via Option B — shift_null preserves evidence."""
        null_mean, sigma = state.regime_null.get_null(new_regime)
        state.sprt.shift_null(null_mean, sigma)
        self._emit(
            "info",
            f"SSRT regime shift: {state.last_regime} → {new_regime} "
            f"(shift_null → null_mean={null_mean:.3f}, sigma={sigma:.3f})",
        )

    def _update_baselines(
        self,
        state: StrategySSRTState,
        trade_result: TradeResult,
    ) -> dict[str, str]:
        """Update all baseline comparators and return their decisions."""
        decisions = {}
        for name, baseline in state.baselines.items():
            decisions[name] = baseline.update(trade_result)
        return decisions

    def _composite_decision(
        self,
        verdict: SSRTVerdict,
        baseline_decisions: dict[str, str],
        state: StrategySSRTState,
    ) -> str:
        """Combine mSPRT verdict with baseline signals.

        Retirement requires mSPRT RETIRE OR at least 2-of-3 baselines RETIRE.
        This prevents premature retirement from noisy single baselines while
        still catching multi-signal decay.
        """
        if verdict.decision == "RETIRE":
            return "RETIRE"

        baseline_retires = sum(1 for d in baseline_decisions.values() if d == "RETIRE")
        if baseline_retires >= 2:
            return "RETIRE"
        return verdict.decision

    def _handle_retirement(
        self,
        strategy: str,
        symbol: str,
        verdict: SSRTVerdict,
    ) -> None:
        """Handle a RETIRE verdict — record and notify."""
        key = self._key(strategy, symbol)
        self._retired[key] = datetime.now(UTC).isoformat()
        self._emit(
            "warn",
            f"STRATEGY RETIRED: {strategy}×{symbol} "
            f"(p={verdict.p_value:.4f}, n={verdict.trades_analyzed}, "
            f"regime={verdict.regime})",
            {
                "strategy": strategy,
                "symbol": symbol,
                "p_value": verdict.p_value,
                "trades_anapsed": verdict.trades_analyzed,
                "regime": verdict.regime,
                "null_mean": verdict.null_mean,
            },
        )

    def _emit(self, level: str, msg: str, data: dict | None = None) -> None:
        if self._db:
            self._db.log_agent_event("ssrt", level, msg, data)

    def _save_state(self, key: str, state: StrategySSRTState) -> None:
        """Persist SSRT state to DB for crash recovery via agent event log."""
        if self._db is None:
            return
        try:
            state_dict = {
                "key": key,
                "sprt": state.sprt.get_state(),
                "regime_null": state.regime_null.get_state(),
                "history": [
                    {
                        "decision": v.decision,
                        "p_value": v.p_value,
                        "lambda_n": v.lambda_n,
                        "trades_analyzed": v.trades_analyzed,
                        "regime": v.regime,
                        "null_mean": v.null_mean,
                    }
                    for v in state.history[-100:]
                ],
                "last_regime": state.last_regime,
            }
            self._db.log_agent_event("ssrt_state", "info", key, state_dict)
        except Exception as exc:
            logger.debug("SSRT state persistence failed: %s", exc)
