import math

import networkx as nx
import pytest

from dijkstra_visualizer.core.dijkstra import (
    dijkstra_steps,
    reconstruct_edge_path,
    reconstruct_path,
)
from dijkstra_visualizer.core.models import StateView


def test_dijkstra_comparisons_and_modes():
    g = nx.MultiDiGraph()
    g.add_edge("A", "2", key=1, weight=5)
    g.add_edge("A", "2", key=0, weight=5)
    g.add_edge("A", "10", weight=0)
    g.add_edge("10", "2", weight=1)
    states = dijkstra_steps(g, "A", "2", detailed=True)
    comparisons = [s for s in states if s.comparison]
    assert [s.current_edge for s in comparisons] == [
        ("A", "10", 0),
        ("A", "2", 0),
        ("A", "2", 1),
        ("10", "2", 0),
    ]
    assert [s.comparison.improved for s in comparisons] == [True, True, False, True]
    assert reconstruct_path(states[-1], "A", "2") == ["A", "10", "2"]
    assert reconstruct_edge_path(states[-1], "A", "2") == [("A", "10", 0), ("10", "2", 0)]
    summary = StateView(states.events, False)
    assert summary[-1] is states[-1]
    assert summary[summary.equivalent(comparisons[1].step)].iteration == 1
    assert states[0].distances["2"] == math.inf
    with pytest.raises(TypeError):
        states[0].distances["2"] = 9
    assert list(reversed(list(reversed(states)))) == list(states)


def test_dijkstra_constraints():
    g = nx.MultiDiGraph()
    g.add_nodes_from(["A", "B"])
    assert reconstruct_path(dijkstra_steps(g, "A", "A")[-1], "A", "A") == ["A"]
    assert reconstruct_path(dijkstra_steps(g, "A", "B")[-1], "A", "B") == []
    g.add_edge("A", "B", weight=-1)
    with pytest.raises(ValueError, match="negativos"):
        dijkstra_steps(g, "A", "B")


def test_bellman_passes_order_and_negative_cycles():
    from dijkstra_visualizer.core.bellman_ford import bellman_ford_steps
    from dijkstra_visualizer.core.graph import ordered_arcs

    g = nx.MultiDiGraph()
    g.add_weighted_edges_from(
        [
            ("A", "B", 1),
            ("B", "C", -2),
            ("C", "B", 0),
            ("C", "D", 3),
            ("A", "E", 5),
            ("X", "Y", -3),
            ("Y", "X", 1),
        ]
    )
    states = bellman_ford_steps(g, "A")
    relaxation = [s for s in states if s.phase == "Relajación"]
    assert len(relaxation) == (len(g) - 1) * len(ordered_arcs(g))
    assert [s.current_edge for s in relaxation[: g.number_of_edges()]] == [
        a[:3] for a in ordered_arcs(g)
    ]
    assert any(s.comparison.left == math.inf for s in relaxation)
    final = states[-1]
    assert final.affected == {"B", "C", "D"}
    assert final.cycle
    assert sum(g[u][v][k]["weight"] for u, v, k in final.cycle) < 0
    assert reconstruct_path(final, "A", "E") == ["A", "E"]
    assert reconstruct_path(final, "A", "B") == []
    assert final.distances["X"] == math.inf
    assert states[0].distances["B"] == math.inf


def test_bellman_reference_and_early_stop():
    from pathlib import Path

    from dijkstra_visualizer.core.bellman_ford import bellman_ford_steps
    from dijkstra_visualizer.io.presets import read_preset

    g = read_preset(Path("src/dijkstra_visualizer/examples/bellman_ford.json")).graph
    states = bellman_ford_steps(g, "z")
    assert dict(states[-1].distances) == nx.single_source_bellman_ford_path_length(g, "z")
    assert dict(bellman_ford_steps(g, "z", early_stop=True)[-1].distances) == dict(
        states[-1].distances
    )


def test_floyd_all_pairs_and_persistent_matrices():
    from pathlib import Path

    from dijkstra_visualizer.core.floyd_warshall import floyd_warshall_steps
    from dijkstra_visualizer.io.presets import read_preset
    from dijkstra_visualizer.ui.state_panel import matrix_style

    g = read_preset(Path("src/dijkstra_visualizer/examples/floyd_warshall.json")).graph
    states = floyd_warshall_steps(g, detailed=True)
    assert len([s for s in states if s.comparison]) == len(g) ** 3
    reference = dict(nx.floyd_warshall(g))
    final = states[-1]
    for i, u in enumerate(final.nodes):
        for j, v in enumerate(final.nodes):
            assert final.matrix[i][j] == reference[u][v]
            edges = reconstruct_edge_path(final, u, v)
            assert sum(g[a][b][k]["weight"] for a, b, k in edges) == reference[u][v]
    unchanged = next(i for i, s in enumerate(states) if s.comparison and not s.comparison.improved)
    assert states[unchanged].matrix is states[unchanged - 1].matrix
    changed = next(s for s in states if s.changed)
    assert matrix_style(changed, *next(iter(changed.changed)))[0] == "#fef08a"
    assert states[1].changed == frozenset()
    assert states[0].matrix[0][0] == 0
    assert len(StateView(states.events, False)) == len(g) + 2


def test_floyd_negative_cycle_pairs_and_exact_parallel_edge():
    from dijkstra_visualizer.core.floyd_warshall import floyd_warshall_steps

    g = nx.MultiDiGraph()
    g.add_weighted_edges_from([("A", "B", 1), ("B", "C", -2), ("C", "B", 1), ("C", "D", 1)])
    g.add_edge("X", "Y", key=3, weight=2)
    g.add_edge("X", "Y", key=1, weight=2)
    final = floyd_warshall_steps(g)[-1]
    idx = {u: i for i, u in enumerate(final.nodes)}
    assert final.matrix[idx["A"]][idx["D"]] == -math.inf
    assert final.matrix[idx["A"]][idx["A"]] == 0
    assert reconstruct_path(final, "A", "D") == []
    assert reconstruct_path(final, "X", "Y") == ["X", "Y"]
    assert reconstruct_edge_path(final, "X", "Y") == [("X", "Y", 1)]
    assert reconstruct_path(final, "Y", "X") == []
