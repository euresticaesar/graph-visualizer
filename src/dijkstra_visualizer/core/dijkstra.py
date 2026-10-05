import heapq
import math

import networkx as nx

from dijkstra_visualizer.core.graph import validate_graph
from dijkstra_visualizer.core.models import DijkstraState


def dijkstra_steps(graph: nx.Graph, start: int, target: int) -> list[DijkstraState]:
    validate_graph(graph)
    if type(start) is not int or start not in graph:
        raise ValueError("Selecciona un nodo de inicio que exista en el grafo.")
    if type(target) is not int or target not in graph:
        raise ValueError("Selecciona un nodo de destino que exista en el grafo.")

    distances = dict.fromkeys(graph, math.inf)
    predecessors: dict[int, int | None] = dict.fromkeys(graph)
    distances[start] = 0.0
    visited: set[int] = set()
    states = [DijkstraState(0, None, distances, predecessors, frozenset(), frozenset())]
    queue = [(0.0, start)]

    while queue:
        distance, current = heapq.heappop(queue)
        if current in visited:
            continue
        visited.add(current)
        updated: set[int] = set()
        if current != target:
            for neighbor in sorted(graph[current]):
                if neighbor in visited:
                    continue
                candidate = distance + graph[current][neighbor]["weight"]
                if not math.isfinite(candidate):
                    raise ValueError("Las distancias exceden el rango numérico permitido.")
                if candidate < distances[neighbor]:
                    distances[neighbor] = candidate
                    predecessors[neighbor] = current
                    updated.add(neighbor)
                    heapq.heappush(queue, (candidate, neighbor))
        states.append(
            DijkstraState(
                len(states),
                current,
                distances,
                predecessors,
                frozenset(visited),
                frozenset(updated),
            )
        )
        if current == target:
            break
    return states


def reconstruct_path(state: DijkstraState, start: int, target: int) -> list[int]:
    if target not in state.visited:
        return []
    path: list[int] = []
    current: int | None = target
    seen: set[int] = set()
    while current is not None:
        if current in seen:
            raise ValueError("Los predecesores contienen un ciclo.")
        seen.add(current)
        path.append(current)
        if current == start:
            return path[::-1]
        current = state.predecessors.get(current)
    return []
