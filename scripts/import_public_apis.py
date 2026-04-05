"""Import selected entries from public-apis/public-apis into research intake."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import urlopen

from backtesting.public_api_intake import (
  TARGET_CATEGORIES,
  api_row_to_candidate,
  extract_api_rows,
  merge_candidate_payload,
)


DEFAULT_README_URL = (
  "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md"
)


def _load_markdown(readme_path: str | None, readme_url: str) -> str:
  if readme_path:
    return Path(readme_path).read_text(encoding="utf-8")

  with urlopen(readme_url, timeout=30) as response:
    return response.read().decode("utf-8")


def _parse_categories(raw_value: str | None) -> set[str]:
  if not raw_value:
    return set(TARGET_CATEGORIES)

  return {
    part.strip().lower()
    for part in raw_value.split(",")
    if part.strip()
  }


def main() -> None:
  parser = argparse.ArgumentParser(
    description="Import selected public APIs into research candidate backlog.",
  )
  parser.add_argument(
    "--readme-path",
    help="Optional local README.md path (useful for offline runs).",
  )
  parser.add_argument(
    "--readme-url",
    default=DEFAULT_README_URL,
    help="Raw GitHub README URL for public-apis/public-apis.",
  )
  parser.add_argument(
    "--categories",
    default=",".join(sorted(TARGET_CATEGORIES)),
    help="Comma-separated category list (default: trading-relevant categories).",
  )
  parser.add_argument(
    "--max-candidates",
    type=int,
    default=20,
    help="Maximum number of candidates to append/update.",
  )
  parser.add_argument(
    "--candidates-path",
    default="research/candidate_backlog.json",
    help="Path to candidate_backlog JSON.",
  )

  args = parser.parse_args()
  markdown = _load_markdown(args.readme_path, args.readme_url)
  categories = _parse_categories(args.categories)
  extracted_rows = extract_api_rows(markdown, target_categories=categories)

  limited_rows = extracted_rows[: max(args.max_candidates, 0)]
  new_candidates = [api_row_to_candidate(row) for row in limited_rows]

  candidate_file = Path(args.candidates_path)
  if candidate_file.exists():
    existing_payload = json.loads(candidate_file.read_text(encoding="utf-8"))
  else:
    existing_payload = {"schema_version": "1.0", "candidates": []}

  merged_payload = merge_candidate_payload(existing_payload, new_candidates)
  candidate_file.parent.mkdir(parents=True, exist_ok=True)
  candidate_file.write_text(json.dumps(merged_payload, indent=2), encoding="utf-8")

  print(
    "Imported",
    len(new_candidates),
    "candidate(s) from public-apis across categories:",
    ", ".join(sorted(categories)),
  )


if __name__ == "__main__":
  main()
