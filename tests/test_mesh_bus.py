"""Unit-tests for utils/mesh_bus.py — isolated from the global singleton."""
from __future__ import annotations

import pytest

from utils.mesh_bus import AgentMeshState
from utils.mesh_bus import get_mesh, record_call, record_coherence, mesh_span


# ---------------------------------------------------------------------------
# Helpers — always work on fresh AgentMeshState instances, NOT the singleton,
# to avoid cross-test contamination.
# ---------------------------------------------------------------------------

def _fresh() -> AgentMeshState:
    return AgentMeshState()


# ---------------------------------------------------------------------------
# Singleton identity
# ---------------------------------------------------------------------------

class TestGetMesh:
    def test_singleton_identity(self):
        """get_mesh() must return the same object on every call."""
        assert get_mesh() is get_mesh()


# ---------------------------------------------------------------------------
# record_call — trust and latency EMA updates
# ---------------------------------------------------------------------------

class TestRecordCall:
    def test_first_call_success_increases_trust(self):
        mesh = _fresh()
        record_call("alpha", 100.0, True, _mesh=mesh, trust_alpha=0.12)
        node = mesh.nodes["alpha"]
        assert node.trust > 0.5
        assert node.call_count == 1
        assert node.error_count == 0

    def test_first_call_failure_decreases_trust(self):
        mesh = _fresh()
        record_call("alpha", 200.0, False, _mesh=mesh, trust_alpha=0.12)
        node = mesh.nodes["alpha"]
        assert node.trust < 0.5
        assert node.call_count == 1
        assert node.error_count == 1

    def test_latency_ema_updates(self):
        mesh = _fresh()
        initial = mesh.nodes.get("alpha") or None
        record_call("alpha", 50.0, True, _mesh=mesh, latency_alpha=0.20)
        node = mesh.nodes["alpha"]
        # EMA should move toward 50 from default 250
        assert node.latency_ms < 250.0

    def test_auto_registers_unknown_node(self):
        mesh = _fresh()
        assert "new_node" not in mesh.nodes
        record_call("new_node", 10.0, True, _mesh=mesh)
        assert "new_node" in mesh.nodes

    def test_multiple_failures_accumulate_error_count(self):
        mesh = _fresh()
        for _ in range(5):
            record_call("beta", 100.0, False, _mesh=mesh)
        node = mesh.nodes["beta"]
        assert node.error_count == 5
        assert node.call_count == 5

    def test_last_seen_updated(self):
        import time as _time
        mesh = _fresh()
        before = _time.monotonic()
        record_call("gamma", 10.0, True, _mesh=mesh)
        after = _time.monotonic()
        node = mesh.nodes["gamma"]
        assert before <= node.last_seen <= after


# ---------------------------------------------------------------------------
# record_coherence — edge coherence EMA + interaction_count
# ---------------------------------------------------------------------------

class TestRecordCoherence:
    def test_agreement_raises_coherence(self):
        mesh = _fresh()
        record_coherence("a", "b", agreed=True, _mesh=mesh, alpha=0.15)
        edge = mesh.edges[("a", "b")]
        # Starting coherence 1.0 — agreement keeps or raises it slightly
        assert edge.coherence >= 1.0
        assert edge.interaction_count == 1

    def test_disagreement_lowers_coherence(self):
        mesh = _fresh()
        record_coherence("a", "b", agreed=False, _mesh=mesh, alpha=0.15)
        edge = mesh.edges[("a", "b")]
        assert edge.coherence < 1.0
        assert edge.interaction_count == 1

    def test_canonical_key_ordering(self):
        """Edge key must always be (min, max) regardless of call order."""
        mesh = _fresh()
        record_coherence("z_node", "a_node", agreed=True, _mesh=mesh)
        assert ("a_node", "z_node") in mesh.edges
        assert ("z_node", "a_node") not in mesh.edges

    def test_interaction_count_accumulates(self):
        mesh = _fresh()
        for _ in range(4):
            record_coherence("x", "y", agreed=True, _mesh=mesh)
        edge = mesh.edges[("x", "y")]
        assert edge.interaction_count == 4


# ---------------------------------------------------------------------------
# mesh_span context manager
# ---------------------------------------------------------------------------

class TestMeshSpan:
    def test_success_path_records_true(self):
        mesh = _fresh()
        with mesh_span("span_node", _mesh=mesh):
            pass  # no exception
        node = mesh.nodes["span_node"]
        assert node.call_count == 1
        assert node.error_count == 0
        assert node.trust > 0.5

    def test_exception_path_records_false_and_reraises(self):
        mesh = _fresh()
        with pytest.raises(ValueError, match="boom"):
            with mesh_span("span_err", _mesh=mesh):
                raise ValueError("boom")
        node = mesh.nodes["span_err"]
        assert node.call_count == 1
        assert node.error_count == 1
        assert node.trust < 0.5

    def test_latency_recorded_on_success(self):
        mesh = _fresh()
        with mesh_span("span_lat", _mesh=mesh):
            pass
        node = mesh.nodes["span_lat"]
        assert node.latency_ms >= 0.0

    def test_latency_recorded_on_failure(self):
        mesh = _fresh()
        with pytest.raises(RuntimeError):
            with mesh_span("span_lat_err", _mesh=mesh):
                raise RuntimeError("fail")
        node = mesh.nodes["span_lat_err"]
        assert node.latency_ms >= 0.0
