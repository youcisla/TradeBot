import json

from backtesting.research_intake import evaluate_research_candidates, run_research_intake_pipeline


def test_evaluate_research_candidates_marks_promotion_correctly():
  candidates = [
    {
      "id": "high_quality",
      "name": "High quality",
      "source_id": "s1",
      "url": "https://example.com/high",
      "reproducibility": 0.9,
      "implementation_readiness": 0.8,
      "maintenance": 0.9,
      "adoption": 0.7,
      "risk_alignment": 0.9,
      "open_source_license": True,
      "active_maintenance": True,
      "implementation_path": True,
      "testability": True,
      "risk_fit": True,
    },
    {
      "id": "fails_gate",
      "name": "Fails gate",
      "source_id": "s2",
      "url": "https://example.com/low",
      "reproducibility": 0.95,
      "implementation_readiness": 0.9,
      "maintenance": 0.8,
      "adoption": 0.8,
      "risk_alignment": 0.9,
      "open_source_license": True,
      "active_maintenance": False,
      "implementation_path": True,
      "testability": True,
      "risk_fit": True,
    },
  ]

  rubric = {
    "promotion_threshold": 0.7,
    "weights": {
      "reproducibility": 0.3,
      "implementation_readiness": 0.25,
      "maintenance": 0.2,
      "adoption": 0.1,
      "risk_alignment": 0.15,
    },
    "defaults": {},
  }
  checklist = {
    "items": [
      {"id": "license", "field": "open_source_license", "required": True, "minimum": 1},
      {"id": "maint", "field": "active_maintenance", "required": True, "minimum": 1},
    ]
  }
  curated_sources = {
    "sources": [
      {"id": "s1", "category": "workflow", "tier": "core"},
      {"id": "s2", "category": "workflow", "tier": "intake"},
    ]
  }

  reports = evaluate_research_candidates(
    candidates,
    rubric=rubric,
    checklist=checklist,
    curated_sources=curated_sources,
  )

  assert reports["high_quality"]["promotion"]["promoted"] is True
  assert reports["fails_gate"]["promotion"]["promoted"] is False
  assert reports["fails_gate"]["promotion"]["required_failed"] is True


def test_run_research_intake_pipeline_exports_experiment_artifact(tmp_path):
  candidates = {
    "candidates": [
      {
        "id": "candidate_a",
        "name": "Candidate A",
        "source_id": "src_a",
        "url": "https://example.com/a",
        "reproducibility": 0.8,
        "implementation_readiness": 0.7,
        "maintenance": 0.8,
        "adoption": 0.6,
        "risk_alignment": 0.9,
        "open_source_license": True,
        "active_maintenance": True,
        "implementation_path": True,
        "testability": True,
        "risk_fit": True,
      }
    ]
  }
  sources = {"sources": [{"id": "src_a", "category": "curation", "tier": "core"}]}
  rubric = {
    "version": "test",
    "promotion_threshold": 0.65,
    "weights": {
      "reproducibility": 0.2,
      "implementation_readiness": 0.2,
      "maintenance": 0.2,
      "adoption": 0.2,
      "risk_alignment": 0.2,
    },
    "defaults": {},
  }
  checklist = {
    "version": "test",
    "items": [
      {"id": "license", "field": "open_source_license", "required": True, "minimum": 1},
      {"id": "fit", "field": "risk_fit", "required": True, "minimum": 1},
    ],
  }

  candidates_path = tmp_path / "candidates.json"
  sources_path = tmp_path / "sources.json"
  rubric_path = tmp_path / "rubric.json"
  checklist_path = tmp_path / "checklist.json"
  output_path = tmp_path / "artifact.json"

  candidates_path.write_text(json.dumps(candidates), encoding="utf-8")
  sources_path.write_text(json.dumps(sources), encoding="utf-8")
  rubric_path.write_text(json.dumps(rubric), encoding="utf-8")
  checklist_path.write_text(json.dumps(checklist), encoding="utf-8")

  artifact = run_research_intake_pipeline(
    candidates_path=candidates_path,
    curated_sources_path=sources_path,
    scoring_rubric_path=rubric_path,
    promotion_checklist_path=checklist_path,
    output_path=output_path,
  )

  assert output_path.exists()
  assert artifact["experiment"]["name"] == "research_intake_promotion"
  assert "candidate_a" in artifact["symbols"]
  assert artifact["symbols"]["candidate_a"]["promotion"]["promoted"] is True