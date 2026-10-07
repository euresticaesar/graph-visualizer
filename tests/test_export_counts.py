import networkx as nx
import pytest
from conftest import wait_idle
from PySide6.QtCore import QElapsedTimer
from PySide6.QtTest import QTest

from graph_visualizer.core.bellman_ford import bellman_ford_steps
from graph_visualizer.core.dijkstra import dijkstra_steps
from graph_visualizer.core.floyd_warshall import floyd_warshall_steps
from graph_visualizer.export import image_exporter


def wait_preview(window):
    timer = QElapsedTimer()
    timer.start()
    while window.export_preview_timer.isActive() and timer.elapsed() < 10000:
        QTest.qWait(10)
    assert not window.export_preview_timer.isActive()
    assert window.export_count_labels["combined"].text() not in {"Calculando…", "No disponible"}


@pytest.mark.parametrize("algorithm", ["Dijkstra", "Bellman-Ford", "Floyd-Warshall"])
@pytest.mark.parametrize("simple", [False, True])
def test_combined_count_matches_png_files_for_every_algorithm(qapp, tmp_path, algorithm, simple):
    graph = nx.MultiDiGraph()
    graph.add_weighted_edges_from([("A", "B", 2), ("B", "C", 1), ("A", "C", 8)])
    positions = {"A": (0, 0), "B": (200, 0), "C": (400, 0)}
    states = (
        dijkstra_steps(graph, "A", "C")
        if algorithm == "Dijkstra"
        else bellman_ford_steps(graph, "A")
        if algorithm == "Bellman-Ford"
        else floyd_warshall_steps(graph)
    )
    job = image_exporter.combined_image_count_job(
        graph,
        positions,
        states,
        "A",
        "C",
        simple=simple,
    )
    predicted = list(job)[-1][1]
    destination = image_exporter.export_graph(
        graph,
        positions,
        states,
        "A",
        "C",
        0,
        "combined",
        tmp_path,
        simple=simple,
    )
    assert predicted == len(list(destination.glob("conjunta_*.png")))


def test_preview_counts_size_changes_and_page_limits_without_rendering(qapp, monkeypatch):
    from dataclasses import replace

    graph = nx.MultiGraph()
    graph.add_edge("A", "B", weight=2)
    positions = {"A": (0, 0), "B": (200, 0)}
    initial = dijkstra_steps(graph, "A", "B")[0]
    states = [replace(initial, explanation=text) for text in ["Corto", "Largo " * 500, "Corto"]]
    monkeypatch.setattr(
        image_exporter,
        "render_state",
        lambda *args, **kwargs: pytest.fail("Preview rendered PNG"),
    )
    predicted = list(image_exporter.combined_image_count_job(graph, positions, states, "A", "B"))
    assert predicted[-1][1] == 3
    monkeypatch.setattr(image_exporter, "MAX_COMBINED_PIXELS", 1)
    repeated = [initial] * 5
    predicted = list(image_exporter.combined_image_count_job(graph, positions, repeated, "A", "B"))
    assert predicted[-1][1] == 5


def test_ui_counts_follow_export_detail_and_match_generated_files(window):
    window.target_combo.setCurrentIndex(window.target_combo.findData("2"))
    window.initialize()
    live_state, index = window.states, window.state_index
    transform, positions = window.graph_view.transform(), window.graph_view.positions()
    window.tabs.setCurrentIndex(3)
    for mode, simple in [(0, False), (1, True), (2, True)]:
        window.export_detail.setCurrentIndex(mode)
        window.export_style.setCurrentIndex(int(simple))
        wait_preview(window)
        expected_steps = (
            sum(state.summary for state in window.states.events)
            if mode == 1
            else len(window.states.events)
        )
        assert window.export_count_labels["all"].text() == f"{expected_steps} imágenes"
        assert window.export_count_labels["current"].text() == "1 imagen"
        assert window.export_count_labels["final"].text() == "1 imagen"
        expected_images = int(window.export_count_labels["combined"].text().split()[0])
        window.export("combined")
        wait_idle(window)
        assert expected_images == len(list(window.last_export_path.glob("*.png")))
        assert window.states is live_state and window.state_index == index
        assert window.graph_view.transform() == transform
        assert window.graph_view.positions() == positions


def test_preview_cancels_on_tab_change_and_reset_and_reuses_counts(window):
    window.initialize()
    window.tabs.setCurrentIndex(3)
    wait_preview(window)
    completed = window.export_count_labels["combined"].text()
    window.tabs.setCurrentIndex(2)
    window.tabs.setCurrentIndex(3)
    assert not window.export_preview_timer.isActive()
    assert window.export_count_labels["combined"].text() == completed
    window.edge_ids_checkbox.setChecked(True)
    assert window.export_preview_timer.isActive()
    window.tabs.setCurrentIndex(2)
    assert not window.export_preview_timer.isActive()
    assert window.export_preview_job is None
    window.reset()
    assert all(label.text() == "—" for label in window.export_count_labels.values())
    assert not window.export_preview_cache
