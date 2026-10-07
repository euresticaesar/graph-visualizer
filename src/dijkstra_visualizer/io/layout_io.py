import json
import math
from pathlib import Path

import networkx as nx

from dijkstra_visualizer.io.files import atomic_write_files

PositionMap = dict[str, tuple[float, float]]


def load_layout(path: Path, graph: nx.Graph) -> PositionMap:
    positions: PositionMap = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as error:
            raise ValueError(f"{path.name}: JSON de posiciones no válido: {error}") from error
        if not isinstance(data, dict):
            raise ValueError(
                f"{path.name}: las posiciones deben estar en un objeto con los ID como claves."
            )
        for key, point in data.items():
            try:
                node = key
                if not node or node.strip() != node or not isinstance(point, dict):
                    raise ValueError
                x, y = point["x"], point["y"]
                if any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    for value in (x, y)
                ):
                    raise ValueError
            except (ValueError, TypeError, KeyError, OverflowError) as error:
                raise ValueError(
                    f"{path.name}: posición no válida para el nodo {key!r}."
                ) from error
            if node in graph:
                positions[node] = (float(x), float(y))

    missing = set(graph) - positions.keys()
    if missing:
        # Conserva las posiciones guardadas; ubica solo los nodos sin coordenadas.
        radius = max(300, 35 * len(graph))
        for index, node in enumerate(sorted(graph)):
            if node in missing:
                angle = 2 * math.pi * index / len(graph)
                x, y = 450 + radius * math.cos(angle), 330 + radius * math.sin(angle)
                while any(math.hypot(x - px, y - py) < 100 for px, py in positions.values()):
                    x += 110
                positions[node] = (x, y)
    return positions


def serialize_layout(positions: PositionMap) -> str:
    data = {str(node): {"x": x, "y": y} for node, (x, y) in sorted(positions.items())}
    return json.dumps(data, indent=2, allow_nan=False) + "\n"


def save_layout(path: Path, positions: PositionMap) -> None:
    atomic_write_files({path: serialize_layout(positions)})
