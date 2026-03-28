"""Agent episodic memory — BM25-based situation/lesson store.

Each agent that benefits from past experience gets its own ``AgentMemory``
instance.  When a trade closes the Reflector generates a lesson and stores it
here.  On the *next* decision for the same symbol/context the most similar
past lesson is retrieved and injected into the agent's reasoning.

Design decisions vs. the upstream TradingAgents implementation
--------------------------------------------------------------
* JSON persistence — memories survive bot restarts.
* ``MAX_MEMORIES`` cap — oldest entries are evicted to keep the index small.
* ``min_score`` threshold on retrieval — low-relevance matches are silenced.
* No dependency on LangChain or any embedding API — pure BM25, offline.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    from rank_bm25 import BM25Okapi
    _BM25_AVAILABLE = True
except ImportError:  # pragma: no cover
    _BM25_AVAILABLE = False
    logger.warning("rank_bm25 not installed — AgentMemory will be a no-op. pip install rank_bm25")

MAX_MEMORIES = 500   # per agent; oldest evicted when exceeded
MIN_SCORE    = 0.05  # normalised BM25 score below which matches are suppressed


class AgentMemory:
    """BM25 episodic memory for a single agent role.

    Stores (situation_summary, lesson) pairs.  On retrieval the top-N most
    similar past situations are returned with their lessons.
    """

    def __init__(self, name: str, persist_path: Path | None = None) -> None:
        self.name           = name
        self._persist_path  = persist_path
        self._situations:  list[str] = []
        self._lessons:     list[str] = []
        self._bm25: "BM25Okapi | None" = None

        if persist_path and persist_path.exists():
            self._load()

    # ── public API ───────────────────────────────────────────────────────

    def add(self, situation: str, lesson: str) -> None:
        """Store a new (situation, lesson) pair and rebuild the index."""
        self._situations.append(situation)
        self._lessons.append(lesson)

        # Evict oldest entries when cap is exceeded
        if len(self._situations) > MAX_MEMORIES:
            excess = len(self._situations) - MAX_MEMORIES
            self._situations = self._situations[excess:]
            self._lessons    = self._lessons[excess:]

        self._rebuild()

        if self._persist_path:
            self._save()

    def recall(self, situation: str, n: int = 2) -> list[dict]:
        """Return up to *n* most relevant past lessons for the given situation.

        Each result dict has keys: ``situation``, ``lesson``, ``score``.
        Returns [] if memory is empty or BM25 is unavailable.
        """
        if not _BM25_AVAILABLE or self._bm25 is None or not self._situations:
            return []

        tokens  = self._tokenize(situation)
        scores  = self._bm25.get_scores(tokens)
        max_s   = max(scores) if len(scores) > 0 else 0.0
        if max_s <= 0:
            return []

        top_idx = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:n]
        results = []
        for idx in top_idx:
            norm = scores[idx] / max_s
            if norm < MIN_SCORE:
                continue
            results.append({
                "situation": self._situations[idx],
                "lesson":    self._lessons[idx],
                "score":     round(float(norm), 3),
            })
        return results

    def size(self) -> int:
        return len(self._situations)

    def clear(self) -> None:
        self._situations.clear()
        self._lessons.clear()
        self._bm25 = None
        if self._persist_path and self._persist_path.exists():
            self._persist_path.unlink()

    # ── internals ────────────────────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"\b\w+\b", text.lower())

    def _rebuild(self) -> None:
        if not _BM25_AVAILABLE or not self._situations:
            return
        tokenized = [self._tokenize(s) for s in self._situations]
        self._bm25 = BM25Okapi(tokenized)

    def _save(self) -> None:
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)  # type: ignore[union-attr]
            data = {"situations": self._situations, "lessons": self._lessons}
            self._persist_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")  # type: ignore[union-attr]
        except Exception:
            logger.warning("AgentMemory[%s]: failed to save to %s", self.name, self._persist_path)

    def _load(self) -> None:
        try:
            data = json.loads(self._persist_path.read_text(encoding="utf-8"))  # type: ignore[union-attr]
            self._situations = data.get("situations", [])
            self._lessons    = data.get("lessons", [])
            self._rebuild()
            logger.info("AgentMemory[%s]: loaded %d memories from disk", self.name, len(self._situations))
        except Exception:
            logger.warning("AgentMemory[%s]: failed to load from %s", self.name, self._persist_path)
