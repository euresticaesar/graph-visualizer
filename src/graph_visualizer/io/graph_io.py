import csv
import io
import json
from pathlib import Path

import networkx as nx

from graph_visualizer.core.graph import edges_with_keys, validate_graph
from graph_visualizer.io.edge_labels import apply_edge_labels, edge_label_records
from graph_visualizer.io.files import atomic_write_files
from graph_visualizer.io.layout_io import PositionMap, serialize_layout


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


def _node_id(value: str, location: str) -> str:
    from graph_visualizer.core.graph import normalize_id

    return normalize_id(value)


def load_graph(nodes_path: Path, edges_path: Path) -> nx.MultiGraph:
    metadata = nodes_path.parent / "graph.json"
    directed = False
    info = {}
    if metadata.exists():
        info = json.loads(metadata.read_text(encoding="utf-8"))
        if (
            not isinstance(info, dict)
            or type(info.get("version")) is not int
            or info.get("version") != 1
            or type(info.get("directed")) is not bool
        ):
            raise ValueError("Métadatos de grafo no válidos.")
        directed = info["directed"]
    graph = nx.MultiDiGraph() if directed else nx.MultiGraph()
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
        try:
            key = int(row["id"]) if "id" in row else None
        except ValueError as error:
            raise ValueError(f"{location}: ID de conexión no válido.") from error
        if key is not None and graph.has_edge(source, target, key):
            raise ValueError(f"{location}: ID de conexión duplicado para {source}–{target}.")
        try:
            weight = float(row["weight"])
        except ValueError as error:
            raise ValueError(f"{location}: peso no válido {row['weight']!r}.") from error
        graph.add_edge(source, target, key=key, weight=weight)

    apply_edge_labels(graph, info.get("edge_labels", []))
    validate_graph(graph)
    return graph


def save_graph_data(data_dir: Path, graph: nx.Graph, positions: PositionMap) -> None:
    validate_graph(graph)
    if set(positions) != set(graph):
        raise ValueError("Cada nodo debe tener una posición para guardar el grafo.")
    nodes_stream, edges_stream = io.StringIO(newline=""), io.StringIO(newline="")
    writer = csv.writer(nodes_stream)
    writer.writerow(["id"])
    writer.writerows((node,) for node in sorted(graph))
    writer = csv.writer(edges_stream)
    writer.writerow(["source", "target", "weight", "id"])
    from graph_visualizer.core.graph import edge_id

    connections = sorted(
        (*edge_id(u, v, k, graph.is_directed()), d["weight"])
        for u, v, k, d in edges_with_keys(graph)
    )
    for source, target, key, weight in connections:
        writer.writerow([source, target, repr(float(weight)), key])
    nodes, edges = nodes_stream.getvalue(), edges_stream.getvalue()
    atomic_write_files(
        {
            data_dir / "graph.json": json.dumps(
                {
                    "version": 1,
                    "directed": graph.is_directed(),
                    "edge_labels": edge_label_records(graph),
                }
            ),
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
    if example_dir.exists():
        atomic_write_files(
            {data_dir / name: (example_dir / name).read_text(encoding="utf-8") for name in names}
        )
    else:
        from graph_visualizer.io.presets import read_preset

        preset = read_preset(Path(__file__).resolve().parents[1] / "examples" / "ejemplo_12.json")
        save_graph_data(data_dir, preset.graph, preset.positions)
