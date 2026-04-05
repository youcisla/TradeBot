"""Research intake scoring and promotion-gate workflow.

Converts curated research candidates into a standardized experiment artifact so
new ideas can follow the same governance path as model benchmarks.
"""

from __future__ import annotations

import json
from pathlib import Path

from backtesting.report import generate_experiment_artifact


def _clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
  return max(lower, min(upper, value))


def _to_score(candidate: dict, key: str, default_value: float) -> float:
  raw = candidate.get(key, default_value)
  if isinstance(raw, bool):
    return 1.0 if raw else 0.0
  try:
    return _clamp(float(raw))
  except (TypeError, ValueError):
    return _clamp(default_value)


def _as_non_negative_float(value: object, default_value: float = 0.0) -> float:
  try:
    return max(0.0, float(value))
  except (TypeError, ValueError):
    return max(0.0, default_value)


def _estimate_uncertainty(candidate: dict) -> float:
  """Estimate uncertainty in [0, 1] from optional candidate metadata."""
  base_uncertainty = _as_non_negative_float(candidate.get("uncertainty", 0.0), 0.0)
  confidence_interval_width = _as_non_negative_float(
    candidate.get("confidence_interval_width", 0.0),
    0.0,
  )
  evidence_count = _as_non_negative_float(candidate.get("evidence_count", 0.0), 0.0)

  # More uncertainty if confidence interval is wide.
  ci_component = _clamp(confidence_interval_width)

  # Small sample sizes imply higher uncertainty.
  sample_penalty = 0.0
  if evidence_count > 0:
    if evidence_count < 100:
      sample_penalty = 0.20
    elif evidence_count < 250:
      sample_penalty = 0.10
    elif evidence_count < 500:
      sample_penalty = 0.05

  return _clamp(max(base_uncertainty, ci_component) + sample_penalty)


def load_json(path: str | Path) -> dict:
  file_path = Path(path)
  with file_path.open("r", encoding="utf-8") as fh:
    return json.load(fh)


def _checklist_status(candidate: dict, checklist: dict) -> dict:
  statuses: list[dict] = []
  required_failed = False

  for item in checklist.get("items", []):
    field = item.get("field", "")
    minimum = float(item.get("minimum", 1))
    required = bool(item.get("required", False))

    raw_value = candidate.get(field)
    if isinstance(raw_value, bool):
      score = 1.0 if raw_value else 0.0
    else:
      try:
        score = float(raw_value)
      except (TypeError, ValueError):
        score = 0.0

    passed = score >= minimum
    if required and not passed:
      required_failed = True

    statuses.append({
      "id": item.get("id"),
      "field": field,
      "required": required,
      "minimum": minimum,
      "value": score,
      "passed": passed,
    })

  passed_count = sum(1 for row in statuses if row["passed"])
  return {
    "items": statuses,
    "passed": passed_count,
    "total": len(statuses),
    "required_failed": required_failed,
  }


def evaluate_research_candidates(
  candidates: list[dict],
  *,
  rubric: dict,
  checklist: dict,
  curated_sources: dict,
) -> dict[str, dict]:
  """Evaluate candidate ideas and return symbol_reports-compatible payload."""
  weights = rubric.get("weights", {})
  defaults = rubric.get("defaults", {})

  source_by_id = {
    source.get("id", ""): source
    for source in curated_sources.get("sources", [])
  }

  reports: dict[str, dict] = {}
  for candidate in candidates:
    parts: dict[str, float] = {}
    weighted_score = 0.0
    for key, weight in weights.items():
      metric = _to_score(candidate, key, defaults.get(key, 0.0))
      parts[key] = metric
      weighted_score += metric * float(weight)

    checklist_status = _checklist_status(candidate, checklist)
    threshold = float(rubric.get("promotion_threshold", 0.7))
    uncertainty = _estimate_uncertainty(candidate)
    uncertainty_penalty_factor = _as_non_negative_float(
      rubric.get("uncertainty_penalty_factor", 0.35),
      0.35,
    )
    posterior_score = weighted_score * (1.0 - _clamp(uncertainty_penalty_factor) * uncertainty)
    promoted = (posterior_score >= threshold) and (not checklist_status["required_failed"])

    source_id = candidate.get("source_id", "")
    source_meta = source_by_id.get(source_id, {})
    candidate_id = candidate.get("id", source_id or "candidate")

    reports[candidate_id] = {
      "models": [
        {
          "name": "research_source_score",
          "accuracy": round(posterior_score, 4),
          "avg_strategy_return": round(posterior_score, 6),
          "trades": checklist_status["passed"],
        }
      ],
      "candidate": {
        "id": candidate_id,
        "name": candidate.get("name", "Unnamed Candidate"),
        "url": candidate.get("url", ""),
        "source_id": source_id,
        "source_category": source_meta.get("category", "unknown"),
        "source_tier": source_meta.get("tier", "unclassified"),
        "notes": candidate.get("notes", ""),
      },
      "score_breakdown": {
        "weighted_score": round(weighted_score, 6),
        "posterior_score": round(posterior_score, 6),
        "uncertainty": round(uncertainty, 6),
        "uncertainty_penalty_factor": round(uncertainty_penalty_factor, 6),
        "threshold": threshold,
        "parts": {k: round(v, 6) for k, v in parts.items()},
      },
      "promotion": {
        "promoted": promoted,
        "checklist_passed": checklist_status["passed"],
        "checklist_total": checklist_status["total"],
        "required_failed": checklist_status["required_failed"],
        "items": checklist_status["items"],
      },
    }

  return reports


def run_research_intake_pipeline(
  *,
  candidates_path: str | Path,
  curated_sources_path: str | Path,
  scoring_rubric_path: str | Path,
  promotion_checklist_path: str | Path,
  output_path: str | Path,
) -> dict:
  """Execute full research intake workflow and export one experiment artifact."""
  candidate_payload = load_json(candidates_path)
  source_payload = load_json(curated_sources_path)
  rubric_payload = load_json(scoring_rubric_path)
  checklist_payload = load_json(promotion_checklist_path)

  candidate_rows = candidate_payload.get("candidates", [])
  symbol_reports = evaluate_research_candidates(
    candidate_rows,
    rubric=rubric_payload,
    checklist=checklist_payload,
    curated_sources=source_payload,
  )

  artifact = generate_experiment_artifact(
    experiment_name="research_intake_promotion",
    symbol_reports=symbol_reports,
    metadata={
      "candidate_count": len(candidate_rows),
      "rubric_version": rubric_payload.get("version", "unknown"),
      "checklist_version": checklist_payload.get("version", "unknown"),
      "promotion_threshold": rubric_payload.get("promotion_threshold", 0.7),
      "source_catalog": str(curated_sources_path),
      "candidate_backlog": str(candidates_path),
    },
  )

  out_file = Path(output_path)
  out_file.parent.mkdir(parents=True, exist_ok=True)
  with out_file.open("w", encoding="utf-8") as fh:
    json.dump(artifact, fh, indent=2)

  return artifact