import json
import math
import os
import tempfile
from pathlib import Path

import networkx as nx

PositionMap = dict[int, tuple[float, float]]


def load_layout(path: Path, graph: nx.Graph) -> PositionMap:
    positions: PositionMap = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as error:
            raise ValueError(f"{path.name}: invalid JSON layout: {error}") from error
        if not isinstance(data, dict):
            raise ValueError(f"{path.name}: layout must be an object keyed by node ID.")
        for key, point in data.items():
            try:
                node = int(key)
                if node <= 0 or str(node) != key or not isinstance(point, dict):
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
                raise ValueError(f"{path.name}: invalid position for node {key!r}.") from error
            if node in graph:
                positions[node] = (float(x), float(y))

    missing = set(graph) - positions.keys()
    if missing:
        # Keep stored positions fixed; only place nodes that have no coordinates.
        radius = max(300, 35 * len(graph))
        for index, node in enumerate(sorted(graph)):
            if node in missing:
                angle = 2 * math.pi * index / len(graph)
                x, y = 450 + radius * math.cos(angle), 330 + radius * math.sin(angle)
                while any(math.hypot(x - px, y - py) < 100 for px, py in positions.values()):
                    x += 110
                positions[node] = (x, y)
    return positions


def save_layout(path: Path, positions: PositionMap) -> None:
    data = {str(node): {"x": x, "y": y} for node, (x, y) in sorted(positions.items())}
    content = json.dumps(data, indent=2, allow_nan=False) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    # Replace atomically so an interrupted save cannot truncate the previous layout.
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as stream:
            temporary = stream.name
            stream.write(content)
        os.replace(temporary, path)
    finally:
        if temporary and Path(temporary).exists():
            Path(temporary).unlink()
