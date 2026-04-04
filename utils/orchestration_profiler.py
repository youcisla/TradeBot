"""Lightweight orchestration profiler for multi-agent loop optimization.

Tracks moving averages for scan/rank/execute/total loop timings and produces
bounded worker-tuning recommendations for non-MT5 parallel scans.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class OrchestrationTargets:
    """Latency goals (milliseconds) used for tuning and alerts."""

    scan_ms: float
    rank_ms: float
    exec_ms: float
    total_ms: float


class OrchestrationProfiler:
    """Collects rolling latency metrics and recommends bounded worker changes."""

    def __init__(self, targets: OrchestrationTargets, window_size: int = 20) -> None:
        self.targets = targets
        self.window_size = max(5, window_size)
        self._scan_ms: deque[float] = deque(maxlen=self.window_size)
        self._rank_ms: deque[float] = deque(maxlen=self.window_size)
        self._exec_ms: deque[float] = deque(maxlen=self.window_size)
        self._total_ms: deque[float] = deque(maxlen=self.window_size)

    def record(self, *, scan_ms: float, rank_ms: float, exec_ms: float, total_ms: float) -> None:
        self._scan_ms.append(max(0.0, scan_ms))
        self._rank_ms.append(max(0.0, rank_ms))
        self._exec_ms.append(max(0.0, exec_ms))
        self._total_ms.append(max(0.0, total_ms))

    @staticmethod
    def _avg(values: deque[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    def snapshot(self) -> dict[str, float]:
        return {
            "avg_scan_ms": self._avg(self._scan_ms),
            "avg_rank_ms": self._avg(self._rank_ms),
            "avg_exec_ms": self._avg(self._exec_ms),
            "avg_total_ms": self._avg(self._total_ms),
        }

    def primary_bottleneck(self) -> str:
        """Return bottleneck phase by largest target-relative overage."""
        s = self.snapshot()
        ratios = {
            "scan": self._ratio(s["avg_scan_ms"], self.targets.scan_ms),
            "rank": self._ratio(s["avg_rank_ms"], self.targets.rank_ms),
            "execute": self._ratio(s["avg_exec_ms"], self.targets.exec_ms),
            "total": self._ratio(s["avg_total_ms"], self.targets.total_ms),
        }
        return max(ratios, key=ratios.get)

    @staticmethod
    def _ratio(value: float, target: float) -> float:
        if target <= 0:
            return 0.0
        return value / target

    def recommend_workers(
        self,
        *,
        current_workers: int,
        min_workers: int,
        max_workers: int,
        scanned_symbol_count: int,
    ) -> int:
        """Adjust workers by at most +/-1 based on rolling scan latency.

        Rules:
        - Scale up when scan latency persistently exceeds target and there is
          enough symbol parallelism left.
        - Scale down when scan latency is far below target to reduce overhead.
        """
        min_w = max(1, min_workers)
        max_w = max(min_w, max_workers)
        workers = max(min_w, min(current_workers, max_w))

        avg_scan = self.snapshot()["avg_scan_ms"]
        if avg_scan <= 0:
            return workers

        high_threshold = self.targets.scan_ms * 1.15
        low_threshold = self.targets.scan_ms * 0.60

        if (
            avg_scan > high_threshold
            and workers < max_w
            and scanned_symbol_count > workers
        ):
            return workers + 1

        if avg_scan < low_threshold and workers > min_w:
            return workers - 1

        return workers
