"""Tests for public API intake parser and merge helpers."""

from backtesting.public_api_intake import (
  api_row_to_candidate,
  extract_api_rows,
  merge_candidate_payload,
)


SAMPLE_MARKDOWN = """
### Finance

| API | Description | Auth | HTTPS | CORS |
| --- | --- | --- | --- | --- |
| [Financial Modeling Prep](https://site.financialmodelingprep.com/developer/docs/) | Real-time and historical market data | apiKey | Yes | Unknown |

### Animals

| API | Description | Auth | HTTPS | CORS |
| --- | --- | --- | --- | --- |
| [Cat Facts](https://example.com/cats) | Cat facts | No | Yes | Yes |

### News

| API | Description | Auth | HTTPS | CORS |
| --- | --- | --- | --- | --- |
| [MarketAux](https://www.marketaux.com/) | News and sentiment feed | apiKey | Yes | Unknown |
"""


def test_extract_api_rows_filters_target_categories():
  rows = extract_api_rows(SAMPLE_MARKDOWN, target_categories={"finance", "news"})

  assert len(rows) == 2
  assert rows[0]["name"] == "Financial Modeling Prep"
  assert rows[0]["category"] == "finance"
  assert rows[1]["name"] == "MarketAux"
  assert rows[1]["category"] == "news"


def test_api_row_to_candidate_shape():
  row = {
    "name": "ExchangeRate-API",
    "url": "https://www.exchangerate-api.com",
    "category": "currency exchange",
    "description": "Exchange rates",
    "auth": "No",
    "https": "Yes",
    "cors": "Unknown",
  }

  candidate = api_row_to_candidate(row)

  assert candidate["id"] == "public-apis-exchangerate-api"
  assert candidate["source_id"] == "public-apis"
  assert candidate["open_source_license"] is True
  assert candidate["risk_alignment"] == 0.88
  assert candidate["reproducibility"] >= 0.6


def test_merge_candidate_payload_updates_and_appends():
  existing = {
    "schema_version": "1.0",
    "candidates": [
      {
        "id": "public-apis-marketaux",
        "name": "Old Name",
      },
      {
        "id": "existing-candidate",
        "name": "Keep Me",
      },
    ],
  }

  new_candidates = [
    {
      "id": "public-apis-marketaux",
      "name": "MarketAux",
    },
    {
      "id": "public-apis-fmp",
      "name": "Financial Modeling Prep",
    },
  ]

  merged = merge_candidate_payload(existing, new_candidates)
  by_id = {row["id"]: row for row in merged["candidates"]}

  assert merged["schema_version"] == "1.0"
  assert by_id["public-apis-marketaux"]["name"] == "MarketAux"
  assert by_id["existing-candidate"]["name"] == "Keep Me"
  assert by_id["public-apis-fmp"]["name"] == "Financial Modeling Prep"
