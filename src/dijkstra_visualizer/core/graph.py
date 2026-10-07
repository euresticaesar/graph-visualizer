import math
from collections.abc import Iterator

import networkx as nx

EdgeId = tuple[str, str, int]


def normalize_id(value: str | int) -> str:
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("El ID debe ser texto o un entero antiguo.")
    value = str(value).strip()
    if not value:
        raise ValueError("El ID no puede estar vacío.")
    return value


def validate_graph(graph: nx.Graph) -> None:
    if not graph:
        raise ValueError("El grafo debe contener al menos un nodo.")
    for node in graph:
        if not isinstance(node, str) or normalize_id(node) != node:
            raise ValueError("Los ID deben ser strings sin espacios exteriores.")
    for source, target, key, data in edges_with_keys(graph):
        if type(key) is not int or key < 0:
            raise ValueError("El ID de cada conexión debe ser un entero desde 0.")
        if source == target:
            raise ValueError("No se permiten conexiones de un nodo consigo mismo.")
        weight = data.get("weight")
        if (
            isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(weight)
        ):
            raise ValueError("Cada peso debe ser un número finito.")
        if not graph.is_directed() and weight < 0:
            raise ValueError("Un grafo no dirigido no admite pesos negativos.")


def edge_id(source: str, target: str, key: int, directed: bool = False) -> EdgeId:
    return (source, target, key) if directed else (min(source, target), max(source, target), key)


def edges_with_keys(graph: nx.Graph) -> Iterator[tuple[str, str, int, dict]]:
    if graph.is_multigraph():
        yield from graph.edges(keys=True, data=True)
    else:
        for source, target, data in graph.edges(data=True):
            yield source, target, 0, data


def ordered_arcs(graph: nx.Graph):
    arcs = []
    for u, v, key, data in edges_with_keys(graph):
        arcs.append((u, v, key, data["weight"]))
        if not graph.is_directed():
            arcs.append((v, u, key, data["weight"]))
    return tuple(sorted(arcs))


def convert_graph(graph: nx.Graph, directed: bool) -> nx.Graph:
    """Undirected→directed duplicates each edge; reverse conversion never merges edges."""
    result = nx.MultiDiGraph() if directed else nx.MultiGraph()
    result.add_nodes_from(graph)
    for u, v, key, data in edges_with_keys(graph):
        chosen = key
        while result.has_edge(u, v, chosen):
            chosen += 1
        result.add_edge(u, v, key=chosen, **data)
        if directed and not graph.is_directed():
            result.add_edge(v, u, key=chosen, **data)
    validate_graph(result)
    return result


def graphs_equal(left, right):
    return left.is_directed() == right.is_directed() and nx.utils.graphs_equal(left, right)
