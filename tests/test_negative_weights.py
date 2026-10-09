import math
from pathlib import Path

import networkx as nx
import pytest
from conftest import wait_idle
from PySide6.QtWidgets import QInputDialog, QMessageBox

from graph_visualizer.core.astar import astar_steps
from graph_visualizer.core.bellman_ford import bellman_ford_steps
from graph_visualizer.core.dijkstra import dijkstra_steps, reconstruct_edge_path, reconstruct_path
from graph_visualizer.core.floyd_warshall import floyd_warshall_steps
from graph_visualizer.io.graph_io import load_graph, save_graph_data
from graph_visualizer.io.presets import Preset, read_preset, write_preset


@pytest.mark.parametrize("directed", [False, True])
def test_signed_graph_and_incompatible_settings_roundtrip(tmp_path, directed):
    graph = nx.MultiDiGraph() if directed else nx.MultiGraph()
    graph.add_edge("A", "B", key=7, weight=-2.5, label_offset=(12, -8))
    graph.add_edge("A", "B", key=3, weight=0)
    positions = {"A": (0, 1), "B": (2, 3)}
    save_graph_data(tmp_path, graph, positions)
    loaded = load_graph(tmp_path / "nodes.csv", tmp_path / "edges.csv")
    assert nx.utils.graphs_equal(graph, loaded)
    preset = Preset("Trabajo actual", graph, positions, {"algorithm": "Dijkstra"})
    file = tmp_path / "preset.json"
    write_preset(file, preset)
    assert read_preset(file).document() == preset.document()


@pytest.mark.parametrize("algorithm", [dijkstra_steps, astar_steps])
@pytest.mark.parametrize("directed", [False, True])
@pytest.mark.parametrize("location", ["parallel", "unreachable"])
def test_incompatible_algorithms_reject_any_negative_edge(algorithm, directed, location):
    graph = nx.MultiDiGraph() if directed else nx.MultiGraph()
    graph.add_edge("A", "B", key=0, weight=0)
    if location == "parallel":
        graph.add_edge("A", "B", key=4, weight=-0.125)
    else:
        graph.add_edge("X", "Y", weight=-0.125)
    with pytest.raises(ValueError, match="no admite pesos negativos; usa Bellman-Ford"):
        algorithm(graph, "A", "B")


def test_undirected_negative_cycle_preserves_unaffected_component():
    graph = nx.MultiGraph()
    graph.add_weighted_edges_from([("A", "B", -2), ("B", "C", 1), ("X", "Y", 3)])
    final = bellman_ford_steps(graph, "A")[-1]
    assert final.affected == {"A", "B", "C"}
    assert all(final.distances[node] == -math.inf for node in final.affected)
    assert sum(graph[u][v][k]["weight"] for u, v, k in final.cycle) < 0
    assert reconstruct_path(final, "A", "C") == []
    assert final.distances["X"] == math.inf
    unaffected = bellman_ford_steps(graph, "X")[-1]
    assert not unaffected.affected
    assert unaffected.distances["Y"] == 3
    final = floyd_warshall_steps(graph)[-1]
    for i, u in enumerate(final.nodes):
        for j, v in enumerate(final.nodes):
            if u in {"A", "B", "C"} and v in {"A", "B", "C"}:
                assert final.matrix[i][j] == -math.inf
                assert reconstruct_edge_path(final, u, v) == []
            elif u == v:
                assert final.matrix[i][j] == 0
            elif {u, v} == {"X", "Y"}:
                assert final.matrix[i][j] == 3
            else:
                assert final.matrix[i][j] == math.inf


def signed_thirty_node_graph():
    example = read_preset(Path("src/graph_visualizer/examples/repositorio_30.json"))
    graph = nx.MultiDiGraph()
    graph.add_nodes_from(example.graph)
    # Orient each connection in lexical order to make a DAG with signed weights.
    for index, (u, v, data) in enumerate(example.graph.edges(data=True)):
        source, target = sorted((u, v))
        weight = -data["weight"] if index % 7 == 0 else data["weight"]
        graph.add_edge(source, target, weight=weight)
        graph.add_edge(source, target, weight=weight + 1)
    return graph, example.positions


