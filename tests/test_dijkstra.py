import math
import random
from dataclasses import FrozenInstanceError

import networkx as nx
import pytest

from graph_visualizer.core.dijkstra import (
    dijkstra_steps as run_steps,
)
from graph_visualizer.core.dijkstra import (
    reconstruct_path as path_of,
)


def dijkstra_steps(graph, start, target):
    return run_steps(graph, str(start), str(target))


def reconstruct_path(state, start, target):
    return path_of(state, str(start), str(target))


def weighted_graph(edges, nodes=()):
    graph = nx.Graph()
    graph.add_nodes_from(str(n) for n in nodes)
    graph.add_weighted_edges_from((str(u), str(v), w) for u, v, w in edges)
    return graph


def test_simple_path_and_initial_state():
    graph = weighted_graph([(1, 2, 2), (2, 3, 3)])
    states = dijkstra_steps(graph, 1, 3)
    initial, final = states[0], states[-1]
    assert initial.step == 0
    assert initial.current_node is None
    assert initial.distances == {"1": 0, "2": math.inf, "3": math.inf}
    assert initial.predecessors == {"1": None, "2": None, "3": None}
    assert initial.visited == initial.updated_nodes == frozenset()
    assert final.distances == {"1": 0, "2": 2, "3": 5}
    assert final.predecessors == {"1": None, "2": "1", "3": "2"}
    assert reconstruct_path(final, 1, 3) == ["1", "2", "3"]
    assert [state.step for state in states] == sorted({state.step for state in states})
    assert [state.current_node for state in states] == [None, "1", "2", "3"]
    assert states[1].visited == {"1"}
    assert states[1].updated_nodes == {"2"}
    assert all(state.distances["1"] == 0 for state in states)


def test_competing_routes_and_tentative_target():
    graph = weighted_graph([(1, 4, 20), (1, 2, 3), (1, 3, 8), (2, 3, 2), (3, 4, 1)])
    states = dijkstra_steps(graph, 1, 4)
    assert states[1].distances["4"] == 20
    assert "4" not in states[1].visited
    assert reconstruct_path(states[1], 1, 4) == []
    assert states[2].distances["3"] == 5
    assert states[2].predecessors["3"] == "2"
    assert states[-1].distances["4"] == 6
    assert reconstruct_path(states[-1], 1, 4) == ["1", "2", "3", "4"]


def test_stops_when_target_is_settled():
    graph = weighted_graph([(1, 2, 1), (2, 3, 1), (1, 4, 100)])
    final = dijkstra_steps(graph, 1, 2)[-1]
    assert final.visited == {"1", "2"}
    assert final.distances["3"] == math.inf
    assert final.distances["4"] == 100


def test_unreachable_target():
    graph = weighted_graph([(1, 2, 2), (3, 4, 1)])
    states = dijkstra_steps(graph, 1, 4)
    assert len(states) == 3
    assert states[-1].visited == {"1", "2"}
    assert math.isinf(states[-1].distances["4"])
    assert reconstruct_path(states[-1], 1, 4) == []


def test_start_equals_target():
    states = dijkstra_steps(weighted_graph([], [1]), 1, 1)
    assert len(states) == 2
    assert states[-1].distances["1"] == 0
    assert reconstruct_path(states[-1], 1, 1) == ["1"]


def test_snapshots_are_independent_and_immutable():
    states = dijkstra_steps(weighted_graph([(1, 2, 1), (2, 3, 1)]), 1, 3)
    assert math.isinf(states[0].distances["2"])
    assert states[1].predecessors["3"] is None
    assert states[1].visited == {"1"}
    with pytest.raises(TypeError):
        states[1].distances["2"] = 99
    with pytest.raises(TypeError):
        states[1].predecessors["2"] = 3
    with pytest.raises(FrozenInstanceError):
        states[1].step = 42
    assert states[1].distances is not states[2].distances


def test_ties_are_deterministic():
    graph = weighted_graph([(1, 3, 1), (1, 2, 1), (3, 4, 1), (2, 4, 1)])
    states = dijkstra_steps(graph, 1, 4)
    assert [state.current_node for state in states] == [None, "1", "2", "3", "4"]
    assert reconstruct_path(states[-1], 1, 4) == ["1", "2", "4"]


@pytest.mark.parametrize("weight", [-1, math.inf, math.nan, "2", True, None])
def test_rejects_invalid_weights(weight):
    with pytest.raises(ValueError, match="peso|negativos"):
        dijkstra_steps(weighted_graph([(1, 2, weight)]), 1, 2)


@pytest.mark.parametrize("start,target", [(0, 2), (1, 9), (True, 2), (1, None)])
def test_rejects_invalid_endpoints(start, target):
    with pytest.raises(ValueError):
        dijkstra_steps(weighted_graph([(1, 2, 1)]), start, target)


@pytest.mark.parametrize("graph", [nx.Graph(), nx.DiGraph([(1, 2)]), nx.MultiDiGraph([(1, 2)])])
def test_rejects_invalid_graph_type(graph):
    with pytest.raises(ValueError):
        dijkstra_steps(graph, 1, 2)


def test_fractional_weights():
    final = dijkstra_steps(weighted_graph([(1, 2, 0.25), (2, 3, 0.5)]), 1, 3)[-1]
    assert final.distances["3"] == pytest.approx(0.75)


@pytest.mark.parametrize("seed", range(10))
def test_matches_networkx_reference(seed):
    rng = random.Random(seed)
    graph = nx.Graph()
    graph.add_nodes_from(map(str, range(1, 16)))
    for source in graph:
        for target in map(str, range(int(source) + 1, 16)):
            if rng.random() < 0.2:
                graph.add_edge(source, target, weight=rng.randint(1, 20))
    reference = nx.single_source_dijkstra_path_length(graph, "1")
    for target in graph:
        states = dijkstra_steps(graph, 1, target)
        final = states[-1]
        assert final.distances[target] == reference.get(target, math.inf)
        for node in final.visited:
            assert final.distances[node] == reference[node]
        for previous, current in zip(states, states[1:], strict=False):
            assert current.visited == previous.visited | {current.current_node}
            assert all(current.distances[node] <= previous.distances[node] for node in graph)
        path = reconstruct_path(final, 1, target)
        if target in reference:
            assert path[0] == "1" and path[-1] == target
            assert (
                sum(graph[u][v]["weight"] for u, v in zip(path, path[1:], strict=False))
                == reference[target]
            )
        else:
            assert path == []


def test_zero_and_large_node_ids():
    large_id = str(10**30)
    graph = weighted_graph([(0, 1, 2), (1, large_id, 3)])
    final = dijkstra_steps(graph, 0, large_id)[-1]
    assert final.distances[large_id] == 5
    assert final.predecessors["1"] == "0"
    assert reconstruct_path(final, 0, large_id) == ["0", "1", large_id]
    assert reconstruct_path(dijkstra_steps(graph, large_id, 0)[-1], large_id, 0) == [
        large_id,
        "1",
        "0",
    ]


@pytest.mark.parametrize("node", [-1, 0.5, 1.0])
def test_rejects_negative_and_decimal_node_ids(node):
    with pytest.raises(ValueError, match="ID"):
        run_steps(nx.Graph([(node, "2", {"weight": 1})]), node, "2")
