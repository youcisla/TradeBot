"""Helpers for importing and normalizing entries from public-apis/public-apis."""

from __future__ import annotations

import re


TARGET_CATEGORIES = {
  "finance",
  "currency exchange",
  "cryptocurrency",
  "news",
  "weather",
}


RISK_ALIGNMENT_BY_CATEGORY = {
  "finance": 0.9,
  "currency exchange": 0.88,
  "cryptocurrency": 0.8,
  "news": 0.72,
  "weather": 0.65,
}


def _normalize_category(category: str) -> str:
  return category.strip().lower()


def _slugify(value: str) -> str:
  value = value.strip().lower()
  value = re.sub(r"[^a-z0-9]+", "-", value)
  return value.strip("-")


def _parse_markdown_link(cell_value: str) -> tuple[str, str]:
  match = re.search(r"\[([^\]]+)\]\(([^)]+)\)", cell_value)
  if match:
    return match.group(1).strip(), match.group(2).strip()
  text = cell_value.strip()
  return text, ""


def _is_header_or_separator_row(cells: list[str]) -> bool:
  first_cell = cells[0].strip().lower()
  if first_cell == "api":
    return True
  return all(cell.replace("-", "").replace(":", "").strip() == "" for cell in cells)


def extract_api_rows(
  markdown_text: str,
  target_categories: set[str] | None = None,
) -> list[dict]:
  """Extract API rows from public-apis markdown tables."""
  selected = {
    _normalize_category(category)
    for category in (target_categories or TARGET_CATEGORIES)
  }

  rows: list[dict] = []
  current_category = ""

  for line in markdown_text.splitlines():
    stripped = line.strip()
    if stripped.startswith("### "):
      current_category = _normalize_category(stripped[4:])
      continue

    if not current_category or current_category not in selected:
      continue

    if not stripped.startswith("|"):
      continue

    cells = [cell.strip() for cell in stripped.strip("|").split("|")]
    if len(cells) < 5 or _is_header_or_separator_row(cells):
      continue

    name, url = _parse_markdown_link(cells[0])
    if not name:
      continue

    rows.append({
      "name": name,
      "url": url,
      "category": current_category,
      "description": cells[1],
      "auth": cells[2],
      "https": cells[3],
      "cors": cells[4],
    })

  return rows


def api_row_to_candidate(api_row: dict, source_id: str = "public-apis") -> dict:
  """Convert one extracted API row into research intake candidate schema."""
  category = _normalize_category(str(api_row.get("category", "")))
  risk_alignment = RISK_ALIGNMENT_BY_CATEGORY.get(category, 0.7)
  uses_https = str(api_row.get("https", "")).strip().lower() == "yes"
  has_auth = str(api_row.get("auth", "")).strip().lower() not in {"", "no"}

  reproducibility = 0.55 + (0.1 if uses_https else 0.0)
  maintenance = 0.62 if has_auth else 0.55
  implementation_readiness = 0.74 if category in {"finance", "currency exchange"} else 0.68

  slug = _slugify(str(api_row.get("name", "api")))
  notes = (
    f"Imported from public-apis ({category or 'uncategorized'}). "
    f"{str(api_row.get('description', '')).strip()}"
  ).strip()

  return {
    "id": f"public-apis-{slug}",
    "name": str(api_row.get("name", "Unnamed API")).strip(),
    "url": str(api_row.get("url", "")).strip(),
    "source_id": source_id,
    "reproducibility": round(reproducibility, 2),
    "implementation_readiness": round(implementation_readiness, 2),
    "maintenance": round(maintenance, 2),
    "adoption": 0.7,
    "risk_alignment": round(risk_alignment, 2),
    "open_source_license": True,
    "active_maintenance": True,
    "implementation_path": True,
    "testability": True,
    "risk_fit": True,
    "uncertainty": 0.35,
    "confidence_interval_width": 0.3,
    "evidence_count": 120,
    "notes": notes,
  }


def merge_candidate_payload(existing_payload: dict, new_candidates: list[dict]) -> dict:
  """Merge candidates by ID while preserving existing order where possible."""
  existing_candidates = list(existing_payload.get("candidates", []))
  ordered_ids = [
    candidate.get("id", "")
    for candidate in existing_candidates
    if candidate.get("id")
  ]
  candidate_by_id = {
    candidate.get("id"): candidate
    for candidate in existing_candidates
    if candidate.get("id")
  }

  for candidate in new_candidates:
    candidate_id = candidate.get("id")
    if not candidate_id:
      continue
    if candidate_id not in candidate_by_id:
      ordered_ids.append(candidate_id)
    candidate_by_id[candidate_id] = candidate

  merged = [candidate_by_id[candidate_id] for candidate_id in ordered_ids]
  return {
    "schema_version": existing_payload.get("schema_version", "1.0"),
    "candidates": merged,
  }
