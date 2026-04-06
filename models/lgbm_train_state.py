"""Adaptive LGBM training threshold — persisted state.

Threshold starts at 20, then grows by 1.5× after each successful training
run, capped at 500.  State is written to models/lgbm_train_state.json so
it survives bot restarts.

Sequence:
  round 1  →  20 trades needed
  round 2  →  30
  round 3  →  45
  round 4  →  68
  round 5  →  102
  round 6  →  153
  round 7  →  229
  round 8  →  343
  round 9+ →  500 (cap)
"""

from __future__ import annotations

import json
import math
from pathlib import Path

_STATE_PATH = Path("models/lgbm_train_state.json")

INITIAL_THRESHOLD: int = 20
GROWTH_FACTOR: float   = 1.5
MAX_THRESHOLD: int     = 500


class LGBMTrainState:
    """Thin wrapper around the JSON state file."""

    def __init__(self, path: Path = _STATE_PATH) -> None:
        self._path = path
        self._data = self._load()

    # ── public ────────────────────────────────────────────────────────────

    @property
    def next_threshold(self) -> int:
        return int(self._data["next_threshold"])

    @property
    def train_count(self) -> int:
        return int(self._data["train_count"])

    def should_train(self, total_closed: int) -> bool:
        """True when enough new trades have accumulated."""
        return total_closed >= self.next_threshold

    def bump(self) -> int:
        """Advance to the next threshold after a successful training run.

        Returns the *new* threshold.
        """
        old = self._data["next_threshold"]
        new = min(int(math.floor(old * GROWTH_FACTOR)), MAX_THRESHOLD)
        self._data["next_threshold"] = new
        self._data["train_count"]   += 1
        self._save()
        return new

    def reset(self) -> None:
        """Reset to initial values (useful for testing or fresh starts)."""
        self._data = {"next_threshold": INITIAL_THRESHOLD, "train_count": 0}
        self._save()

    def as_dict(self) -> dict:
        return dict(self._data)

    # ── internal ─────────────────────────────────────────────────────────

    def _load(self) -> dict:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"next_threshold": INITIAL_THRESHOLD, "train_count": 0}

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")


# Module-level singleton
_state: LGBMTrainState | None = None


def get_state() -> LGBMTrainState:
    global _state
    if _state is None:
        _state = LGBMTrainState()
    return _state
