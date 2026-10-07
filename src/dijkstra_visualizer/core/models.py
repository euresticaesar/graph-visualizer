"""Immutable algorithm records, independent of Qt, files and exporters."""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType

from dijkstra_visualizer.core.graph import EdgeId


def format_number(value: float) -> str:
    if math.isinf(value):
        return "−∞" if value < 0 else "∞"
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


@dataclass(frozen=True)
class Comparison:
    source: str
    target: str
    weight: float
    before: float
    left: float
    right: float
    candidate: float
    improved: bool
    after: float
    predecessor_before: str | None = None
    predecessor_after: str | None = None

    def explain(self):
        f = format_number
        return (
            f"{self.source} → {self.target}: anterior {f(self.before)}; "
            f"{f(self.left)} + {f(self.right)} = {f(self.candidate)}. "
            f"¿Mejora estricta? {'Sí' if self.improved else 'No'}. "
            f"Resultante: {f(self.after)}. "
            f"Predecesor: {self.predecessor_before or '—'} → "
            f"{self.predecessor_after or '—'}."
        )


@dataclass(frozen=True)
class RouteTree:
    """Persistent composition of exact connections, never a live matrix reference."""

    edge: EdgeId | None = None
    left: "RouteTree | None" = None
    right: "RouteTree | None" = None


def tree_edges(tree: RouteTree | None, limit: int) -> list[EdgeId]:
    result = []
    stack = [tree] if tree else []
    budget = max(8, limit * 4)
    while stack:
        budget -= 1
        if budget < 0:
            return []
        part = stack.pop()
        if part.edge is not None:
            result.append(part.edge)
        else:
            if part.right:
                stack.append(part.right)
            if part.left:
                stack.append(part.left)
    return result


@dataclass(frozen=True)
class AlgorithmState:
    step: int
    current_node: str | None = None
    distances: Mapping[str, float] = field(default_factory=dict)
    predecessors: Mapping[str, str | None] = field(default_factory=dict)
    visited: frozenset[str] = frozenset()
    updated_nodes: frozenset[str] = frozenset()
    predecessor_edges: Mapping[str, int | None] = field(default_factory=dict)
    algorithm: str = "Dijkstra"
    phase: str = "Inicialización"
    iteration: int = 0
    current_edge: EdgeId | None = None
    comparison: Comparison | None = None
    explanation: str = ""
    summary: bool = False
    directed: bool = False
    affected: frozenset = frozenset()
    cycle: tuple[EdgeId, ...] = ()
    nodes: tuple[str, ...] = ()
    matrix: tuple = ()
    intermediates: tuple = ()
    routes: tuple = ()
    changed: frozenset[tuple[int, int]] = frozenset()
    cell: tuple[int, int] | None = None
    k: int | None = None

    def __post_init__(self):
        for name in ("distances", "predecessors", "predecessor_edges"):
            value = getattr(self, name)
            if not isinstance(value, MappingProxyType):
                object.__setattr__(self, name, MappingProxyType(dict(value)))
        for name in ("visited", "updated_nodes", "affected", "changed"):
            object.__setattr__(self, name, frozenset(getattr(self, name)))


DijkstraState = AlgorithmState


class StateView(Sequence):
    """Two navigations over one execution; absolute event IDs keep equivalent positions."""

    def __init__(self, states, detailed=True):
        self.events = tuple(states)
        self.indices = tuple(i for i, s in enumerate(states) if detailed or s.summary)

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, index):
        if isinstance(index, slice):
            return tuple(self.events[i] for i in self.indices[index])
        return self.events[self.indices[index]]

    def equivalent(self, event_step):
        return next((i for i, s in enumerate(self) if s.step >= event_step), len(self) - 1)
