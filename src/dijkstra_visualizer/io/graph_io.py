import csv
import math
from pathlib import Path

import networkx as nx

from dijkstra_visualizer.core.graph import edges_with_keys, validate_graph
from dijkstra_visualizer.io.files import atomic_write_files
from dijkstra_visualizer.io.layout_io import PositionMap, serialize_layout


def _rows(path: Path, columns: list[str], optional_id: bool = False) -> list[dict[str, str]]:
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            if reader.fieldnames != columns and not (
                optional_id and reader.fieldnames == [*columns, "id"]
            ):
                raise ValueError(f"{path.name}: se esperaba el encabezado CSV {','.join(columns)}.")
            rows = list(reader)
    except csv.Error as error:
        raise ValueError(f"{path.name}: CSV no válido: {error}") from error
    for line, row in enumerate(rows, 2):
        if None in row or any(value is None or not value.strip() for value in row.values()):
            raise ValueError(f"{path.name}, fila {line}: faltan valores o hay valores de más.")
    return rows


def _node_id(value: str, location: str) -> int:
    try:
        node = int(value)
    except ValueError as error:
        raise ValueError(f"{location}: ID de nodo no válido {value!r}.") from error
    if node < 0:
        raise ValueError(
            f"{location}: los ID de los nodos deben ser enteros mayores o iguales a cero."
        )
    return node


def load_graph(nodes_path: Path, edges_path: Path) -> nx.MultiGraph:
    graph = nx.MultiGraph()
    for line, row in enumerate(_rows(nodes_path, ["id"]), 2):
        node = _node_id(row["id"], f"{nodes_path.name}, fila {line}")
        if node in graph:
            raise ValueError(f"{nodes_path.name}, fila {line}: nodo duplicado {node}.")
        graph.add_node(node)

    for line, row in enumerate(
        _rows(edges_path, ["source", "target", "weight"], optional_id=True), 2
    ):
        location = f"{edges_path.name}, fila {line}"
        source = _node_id(row["source"], location)
        target = _node_id(row["target"], location)
        if source not in graph or target not in graph:
            raise ValueError(
                f"{location}: la conexión {source}–{target} usa un nodo que no existe."
            )
        key = _node_id(row["id"], location) if "id" in row else None
        if key is not None and graph.has_edge(source, target, key):
            raise ValueError(f"{location}: ID de conexión duplicado para {source}–{target}.")
        try:
            weight = float(row["weight"])
        except ValueError as error:
            raise ValueError(f"{location}: peso no válido {row['weight']!r}.") from error
        if not math.isfinite(weight) or weight <= 0:
            raise ValueError(f"{location}: los pesos deben ser números positivos y finitos.")
        graph.add_edge(source, target, key=key, weight=weight)

    validate_graph(graph)
    return graph


def save_graph_data(data_dir: Path, graph: nx.Graph, positions: PositionMap) -> None:
    validate_graph(graph)
    if set(positions) != set(graph):
        raise ValueError("Cada nodo debe tener una posición para guardar el grafo.")
    nodes = "id\n" + "".join(f"{node}\n" for node in sorted(graph))
    edges = "source,target,weight,id\n"
    connections = sorted(
        (min(source, target), max(source, target), key, data["weight"])
        for source, target, key, data in edges_with_keys(graph)
    )
    for source, target, key, weight in connections:
        edges += f"{source},{target},{weight:.17g},{key}\n"
    atomic_write_files(
        {
            data_dir / "nodes.csv": nodes,
            data_dir / "edges.csv": edges,
            data_dir / "layout.json": serialize_layout(positions),
        }
    )


def initialize_graph_data(data_dir: Path) -> None:
    names = ("nodes.csv", "edges.csv", "layout.json")
    if any((data_dir / name).exists() for name in names):
        return
    example_dir = data_dir / "example"
    atomic_write_files(
        {data_dir / name: (example_dir / name).read_text(encoding="utf-8") for name in names}
    )
