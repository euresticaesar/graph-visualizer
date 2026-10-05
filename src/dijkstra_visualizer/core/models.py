from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class DijkstraState:
    step: int
    current_node: int | None
    distances: Mapping[int, float]
    predecessors: Mapping[int, int | None]
    visited: frozenset[int]
    updated_nodes: frozenset[int]

    def __post_init__(self) -> None:
        object.__setattr__(self, "distances", MappingProxyType(dict(self.distances)))
        object.__setattr__(self, "predecessors", MappingProxyType(dict(self.predecessors)))
        object.__setattr__(self, "visited", frozenset(self.visited))
        object.__setattr__(self, "updated_nodes", frozenset(self.updated_nodes))
