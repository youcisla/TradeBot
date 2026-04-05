from backtesting.walk_forward import generate_purged_walk_forward_slices


def test_generate_purged_walk_forward_slices_no_overlap():
  slices = generate_purged_walk_forward_slices(
    500,
    train_size=200,
    test_size=60,
    purge_size=7,
    embargo_size=5,
  )
  assert len(slices) > 0

  for wf_slice in slices:
    train_set = set(wf_slice.train_indices)
    test_set = set(wf_slice.test_indices)
    assert train_set.isdisjoint(test_set)


def test_generate_purged_walk_forward_respects_bounds():
  slices = generate_purged_walk_forward_slices(
    120,
    train_size=50,
    test_size=20,
    purge_size=2,
    embargo_size=3,
  )
  assert len(slices) > 0
  for wf_slice in slices:
    assert min(wf_slice.train_indices) >= 0
    assert max(wf_slice.test_indices) < 120
