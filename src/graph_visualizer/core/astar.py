"""A* with a consistent lower bound independent of the drawing coordinates."""

import math

import networkx as nx

from graph_visualizer.core.dijkstra import dijkstra_steps
from graph_visualizer.core.graph import algorithm_weight_error, ordered_arcs, validate_graph


def astar_steps(graph, start, target, *, detailed=False, _cancelled=None):
    validate_graph(graph)
    if start not in graph or target not in graph:
        raise ValueError("Selecciona origen y destino existentes.")
    if error := algorithm_weight_error(graph, "A*"):
        raise ValueError(error)
    arcs = ordered_arcs(graph)
    minimum = min((w for _, _, _, w in arcs), default=0.0)
    reverse = graph.reverse(copy=False) if graph.is_directed() else graph
    hops = nx.single_source_shortest_path_length(reverse, target)
    # A finite common bound for unreachable nodes preserves consistency on every arc.
    unreachable_hops = max(hops.values()) + 1
    heuristics = {node: minimum * hops.get(node, unreachable_hops) for node in graph}
    if not all(math.isfinite(value) for value in heuristics.values()):
        raise ValueError("La heurística excede el rango numérico permitido.")
    return dijkstra_steps(
        graph, start, target, detailed=detailed, _heuristics=heuristics, _cancelled=_cancelled
    )
