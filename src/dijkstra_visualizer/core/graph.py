import math
from collections.abc import Iterator

import networkx as nx


def validate_graph(graph: nx.Graph) -> None:
    if graph.is_directed():
        raise ValueError("El grafo debe ser no dirigido.")
    if not graph:
        raise ValueError("El grafo debe contener al menos un nodo.")
    for node in graph:
        if type(node) is not int or node < 0:
            raise ValueError(
                f"Los ID de los nodos deben ser enteros mayores o iguales a cero: {node!r}."
            )
    for source, target, key, data in edges_with_keys(graph):
        if type(key) is not int or key < 0:
            raise ValueError("El ID de cada conexión debe ser un entero desde 0.")
        if source == target:
            raise ValueError(f"No se permiten conexiones de un nodo consigo mismo: nodo {source}.")
        weight = data.get("weight")
        if (
            isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(weight)
            or weight <= 0
        ):
            raise ValueError(f"La conexión {source}–{target} debe tener un peso positivo y finito.")


EdgeId = tuple[int, int, int]


def edge_id(source: int, target: int, key: int) -> EdgeId:
    return min(source, target), max(source, target), key


def edges_with_keys(graph: nx.Graph) -> Iterator[tuple[int, int, int, dict]]:
    if graph.is_multigraph():
        yield from graph.edges(keys=True, data=True)
    else:
        for source, target, data in graph.edges(data=True):
            yield source, target, 0, data
