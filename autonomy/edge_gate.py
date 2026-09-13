"""Promotion gate — may this strategy trade real money?

An autonomous bot that can promote *itself* to live trading is a machine that
can remove its own brakes.  This module is the brake.  It reads a measured
out-of-sample result and answers one question: has this strategy earned the
right to risk capital?

**Fail-closed by construction.**  No measurement, a stale measurement, a
measurement taken on different code, or a holdout that does not itself show a
profitable edge all mean NO.  The failure mode of a gate like this must be
"refuse to trade", never "proceed without evidence" — the whole point is that
it is the last thing standing between a hypothesis and the account.

Demo trading is always permitted; the gate governs *live* capital only.
Thresholds are module constants and are deliberately not configurable from the
environment, so the adaptive layer cannot widen its own limits.
"""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Thresholds.  IMMUTABLE: not read from settings, not writable at runtime. ──

MIN_POSITIONS = 200        # below this the sample cannot support a conclusion
MIN_EXPECTANCY_R = 0.05    # average R per trade, net of costs, must be positive
MIN_PROFIT_FACTOR = 1.15   # gross wins must clear gross losses by a margin
MAX_DRAWDOWN_PCT = 0.20    # a 20% drawdown is already a serious event
MIN_SHARPE = 0.5           # annualised
MAX_AGE_DAYS = 14          # a stale measurement describes a different world

ARTIFACT_PATH = Path("state") / "measurement.json"


@dataclass
class Verdict:
    allowed: bool
    reason: str
    checks: list[tuple[str, bool, str]] = field(default_factory=list)

    def render(self) -> str:
        lines = [f"EDGE GATE: {'PASS' if self.allowed else 'BLOCKED'} — {self.reason}"]
        for name, ok, detail in self.checks:
            lines.append(f"  [{'x' if ok else ' '}] {name:<22} {detail}")
        return "\n".join(lines)


def _code_revision() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() if out.returncode == 0 else "unknown"
    except Exception:                                      # noqa: BLE001
        return "unknown"


def evaluate(artifact: dict, *, revision: str | None = None) -> Verdict:
    """Decide whether *artifact* justifies live trading."""
    checks: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str) -> bool:
        checks.append((name, ok, detail))
        return ok

    def num(block: dict, key: str, default: float = 0.0) -> float:
        try:
            return float(block.get(key, default) or 0.0)
        except (TypeError, ValueError):
            return default

    # ── Freshness ────────────────────────────────────────────────────────────
    try:
        generated = datetime.fromisoformat(str(artifact.get("generated_at", "")))
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=UTC)
        age = datetime.now(UTC) - generated
        check(
            "measurement_freshness",
            age <= timedelta(days=MAX_AGE_DAYS),
            f"{age.days}d old (limit {MAX_AGE_DAYS}d)",
        )
    except Exception:                                      # noqa: BLE001
        check("measurement_freshness", False, "unparseable or missing generated_at")

    # ── The measurement must describe the code that would trade ──────────────
    measured_rev = str(artifact.get("code_revision", "unknown"))
    current_rev = revision or _code_revision()
    check(
        "code_revision_match",
        measured_rev not in ("", "unknown") and measured_rev == current_rev,
        f"measured {measured_rev}, running {current_rev}",
    )

    # ── Costs must have been modelled ────────────────────────────────────────
    check(
        "costs_modelled",
        bool(artifact.get("costs_modelled")),
        "spread+commission charged on every fill",
    )

    # ── The holdout is the number that counts ────────────────────────────────
    holdout = artifact.get("holdout") or {}
    pooled = artifact.get("pooled") or {}

    n = int(num(holdout, "positions"))
    check("holdout_sample_size", n >= MIN_POSITIONS, f"n={n} (min {MIN_POSITIONS})")

    exp = num(holdout, "avg_r")
    check("holdout_expectancy", exp > MIN_EXPECTANCY_R,
          f"avgR={exp:+.3f} (need > {MIN_EXPECTANCY_R:+.3f})")

    pf = num(holdout, "profit_factor")
    check("holdout_profit_factor", pf > MIN_PROFIT_FACTOR,
          f"PF={pf:.2f} (need > {MIN_PROFIT_FACTOR:.2f})")

    dd = num(holdout, "max_drawdown_pct")
    check("holdout_drawdown", dd <= MAX_DRAWDOWN_PCT,
          f"maxDD={dd:.1%} (limit {MAX_DRAWDOWN_PCT:.0%})")

    sharpe = num(holdout, "annualised_sharpe")
    check("holdout_sharpe", sharpe > MIN_SHARPE,
          f"Sharpe={sharpe:.2f} (need > {MIN_SHARPE:.2f})")

    # ── Pooled must not contradict the holdout ──────────────────────────────
    check("pooled_agrees", num(pooled, "avg_r") > 0.0,
          f"pooled avgR={num(pooled, 'avg_r'):+.3f} (must be positive)")

    allowed = all(ok for _, ok, _ in checks)
    if allowed:
        reason = (
            f"holdout n={n}, avgR={exp:+.3f}, PF={pf:.2f}, "
            f"maxDD={dd:.1%}, Sharpe={sharpe:.2f}"
        )
    else:
        reason = "failed: " + ", ".join(name for name, ok, _ in checks if not ok)

    return Verdict(allowed=allowed, reason=reason, checks=checks)


def load_artifact(path: Path | str = ARTIFACT_PATH) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:                               # noqa: BLE001
        logger.error("Edge gate: measurement artifact unreadable (%s)", exc)
        return None


def evaluate_file(path: Path | str = ARTIFACT_PATH) -> Verdict:
    artifact = load_artifact(path)
    if artifact is None:
        return Verdict(
            allowed=False,
            reason=f"no measurement artifact at {path} — run scripts/measure.py",
            checks=[("artifact_present", False, str(path))],
        )
    return evaluate(artifact)


def live_trading_allowed() -> tuple[bool, str]:
    """Convenience for the bot's startup path.

    Returns ``(allowed, reason)``.  Demo mode does not consult the gate — the
    gate exists to protect capital, and there is none at risk on a demo.
    """
    from config import settings

    if getattr(settings, "DEMO_MODE", True):
        return True, "demo mode — edge gate not required"

    verdict = evaluate_file()
    logger.info("\n%s", verdict.render())
    return verdict.allowed, verdict.reason
