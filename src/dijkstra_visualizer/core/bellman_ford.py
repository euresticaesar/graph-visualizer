import math

from dijkstra_visualizer.core.graph import ordered_arcs, validate_graph
from dijkstra_visualizer.core.models import AlgorithmState, Comparison, StateView


def bellman_ford_steps(graph, start, *, early_stop=False):
    validate_graph(graph)
    if start not in graph:
        raise ValueError("Selecciona un origen existente.")
    arcs = ordered_arcs(graph)
    distances = dict.fromkeys(sorted(graph), math.inf)
    predecessors = dict.fromkeys(graph)
    keys = dict.fromkeys(graph)
    distances[start] = 0.0
    events = []

    def emit(**kw):
        events.append(
            AlgorithmState(
                len(events),
                distances=distances,
                predecessors=predecessors,
                predecessor_edges=keys,
                algorithm="Bellman-Ford",
                directed=graph.is_directed(),
                **kw,
            )
        )

    emit(
        summary=True,
        explanation="Origen a distancia 0; los demás a ∞. "
        + (
            "Cada conexión no dirigida genera dos arcos con la misma identidad."
            if not graph.is_directed()
            else "Se examinan los arcos en orden origen, destino, ID."
        ),
    )
    for iteration in range(1, len(graph)):
        changed = False
        emit(
            phase="Inicio de pasada",
            iteration=iteration,
            explanation=f"Pasada {iteration} de {len(graph) - 1}.",
        )
        for u, v, key, weight in arcs:
            before, pred, left = distances[v], predecessors[v], distances[u]
            candidate = left + weight
            if math.isfinite(left) and not math.isfinite(candidate):
                raise ValueError("Las distancias exceden el rango numérico permitido.")
            improved = candidate < before
            if improved:
                distances[v], predecessors[v], keys[v] = candidate, u, key
                changed = True
            comparison = Comparison(
                u,
                v,
                weight,
                before,
                left,
                weight,
                candidate,
                improved,
                distances[v],
                pred,
                predecessors[v],
            )
            emit(
                phase="Relajación",
                iteration=iteration,
                current_node=u,
                current_edge=(u, v, key),
                comparison=comparison,
                updated_nodes=frozenset({v} if improved else ()),
                explanation=f"Arco {u} → {v} · #{key} · " + comparison.explain(),
            )
        emit(
            phase="Fin de pasada",
            iteration=iteration,
            summary=True,
            explanation="Pasada con mejoras." if changed else "Pasada sin cambios.",
        )
        if early_stop and not changed:
            break
    # A separate probe pass supplies a predecessor witness and all reachable seeds.
    original = distances.copy(), predecessors.copy(), keys.copy()
    seeds = set()
    emit(
        phase="Verificación", explanation="Pasada adicional: detectar ciclos negativos alcanzables."
    )
    for u, v, key, weight in arcs:
        before, pred, left = distances[v], predecessors[v], distances[u]
        candidate = left + weight
        if math.isfinite(left) and not math.isfinite(candidate):
            raise ValueError("Las distancias exceden el rango numérico permitido.")
        improved = candidate < before
        if improved:
            distances[v], predecessors[v], keys[v] = candidate, u, key
            seeds.add(v)
        comparison = Comparison(
            u,
            v,
            weight,
            before,
            left,
            weight,
            candidate,
            improved,
            distances[v],
            pred,
            predecessors[v],
        )
        emit(
            phase="Verificación",
            current_node=u,
            current_edge=(u, v, key),
            comparison=comparison,
            explanation="Sondeo de ciclo negativo. " + comparison.explain(),
            updated_nodes=frozenset({v} if improved else ()),
        )
    cycle = []
    if seeds:
        current = sorted(seeds)[0]
        for _ in graph:
            current = predecessors[current]
        anchor = current
        for _ in range(len(graph) + 1):
            parent = predecessors[current]
            cycle.append((parent, current, keys[current]))
            current = parent
            if current == anchor:
                break
        cycle.reverse()
    affected = set(seeds)
    pending = list(seeds)
    while pending:
        u = pending.pop()
        for v in sorted(graph[u]):
            if v not in affected:
                affected.add(v)
                pending.append(v)
    distances, predecessors, keys = original
    for node in affected:
        distances[node], predecessors[node], keys[node] = -math.inf, None, None
    emit(
        phase="Resultado",
        summary=True,
        affected=frozenset(affected),
        cycle=tuple(cycle),
        explanation=(
            "Ciclo negativo alcanzable: los nodos marcados −∞ no tienen costo mínimo "
            "finito. Los demás conservan sus resultados."
            if affected
            else "No hay ciclos negativos alcanzables desde el origen. Distancias finales."
        ),
    )
    return StateView(events)
