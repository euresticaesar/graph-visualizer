import math

import networkx as nx


def validate_graph(graph: nx.Graph) -> None:
    if graph.is_directed() or graph.is_multigraph():
        raise ValueError("The graph must be simple and undirected.")
    if not graph:
        raise ValueError("The graph must contain at least one node.")
    for node in graph:
        if type(node) is not int or node <= 0:
            raise ValueError(f"Node IDs must be positive integers: {node!r}.")
    for source, target, data in graph.edges(data=True):
        if source == target:
            raise ValueError(f"Self-loops are not supported: node {source}.")
        weight = data.get("weight")
        if (
            isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(weight)
            or weight <= 0
        ):
            raise ValueError(f"Edge {source}–{target} must have a finite positive weight.")
