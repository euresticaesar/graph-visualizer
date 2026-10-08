"""Floyd-Warshall with persistent rows and route expression trees.

Unchanged comparisons share all matrices; an improvement replaces only one row.
Route trees retain the operands at the instant of improvement, not mutable references.
"""

import math

from graph_visualizer.core.graph import ordered_arcs, validate_graph
from graph_visualizer.core.models import (
    AlgorithmCancelled,
    AlgorithmState,
    Comparison,
    RouteTree,
    StateView,
    format_number,
)


def replace_cell(matrix, i, j, value):
    row = matrix[i][:j] + (value,) + matrix[i][j + 1 :]
    return matrix[:i] + (row,) + matrix[i + 1 :]


def floyd_warshall_steps(graph, *, detailed=False, _cancelled=None):
    validate_graph(graph)
    nodes = tuple(sorted(graph))
    n = len(nodes)
    indices = {node: i for i, node in enumerate(nodes)}
    distances = tuple(tuple(0.0 if i == j else math.inf for j in range(n)) for i in range(n))
    intermediates = tuple(tuple(nodes[i] if i == j else None for j in range(n)) for i in range(n))
    routes = tuple(tuple(None for j in range(n)) for i in range(n))
    for u, v, key, weight in ordered_arcs(graph):
        i, j = indices[u], indices[v]
        if weight < distances[i][j]:
            distances = replace_cell(distances, i, j, weight)
            intermediates = replace_cell(intermediates, i, j, v)
            routes = replace_cell(routes, i, j, RouteTree(edge=(u, v, key)))
    events = []
    changed = frozenset()

    def emit(**kw):
        if _cancelled and _cancelled():
            raise AlgorithmCancelled
        events.append(
            AlgorithmState(
                len(events),
                algorithm="Floyd-Warshall",
                directed=graph.is_directed(),
                nodes=nodes,
                matrix=distances,
                intermediates=intermediates,
                routes=routes,
                changed=changed,
                **kw,
            )
        )

    emit(
        summary=True,
        explanation="Todos los pares: diagonal 0, conexiones directas de menor "
        "peso, pares sin ruta ∞. Recorridos: destino directo, nodo propio o —.",
    )
    for k, intermediate in enumerate(nodes):
        changed = frozenset()
        emit(
            phase="Inicio de iteración",
            iteration=k + 1,
            k=k,
            current_node=intermediate,
            explanation=f"Comienza k = {intermediate}; se limpian las mejoras amarillas.",
        )
        for i, source in enumerate(nodes):
            for j, target in enumerate(nodes):
                before, left, right = distances[i][j], distances[i][k], distances[k][j]
                candidate = left + right
                if math.isfinite(left) and math.isfinite(right) and not math.isfinite(candidate):
                    raise ValueError("Las distancias exceden el rango numérico permitido.")
                improved = candidate < before
                if improved:
                    tree = RouteTree(left=routes[i][k], right=routes[k][j])
                    distances = replace_cell(distances, i, j, candidate)
                    intermediates = replace_cell(intermediates, i, j, intermediate)
                    routes = replace_cell(routes, i, j, tree)
                    changed = changed | {(i, j)}
                comparison = Comparison(
                    source, target, 0, before, left, right, candidate, improved, distances[i][j]
                )
                f = format_number
                emit(
                    phase="Comparación",
                    iteration=k + 1,
                    k=k,
                    current_node=intermediate,
                    cell=(i, j),
                    comparison=comparison,
                    explanation=f"k={intermediate}, i={source}, j={target}: "
                    f"D[i,j] anterior={f(before)}; D[i,k]={f(left)}; D[k,j]={f(right)}. "
                    f"Candidata={f(candidate)}. {'Mejora' if improved else 'Sin cambio'}; "
                    f"resultante={f(distances[i][j])}.",
                )
        emit(
            phase="Iteración completa",
            iteration=k + 1,
            k=k,
            current_node=intermediate,
            summary=True,
            explanation=f"k = {intermediate}: {len(changed)} entradas mejoradas. "
            "Cambios resaltados en negritas; borde: fila y columna de k.",
        )
    negative = [k for k in range(n) if distances[k][k] < 0]
    affected = frozenset(
        (i, j)
        for i in range(n)
        for j in range(n)
        if any(distances[i][k] != math.inf and distances[k][j] != math.inf for k in negative)
    )
    for i, j in sorted(affected):
        distances = replace_cell(distances, i, j, -math.inf)
        intermediates = replace_cell(intermediates, i, j, None)
        routes = replace_cell(routes, i, j, None)
    changed = frozenset()
    emit(
        phase="Resultado",
        iteration=n,
        summary=True,
        affected=affected,
        explanation=(
            f"{len(affected)} pares afectados por ciclos negativos: −∞ significa "
            "que no existe costo mínimo finito. Los demás pares siguen consultables."
            if affected
            else "Matrices finales para todos los pares. "
            "Los selectores solo consultan una ruta; no limitan el cálculo."
        ),
    )
    return StateView(events, detailed)
