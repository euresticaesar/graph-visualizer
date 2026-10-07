"""Versioned, validated presets. No calculated states or edit history are serialized."""

import json
import math
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import networkx as nx

from dijkstra_visualizer.core.graph import edges_with_keys, normalize_id, validate_graph
from dijkstra_visualizer.io.files import atomic_write_files
from dijkstra_visualizer.io.layout_io import PositionMap


@dataclass
class Preset:
    name: str
    graph: nx.Graph
    positions: PositionMap
    settings: dict = field(default_factory=dict)

    def document(self):
        return {
            "version": 1,
            "name": self.name,
            "directed": self.graph.is_directed(),
            "nodes": sorted(self.graph),
            "edges": [
                {"source": u, "target": v, "id": k, "weight": d["weight"]}
                for u, v, k, d in edges_with_keys(self.graph)
            ],
            "positions": {n: list(p) for n, p in self.positions.items()},
            "settings": self.settings,
        }


def parse_preset(data) -> Preset:
    try:
        if not isinstance(data, dict) or type(data["version"]) is not int or data["version"] != 1:
            raise ValueError("Versión de preset no compatible.")
        if not isinstance(data["name"], str) or not data["name"].strip():
            raise ValueError("El preset necesita un nombre.")
        if type(data["directed"]) is not bool:
            raise ValueError("Tipo de grafo no válido.")
        if not isinstance(data["nodes"], list) or not isinstance(data["edges"], list):
            raise ValueError("Nodos y conexiones deben ser listas.")
        graph = nx.MultiDiGraph() if data["directed"] else nx.MultiGraph()
        for value in data["nodes"]:
            node = normalize_id(value)
            if node in graph:
                raise ValueError("ID duplicado después de normalizar espacios.")
            graph.add_node(node)
        for edge in data["edges"]:
            u, v = normalize_id(edge["source"]), normalize_id(edge["target"])
            key = edge["id"]
            if u not in graph or v not in graph or type(key) is not int or key < 0:
                raise ValueError("Conexión no válida.")
            if graph.has_edge(u, v, key):
                raise ValueError("ID de conexión duplicado para el par.")
            graph.add_edge(u, v, key=key, weight=edge["weight"])
        validate_graph(graph)
        positions = {}
        for value, point in data["positions"].items():
            node = normalize_id(value)
            if (
                node in positions
                or len(point) != 2
                or any(
                    isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
                    for v in point
                )
            ):
                raise ValueError("Posición no válida.")
            positions[node] = tuple(point)
        if set(positions) != set(graph):
            raise ValueError("Las posiciones deben corresponder a todos los nodos.")
        settings = data.get("settings", {})
        if not isinstance(settings, dict):
            raise ValueError("Ajustes no válidos.")
        if "algorithm" in settings and settings["algorithm"] not in (
            "Dijkstra",
            "Bellman-Ford",
            "Floyd-Warshall",
        ):
            raise ValueError("Algoritmo de preset no válido.")
        for endpoint in ("start", "target"):
            if endpoint in settings:
                settings[endpoint] = normalize_id(settings[endpoint])
                if settings[endpoint] not in graph:
                    raise ValueError("El origen/destino del preset debe existir.")
        if "detail" in settings and type(settings["detail"]) is not bool:
            raise ValueError("El detalle debe ser booleano.")
        settings = {
            k: v for k, v in settings.items() if k in {"algorithm", "start", "target", "detail"}
        }
        return Preset(data["name"].strip(), graph, positions, settings)
    except (KeyError, TypeError, AttributeError, OverflowError) as error:
        raise ValueError(f"Preset incompleto o no válido: {error}") from error


def read_preset(path: Path) -> Preset:
    try:
        return parse_preset(json.loads(path.read_text(encoding="utf-8")))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"JSON no válido: {error}") from error


def write_preset(path: Path, preset: Preset) -> None:
    document = parse_preset(preset.document()).document()
    atomic_write_files(
        {path: json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n"}
    )


def new_preset_path(directory: Path) -> Path:
    return directory / f"{uuid.uuid4().hex}.json"
