"""
utils/mesh_bus.py
-----------------
Global nervous system for PulseTrade TradingBot.

Every component (agents, strategies, filters, broker, backtesting, state)
feeds real call telemetry into a shared AgentMeshState so trust, latency, and
inter-component coherence evolve based on actual runtime behaviour.

Public API
~~~~~~~~~~
- ``get_mesh()``            → live AgentMeshState singleton
- ``record_call(…)``        → EMA-update trust + latency for one node
- ``record_coherence(…)``   → EMA-update pairwise edge coherence
- ``mesh_span(node)``       → context-manager that records a call automatically

All EMA alphas are tunable per-call.  Defaults produce a ~8-call half-life for
trust and a ~5-call half-life for latency.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Generator

# Inlined from models.agent_mesh (deleted in Phase 2C)
from dataclasses import dataclass, field


@dataclass
class AgentNode:
    trust: float = 0.5
    latency_ms: float = 250.0
    name: str = ""
    role: str = "component"
    call_count: int = 0
    error_count: int = 0
    last_seen: float = 0.0


@dataclass
class AgentEdge:
    coherence: float = 1.0
    interaction_count: int = 0


@dataclass
class AgentMeshState:
    nodes: dict[str, AgentNode] = field(default_factory=dict)
    edges: dict[tuple[str, str], AgentEdge] = field(default_factory=dict)

# ---------------------------------------------------------------------------
# Known component registry (role hints for dashboard / inspection)
# ---------------------------------------------------------------------------

_KNOWN_COMPONENTS: dict[str, str] = {
    # agents
    "crucix": "agent",
    "market": "agent",
    "analysis": "agent",
    "strategy": "agent",
    "neural": "agent",
    "council": "agent",
    "risk": "agent",
    "execution": "agent",
    "trade_manager": "agent",
    "learning": "agent",
    "logging": "agent",
    # council experts
    "ict_expert": "expert",
    "danial_expert": "expert",
    "traditional_expert": "expert",
    "world_expert": "expert",
    # strategies (auto-registered on first use; pre-seeded here for dashboard)
    "ict_strategy": "strategy",
    # swarm profiles (registered by DeepSeek strategy)
    "trend_follower": "swarm",
    "structure_analyst": "swarm",
    "risk_specialist": "swarm",
    # filters
    "crucix_client": "filter",
    "data_validator": "filter",
    # broker
    "mt5_connector": "broker",
    "mock_connector": "broker",
    # backtesting
    "backtest_engine": "backtest",
    "data_downloader": "backtest",
    "mock_broker": "backtest",
    # state / persistence
    "persistence": "state",
    "database": "state",
}

# ---------------------------------------------------------------------------
# Singleton global mesh
# ---------------------------------------------------------------------------

_GLOBAL_MESH: AgentMeshState = AgentMeshState()


def _seed_mesh() -> None:
    """Pre-populate nodes for every known component so the dashboard always has a baseline."""
    for name, role in _KNOWN_COMPONENTS.items():
        if name not in _GLOBAL_MESH.nodes:
            _GLOBAL_MESH.nodes[name] = AgentNode(name=name, role=role)


_seed_mesh()


def get_mesh() -> AgentMeshState:
    """Return the live global AgentMeshState singleton."""
    return _GLOBAL_MESH


# ---------------------------------------------------------------------------
# Core recording helpers
# ---------------------------------------------------------------------------


def record_call(
    node: str,
    latency_ms: float,
    success: bool,
    *,
    trust_alpha: float = 0.12,
    latency_alpha: float = 0.20,
    _mesh: AgentMeshState | None = None,
) -> None:
    """EMA-update trust and latency for *node*, then bump counters.

    trust_alpha  ≈ 0.12 → ~8-call half-life
    latency_alpha ≈ 0.20 → ~5-call half-life

    Auto-registers unknown nodes as role="component".
    """
    mesh = _mesh if _mesh is not None else _GLOBAL_MESH
    if node not in mesh.nodes:
        mesh.nodes[node] = AgentNode(name=node, role="component")

    n = mesh.nodes[node]
    delta = 1.0 if success else 0.0
    n.trust = (1.0 - trust_alpha) * n.trust + trust_alpha * delta
    n.latency_ms = (1.0 - latency_alpha) * n.latency_ms + latency_alpha * latency_ms
    n.call_count += 1
    if not success:
        n.error_count += 1
    n.last_seen = time.monotonic()


def record_coherence(
    node_a: str,
    node_b: str,
    agreed: bool,
    *,
    alpha: float = 0.15,
    _mesh: AgentMeshState | None = None,
) -> None:
    """EMA-update pairwise coherence between *node_a* and *node_b*.

    Canonical key is (min, max) so order of arguments doesn't matter.
    alpha ≈ 0.15 → ~6-interaction half-life.
    """
    mesh = _mesh if _mesh is not None else _GLOBAL_MESH
    key: tuple[str, str] = (min(node_a, node_b), max(node_a, node_b))
    if key not in mesh.edges:
        mesh.edges[key] = AgentEdge()

    e = mesh.edges[key]
    delta = 1.0 if agreed else 0.0
    e.coherence = (1.0 - alpha) * e.coherence + alpha * delta
    e.interaction_count += 1


# ---------------------------------------------------------------------------
# Context-manager helper (Pattern A — inner-delegation components)
# ---------------------------------------------------------------------------


@contextmanager
def mesh_span(node: str, *, _mesh: AgentMeshState | None = None) -> Generator[None, None, None]:
    """Time the wrapped block and call ``record_call`` automatically.

    On success  → records True; on exception → records False and re-raises.

    Usage::

        with mesh_span("analysis"):
            ctx = self._analyze_inner(data)
    """
    _t0 = time.monotonic()
    try:
        yield
        record_call(node, (time.monotonic() - _t0) * 1_000.0, True, _mesh=_mesh)
    except Exception:
        record_call(node, (time.monotonic() - _t0) * 1_000.0, False, _mesh=_mesh)
        raise
