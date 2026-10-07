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
