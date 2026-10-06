import math
import random

import networkx as nx
import pytest

from dijkstra_visualizer.core.dijkstra import (
    dijkstra_steps,
    reconstruct_edge_path,
    reconstruct_path,
)


def test_parallel_edges_choose_the_cheapest_specific_connection():
    graph = nx.MultiGraph()
    graph.add_edge(0, 1, key=0, weight=9)
    graph.add_edge(0, 1, key=7, weight=2)
    graph.add_edge(1, 2, key=3, weight=4)
    graph.add_edge(0, 2, weight=20)
    states = dijkstra_steps(graph, 0, 2)
    assert states[-1].distances[2] == 6
    assert reconstruct_path(states[-1], 0, 2) == [0, 1, 2]
    assert reconstruct_edge_path(states[-1], 0, 2) == [(0, 1, 7), (1, 2, 3)]
    assert states[0].predecessor_edges == {0: None, 1: None, 2: None}
    assert states[1].predecessor_edges[2] == 0
    assert states[-1].predecessor_edges[2] == 3
    with pytest.raises(TypeError):
        states[-1].predecessor_edges[2] = 99


def test_equal_weights_choose_lowest_connection_id_in_both_directions():
    graph = nx.MultiGraph()
    graph.add_edge(1, 2, key=9, weight=3)
    graph.add_edge(2, 1, key=4, weight=3)
    for start, target in [(1, 2), (2, 1)]:
        final = dijkstra_steps(graph, start, target)[-1]
        assert reconstruct_edge_path(final, start, target) == [(1, 2, 4)]


def test_unreachable_parallel_graph_has_no_final_edges():
    graph = nx.MultiGraph()
    graph.add_node(3)
    graph.add_edge(1, 2, weight=2)
    graph.add_edge(1, 2, weight=1)
    final = dijkstra_steps(graph, 1, 3)[-1]
    assert final.distances[3] == math.inf
    assert reconstruct_edge_path(final, 1, 3) == []


@pytest.mark.parametrize("seed", range(5))
def test_parallel_graph_matches_networkx(seed):
    rng = random.Random(seed)
    graph = nx.MultiGraph()
    graph.add_nodes_from(range(8))
    for source in graph:
        for target in range(source + 1, 8):
            for _ in range(rng.randrange(4)):
                graph.add_edge(source, target, weight=rng.randint(1, 20))
    expected = nx.single_source_dijkstra_path_length(graph, 0)
    for target in graph:
        final = dijkstra_steps(graph, 0, target)[-1]
        assert final.distances[target] == expected.get(target, math.inf)
        if target in expected:
            path = reconstruct_edge_path(final, 0, target)
            assert sum(graph[u][v][key]["weight"] for u, v, key in path) == expected[target]
