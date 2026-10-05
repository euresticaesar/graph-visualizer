import csv
import math
from pathlib import Path

import networkx as nx

from dijkstra_visualizer.core.graph import validate_graph
from dijkstra_visualizer.io.files import atomic_write_files
from dijkstra_visualizer.io.layout_io import PositionMap, serialize_layout


def _rows(path: Path, columns: list[str]) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames != columns:
                raise ValueError(f"{path.name}: expected CSV header {','.join(columns)}.")
            rows = list(reader)
    except csv.Error as error:
        raise ValueError(f"{path.name}: invalid CSV: {error}") from error
    for line, row in enumerate(rows, 2):
        if None in row or any(value is None or not value.strip() for value in row.values()):
            raise ValueError(f"{path.name}, row {line}: missing or extra values.")
    return rows


def _node_id(value: str, location: str) -> int:
    try:
        node = int(value)
    except ValueError as error:
        raise ValueError(f"{location}: invalid node ID {value!r}.") from error
    if node <= 0:
        raise ValueError(f"{location}: node IDs must be positive integers.")
    return node


def load_graph(nodes_path: Path, edges_path: Path) -> nx.Graph:
    graph = nx.Graph()
    for line, row in enumerate(_rows(nodes_path, ["id"]), 2):
        node = _node_id(row["id"], f"{nodes_path.name}, row {line}")
        if node in graph:
            raise ValueError(f"{nodes_path.name}, row {line}: duplicate node {node}.")
        graph.add_node(node)

    for line, row in enumerate(_rows(edges_path, ["source", "target", "weight"]), 2):
        location = f"{edges_path.name}, row {line}"
        source = _node_id(row["source"], location)
        target = _node_id(row["target"], location)
        if source not in graph or target not in graph:
            raise ValueError(f"{location}: edge {source}–{target} references a missing node.")
        if graph.has_edge(source, target):
            raise ValueError(f"{location}: duplicate undirected edge {source}–{target}.")
        try:
            weight = float(row["weight"])
        except ValueError as error:
            raise ValueError(f"{location}: invalid weight {row['weight']!r}.") from error
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError(f"{location}: weights must be finite positive numbers.")
        graph.add_edge(source, target, weight=weight)

    validate_graph(graph)
    return graph


def save_graph_data(data_dir: Path, graph: nx.Graph, positions: PositionMap) -> None:
    validate_graph(graph)
    if set(positions) != set(graph):
        raise ValueError("Cada nodo debe tener una posición para guardar el grafo.")
    nodes = "id\n" + "".join(f"{node}\n" for node in sorted(graph))
    edges = "source,target,weight\n"
    for source, target in sorted({tuple(sorted(pair)) for pair in graph.edges}):
        edges += f"{source},{target},{graph[source][target]['weight']:.17g}\n"
    atomic_write_files(
        {
            data_dir / "nodes.csv": nodes,
            data_dir / "edges.csv": edges,
            data_dir / "layout.json": serialize_layout(positions),
        }
    )
