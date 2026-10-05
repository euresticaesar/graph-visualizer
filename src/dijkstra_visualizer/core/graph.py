import math

import networkx as nx


def validate_graph(graph: nx.Graph) -> None:
    if graph.is_directed() or graph.is_multigraph():
        raise ValueError("El grafo debe ser simple y no dirigido.")
    if not graph:
        raise ValueError("El grafo debe contener al menos un nodo.")
    for node in graph:
        if type(node) is not int or node <= 0:
            raise ValueError(f"Los ID de los nodos deben ser enteros positivos: {node!r}.")
    for source, target, data in graph.edges(data=True):
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