def test_signed_thirty_node_distances_and_exact_routes_match_networkx():
    graph, _ = signed_thirty_node_graph()
    assert len(graph) == 30 and nx.is_directed_acyclic_graph(graph)
    final = floyd_warshall_steps(graph)[-1]
    for i, start in enumerate(final.nodes):
        expected = nx.single_source_bellman_ford_path_length(graph, start)
        bellman = bellman_ford_steps(graph, start, early_stop=True)[-1]
        for j, target in enumerate(final.nodes):
            distance = expected.get(target, math.inf)
            assert bellman.distances[target] == final.matrix[i][j] == distance
            for state in (bellman, final):
                route = reconstruct_edge_path(state, start, target)
                if math.isfinite(distance):
                    assert sum(graph[u][v][k]["weight"] for u, v, k in route) == distance
                else:
                    assert not route


@pytest.mark.parametrize("directed", [False, True])
def test_negative_editor_and_canvas_input_update_availability(window, directed, monkeypatch):
    window.editor.graph_type.setCurrentIndex(int(directed))
    window.tabs.setCurrentIndex(1)
    window.editor.select_edge("1", "2", 0)
    window.editor.weight_input.setText("-2.5")
    window.editor.save_edge_button.click()
    assert not window.editor.error_label.text()
    assert window.graph["1"]["2"][0]["weight"] == -2.5
    assert (
        load_graph(window.data_dir / "nodes.csv", window.data_dir / "edges.csv")["1"]["2"][0][
            "weight"
        ]
        == -2.5
    )
    assert not window.run_button.isEnabled()
    assert "Dijkstra" in window.algorithm_warning.text()
    for algorithm in ("Bellman-Ford", "Floyd-Warshall", "A*", "Dijkstra"):
        window.algorithm_combo.setCurrentText(algorithm)
        compatible = algorithm in {"Bellman-Ford", "Floyd-Warshall"}
        assert window.run_button.isEnabled() == compatible
        assert window.algorithm_warning.isHidden() == compatible
    window.undo()
    assert window.run_button.isEnabled()
    assert window.algorithm_warning.isHidden()
    window.redo()
    assert not window.run_button.isEnabled()
    window.reset()
    assert not window.run_button.isEnabled()
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("-0.5", True))
    assert window._request_weight("1", "2", 4) == -0.5
    assert window.set_edge("1", "2", 0, 0)
    assert window.run_button.isEnabled()
    assert window.algorithm_warning.isHidden()


@pytest.mark.parametrize("directed", [False, True])
def test_loading_signed_thirty_node_preset_blocks_before_worker_and_runs_supported_algorithms(
    window, tmp_path, monkeypatch, directed
):
    graph, positions = signed_thirty_node_graph()
    if not directed:
        graph = nx.MultiGraph(graph)
    start, target = min(graph), max(graph)
    preset = Preset(
        "Trabajo actual",
        graph,
        positions,
        {"algorithm": "Dijkstra", "start": start, "target": target, "detail": False},
    )
    file = tmp_path / "signed.json"
    write_preset(file, preset)
    assert window.load_preset_path(file)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[-1]))
    for algorithm in ("Dijkstra", "A*"):
        window.algorithm_combo.setCurrentText(algorithm)
        assert not window.run_button.isEnabled()
        assert algorithm in window.algorithm_warning.text()
        window.initialize()
        assert not window.states and not window.busy and window.worker is None
        assert window.editor.isEnabled()
    for algorithm in ("Bellman-Ford", "Floyd-Warshall"):
        window.algorithm_combo.setCurrentText(algorithm)
        assert window.run_button.isEnabled()
        window.run_button.click()
        assert window.busy
        wait_idle(window)
        final = window.states[-1]
        expected = (
            nx.single_source_bellman_ford_path_length(graph, start).get(target, math.inf)
            if directed
            else -math.inf
        )
        if algorithm == "Bellman-Ford":
            assert final.distances[target] == expected
        else:
            assert final.matrix[final.nodes.index(start)][final.nodes.index(target)] == expected
        assert not window.run_button.isEnabled()
        window.reset()
        assert window.run_button.isEnabled()
    assert not warnings
    window.algorithm_combo.setCurrentText("Dijkstra")
    for u, v, key, data in list(window.graph.edges(keys=True, data=True)):
        if data["weight"] < 0:
            assert window.delete_edge(u, v, key)
    assert window.run_button.isEnabled()
    assert window.algorithm_warning.isHidden()
