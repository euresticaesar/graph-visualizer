"""Validate and serialize optional manual label positions by exact connection ID."""

import math

from graph_visualizer.core.graph import edge_id, edges_with_keys


def label_offset(value):
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 2
        or any(
            type(component) not in (int, float)
            or not math.isfinite(component)
            or abs(component) > 10000
            for component in value
        )
    ):
        raise ValueError("Los desplazamientos de etiqueta deben ser números entre −10000 y 10000.")
    return tuple(float(component) for component in value)


def edge_label_records(graph):
    records = []
    for u, v, key, data in edges_with_keys(graph):
        offset = label_offset(data.get("label_offset", (0, 0)))
        if offset != (0, 0):
            u, v, key = edge_id(u, v, key, graph.is_directed())
            records.append({"source": u, "target": v, "id": key, "offset": list(offset)})
    return sorted(records, key=lambda item: (item["source"], item["target"], item["id"]))


def apply_edge_labels(graph, records):
    if not isinstance(records, list):
        raise ValueError("Las posiciones de etiquetas deben ser una lista.")
    seen, updates = set(), []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Posición de etiqueta no válida.")
        u, v, key = record.get("source"), record.get("target"), record.get("id")
        if (
            not isinstance(u, str)
            or not isinstance(v, str)
            or type(key) is not int
            or key < 0
            or not graph.has_edge(u, v, key)
        ):
            raise ValueError("La etiqueta debe identificar una conexión existente.")
        identity = edge_id(u, v, key, graph.is_directed())
        if identity in seen:
            raise ValueError("Posición de etiqueta duplicada.")
        seen.add(identity)
        updates.append((u, v, key, label_offset(record.get("offset"))))
    for u, v, key, offset in updates:
        graph[u][v][key]["label_offset"] = offset
