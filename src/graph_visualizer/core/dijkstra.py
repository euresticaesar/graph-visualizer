import heapq
import math

import networkx as nx

from graph_visualizer.core.graph import (
    EdgeId,
    algorithm_weight_error,
    edge_id,
    ordered_arcs,
    validate_graph,
)
from graph_visualizer.core.models import (
    AlgorithmCancelled,
    AlgorithmState,
    Comparison,
    StateView,
    tree_edges,
)


def dijkstra_steps(
    graph: nx.Graph, start: str, target: str, *, detailed=False, _heuristics=None, _cancelled=None
):
    validate_graph(graph)
    if start not in graph or target not in graph:
        raise ValueError("Selecciona origen y destino existentes.")
    algorithm = "A*" if _heuristics is not None else "Dijkstra"
    if error := algorithm_weight_error(graph, algorithm):
        raise ValueError(error)
    arcs = ordered_arcs(graph)
    heuristics = _heuristics or dict.fromkeys(graph, 0.0)
    distances = dict.fromkeys(sorted(graph), math.inf)
    predecessors = dict.fromkeys(graph)
    keys = dict.fromkeys(graph)
    distances[start] = 0.0
    visited = set()
    events = []

    def emit(current=None, **kw):
        if _cancelled and _cancelled():
            raise AlgorithmCancelled
        events.append(
            AlgorithmState(
                len(events),
                current,
                distances,
                predecessors,
                frozenset(visited),
                predecessor_edges=keys,
                directed=graph.is_directed(),
                algorithm=algorithm,
                heuristics=heuristics if algorithm == "A*" else {},
                **kw,
            )
        )

    emit(summary=True, explanation="Distancia inicial del origen: 0; las demás: ∞.")
    queue = [(heuristics[start], start)]
    iteration = 0
    while queue:
        _, current = heapq.heappop(queue)
        distance = distances[current]
        if current in visited:
            continue
        iteration += 1
        visited.add(current)
        emit(
            current,
            phase="Selección",
            iteration=iteration,
            explanation=(
                f"Se selecciona {current}: g={distance:g}, h={heuristics[current]:g}, "
                f"f=g+h={distance + heuristics[current]:g}."
                if algorithm == "A*"
                else f"Se selecciona {current}, de menor distancia tentativa."
            ),
        )
        updated = set()
        if current != target:
            for u, v, key, weight in arcs:
                if u != current or v in visited:
                    continue
                before, pred = distances[v], predecessors[v]
                candidate = distance + weight
                if not math.isfinite(candidate):
                    raise ValueError("Las distancias exceden el rango numérico permitido.")
                improved = candidate < before
                if improved:
                    distances[v], predecessors[v], keys[v] = candidate, u, key
                    updated.add(v)
                    priority = candidate + heuristics[v]
                    if not math.isfinite(priority):
                        raise ValueError("La prioridad excede el rango numérico permitido.")
                    heapq.heappush(queue, (priority, v))
                comparison = Comparison(
                    u,
                    v,
                    weight,
                    before,
                    distance,
                    weight,
                    candidate,
                    improved,
                    distances[v],
                    pred,
                    predecessors[v],
                )
                emit(
                    current,
                    phase="Comparación",
                    iteration=iteration,
                    current_edge=(u, v, key),
                    comparison=comparison,
                    updated_nodes=frozenset({v} if improved else ()),
                    explanation=f"Conexión #{key}. " + comparison.explain(),
                )
        emit(
            current,
            phase="Por nodo",
            iteration=iteration,
            summary=True,
            updated_nodes=frozenset(updated),
            explanation=f"Nodo {current} procesado; {len(updated)} etiquetas mejoradas.",
        )
        if current == target:
            break
    # The last node summary is also the result, avoiding a duplicated summary click.
    from dataclasses import replace

    events[-1] = replace(
        events[-1],
        phase="Resultado",
        explanation="Destino seleccionado."
        if target in visited
        else "No hay ruta al destino; no quedan nodos alcanzables.",
    )
    return StateView(events, detailed)


def reconstruct_path(state: AlgorithmState, start: str, target: str) -> list[str]:
    if state.algorithm == "Floyd-Warshall":
        if start not in state.nodes or target not in state.nodes:
            return []
        i, j = state.nodes.index(start), state.nodes.index(target)
        if not math.isfinite(state.matrix[i][j]):
            return []
        if start == target:
            return [start]
        edges = tree_edges(state.routes[i][j], len(state.nodes))
        path = [start]
        for u, v, _ in edges:
            if u != path[-1] or v in path:
                return []
            path.append(v)
        return path if path[-1] == target else []
    if target in state.affected or not math.isfinite(state.distances.get(target, math.inf)):
        return []
    if state.algorithm in {"Dijkstra", "A*"} and target not in state.visited:
        return []
    path, seen = [], set()
    current = target
    while current is not None:
        if current in seen:
            return []
        seen.add(current)
        path.append(current)
        if current == start:
            return path[::-1]
        current = state.predecessors.get(current)
    return []


def reconstruct_edge_path(state: AlgorithmState, start: str, target: str) -> list[EdgeId]:
    path = reconstruct_path(state, start, target)
    if not path:
        return []
    if state.algorithm == "Floyd-Warshall":
        edges = tree_edges(
            state.routes[state.nodes.index(start)][state.nodes.index(target)], len(state.nodes)
        )
        return [edge_id(u, v, k, state.directed) for u, v, k in edges]
    result = []
    for u, v in zip(path, path[1:], strict=False):
        key = state.predecessor_edges.get(v)
        if key is None:
            return []
        result.append(edge_id(u, v, key, state.directed))
    return result


def route_description(state, start, target):
    from graph_visualizer.core.models import format_number

    distance = (
        state.matrix[state.nodes.index(start)][state.nodes.index(target)]
        if state.algorithm == "Floyd-Warshall"
        else state.distances[target]
    )
    if distance == -math.inf:
        return "−∞: no existe costo mínimo finito; la ruta puede atravesar un ciclo negativo."
    path = reconstruct_path(state, start, target)
    if path:
        label = "Ruta mínima" if state.phase == "Resultado" else "Ruta del estado actual"
        return f"{label}: {' → '.join(path)} · Costo {format_number(distance)}"
    return "Sin ruta confirmada en este estado."
