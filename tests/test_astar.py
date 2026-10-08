import math

import networkx as nx
import pytest

from graph_visualizer.core.astar import astar_steps
from graph_visualizer.core.dijkstra import reconstruct_edge_path, reconstruct_path


@pytest.mark.parametrize("directed", [False, True])
def test_astar_matches_shortest_paths(directed):
    for seed in range(8):
        graph = nx.gnp_random_graph(9, 0.3, seed=seed, directed=directed)
        graph = nx.relabel_nodes(graph, str)
        graph = nx.MultiDiGraph(graph) if directed else nx.MultiGraph(graph)
        for u, v, key in graph.edges(keys=True):
            graph[u][v][key]["weight"] = (int(u) + int(v) + seed) % 7
        for target in graph:
            states = astar_steps(graph, "0", target, detailed=True)
            final = states[-1]
            expected = nx.single_source_dijkstra_path_length(graph, "0").get(target, math.inf)
            assert final.distances[target] == expected
            assert bool(reconstruct_path(final, "0", target)) == math.isfinite(expected)
            for u, v, data in graph.edges(data=True):
                assert final.heuristics[u] <= data["weight"] + final.heuristics[v]
            assert states[0].distances["0"] == 0
            assert final.algorithm == "A*"


def test_astar_parallel_edges_and_validation():
    graph = nx.MultiDiGraph()
    graph.add_edge("a", "b", key=3, weight=10)
    graph.add_edge("a", "b", key=8, weight=2)
    states = astar_steps(graph, "a", "b")
    assert reconstruct_edge_path(states[-1], "a", "b") == [("a", "b", 8)]
    assert reconstruct_path(states[0], "a", "b") == []
    with pytest.raises(TypeError):
        states[-1].heuristics["a"] = 12
    with pytest.raises(ValueError):
        astar_steps(graph, "missing", "b")
    graph.add_edge("b", "c", weight=-1)
    with pytest.raises(ValueError, match="negativos"):
        astar_steps(graph, "a", "b")


def test_astar_ui(window):
    window.algorithm_combo.setCurrentText("A*")
    window.initialize()
    assert window.states[-1].algorithm == "A*"
    assert not window.target_combo.isEnabled()
    assert window.state_panel.table.columnCount() == 5
    window.show_state(len(window.states) - 1)
    assert window.state_panel.table.horizontalHeaderItem(3).text() == "f = g + h"


def test_astar_worker_and_preset(window, tmp_path):
    from graph_visualizer.io.presets import Preset, read_preset, write_preset
    from graph_visualizer.ui.worker import AlgorithmWorker

    path = tmp_path / "astar.json"
    write_preset(
        path,
        Preset(
            "A*",
            window.graph,
            window.graph_view.positions(),
            {"algorithm": "A*", "start": window.start, "target": window.target},
        ),
    )
    assert read_preset(path).settings["algorithm"] == "A*"
    results = []
    worker = AlgorithmWorker(window.graph, "A*", window.start, window.target, True, False)
    worker.ready.connect(results.append)
    worker.run()
    assert results[0][-1].algorithm == "A*"
