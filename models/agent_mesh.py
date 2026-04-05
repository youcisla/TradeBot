from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class AgentNode:
    """Per-component adaptive state in the global mesh."""

    trust: float = 0.5
    latency_ms: float = 250.0
    name: str = ""
    role: str = "component"
    call_count: int = 0
    error_count: int = 0
    last_seen: float = 0.0


@dataclass
class AgentEdge:
    """Pairwise coherence weight between two mesh nodes."""

    coherence: float = 1.0
    interaction_count: int = 0


@dataclass
class AgentMeshState:
    """Global graph state: nodes are system components, edges are interaction weights."""

    nodes: dict[str, AgentNode] = field(default_factory=dict)
    edges: dict[tuple[str, str], AgentEdge] = field(default_factory=dict)
