"""Purged walk-forward split generator to reduce leakage in time-series ML tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class WalkForwardSlice:
  train_indices: list[int]
  test_indices: list[int]


def generate_purged_walk_forward_slices(
  sample_count: int,
  *,
  train_size: int,
  test_size: int,
  step_size: int | None = None,
  purge_size: int = 0,
  embargo_size: int = 0,
) -> list[WalkForwardSlice]:
  """Generate walk-forward slices with purge+embargo around train/test boundary."""
  if sample_count <= 0 or train_size <= 0 or test_size <= 0:
    return []

  step = step_size if step_size is not None else test_size
  if step <= 0:
    step = test_size

  slices: list[WalkForwardSlice] = []
  test_start = train_size

  while test_start + test_size <= sample_count:
    train_start = max(0, test_start - train_size)
    raw_train_end = test_start - purge_size
    train_end = max(train_start, raw_train_end)

    train_indices = list(range(train_start, train_end))
    test_indices = list(range(test_start, test_start + test_size))

    if train_indices and test_indices:
      slices.append(WalkForwardSlice(train_indices=train_indices, test_indices=test_indices))

    test_start += step + embargo_size

  return slices
