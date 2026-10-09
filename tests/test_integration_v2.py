from pathlib import Path

import networkx as nx
import pytest
from conftest import wait_idle
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QInputDialog, QMessageBox

from graph_visualizer.core.bellman_ford import bellman_ford_steps
from graph_visualizer.core.dijkstra import dijkstra_steps
from graph_visualizer.core.floyd_warshall import floyd_warshall_steps
from graph_visualizer.export import image_exporter
from graph_visualizer.io.presets import read_preset
from graph_visualizer.ui.graph_view import GraphView

EXAMPLES = Path("src/graph_visualizer/examples")


def test_playback_stops_on_every_context_change(window):
    window.initialize()
    window.speed.setValue(50)
    window.toggle_playback()
    assert window.play_timer.isActive()
    from PySide6.QtCore import QElapsedTimer

    timer = QElapsedTimer()
    timer.start()
    while window.state_index == 0 and timer.elapsed() < 2000:
        QTest.qWait(10)
    assert window.state_index > 0
    window.toggle_playback()
    assert not window.play_timer.isActive()
    window.toggle_playback()
    window.show_state(len(window.states) - 1)
    assert not window.play_timer.isActive()
    window.show_state(0)
    window.toggle_playback()
    window.detail_checkbox.setChecked(False)
    assert not window.play_timer.isActive()
    window.toggle_playback()
    window.algorithm_combo.setCurrentText("Bellman-Ford")
    assert not window.play_timer.isActive() and not window.states
    window.initialize()
    window.toggle_playback()
    window.reset()
    assert not window.play_timer.isActive()
    window.preset_baseline = window.preset_fingerprint()
    window.initialize()
    window.toggle_playback()
    window.load_preset_path(EXAMPLES / "floyd_warshall.json")
    assert not window.play_timer.isActive() and not window.states


def test_directed_ui_conversion_and_negative_weight_rules(window, monkeypatch):
    count = window.graph.number_of_edges()
    window.editor.graph_type.setCurrentIndex(1)
    assert window.graph.is_directed()
    assert window.graph.number_of_edges() == 2 * count
    assert window.set_edge("1", "2", -3, 0)
    window.editor.graph_type.setCurrentIndex(0)
    assert not window.graph.is_directed()
    assert window.graph.number_of_edges() == 2 * count
    assert not window.editor.error_label.text()
    assert not window.run_button.isEnabled()
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a: warnings.append(a[-1]))
    window.initialize()
    assert not window.states
    assert not warnings
    assert "Dijkstra" in window.algorithm_warning.text()
    window.undo()
    assert window.graph.is_directed()
    assert not window.run_button.isEnabled()
    window.undo()
    assert window.graph["1"]["2"][0]["weight"] == 4
    assert window.run_button.isEnabled()
    window.editor.graph_type.setCurrentIndex(0)
    assert window.graph.number_of_edges() == 2 * count
    assert not window.graph.is_directed()


def test_preset_changes_do_not_autoupdate_and_failed_save_keeps_work(window, tmp_path, monkeypatch):
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Personal", True))
    assert window.save_new_preset()
    path = window.preset_path
    before = path.read_bytes()
    window.add_node("Ciudad, México")
    assert path.read_bytes() == before
    assert window.update_preset()
    assert "Ciudad, México" in read_preset(path).graph
    assert window.preset_fingerprint() == window.preset_baseline
    window.load_preset_path(EXAMPLES / "bellman_ford.json")
    window.undo()
    assert window.preset_path == path
    assert "Ciudad, México" in window.graph


def test_matrix_restores_colors_and_arc_table_tracks_exact_connection(window):
    window.load_preset_path(EXAMPLES / "floyd_warshall.json")
    window.detail_checkbox.setChecked(True)
    window.initialize()
    index = next(i for i, s in enumerate(window.states) if s.changed)
    window.show_state(index)
    state = window.states[index]
    i, j = next(iter(state.changed))
    table = window.matrix_panel.tables[0]
    assert table.item(i, j).background().color().name() == "#fef08a"
    assert table.horizontalHeaderItem(state.k).background().color().name() == "#bbf7d0"
    assert table.item(*state.cell).data(Qt.ItemDataRole.UserRole + 1)
    window.show_state(index + 10)
    window.show_state(index)
    assert window.states[index] is state
    assert table.item(i, j).background().color().name() == "#fef08a"
    window.reset()
    window.preset_baseline = window.preset_fingerprint()
    window.load_preset_path(EXAMPLES / "bellman_ford.json")
    window.initialize()
    window.show_state(2)
    assert window.state_panel.arcs.item(0, 0).background().color().name() == "#fed7aa"
    assert window.graph_view.edges["u", "v", 0].pen().color().name() == "#a66300"


@pytest.mark.parametrize("algorithm", ["Dijkstra", "Bellman-Ford", "Floyd-Warshall"])
@pytest.mark.parametrize("simple", [False, True])
def test_exports_all_algorithms_and_styles(qapp, tmp_path, monkeypatch, algorithm, simple):
    g = nx.MultiDiGraph()
    g.add_edge("A", "B", key=3, weight=2)
    positions = {"A": (0, 0), "B": (150, 0)}
    states = (
        dijkstra_steps(g, "A", "B", detailed=True)
        if algorithm == "Dijkstra"
        else bellman_ford_steps(g, "A")
        if algorithm == "Bellman-Ford"
        else floyd_warshall_steps(g, detailed=True)
    )
    seen = []
    original = GraphView.close

    def inspect(view):
        seen.append((view.nodes["A"].label.isVisible(), view.nodes["A"].caption.isVisible()))
        return original(view)

    monkeypatch.setattr(GraphView, "close", inspect)
    monkeypatch.setattr(image_exporter, "MAX_COMBINED_PIXELS", 1)
    for kind in ["current", "all", "combined", "final"]:
        path = image_exporter.export_graph(
            g, positions, states, "A", "B", 0, kind, tmp_path, simple=simple
        )
        assert path.exists()
        if kind == "combined":
            assert len(list(path.glob("conjunta_*.png"))) == len(states)
    assert all(visible == (not simple) for visible, _ in seen)
    assert all(not caption for _, caption in seen) if simple else True


def test_large_graph_worker_and_navigation(window):
    window.load_preset_path(EXAMPLES / "repositorio_30.json")
    window.algorithm_combo.setCurrentText("Floyd-Warshall")
    window.initialize()
    assert window.busy
    wait_idle(window)
    assert len(window.states) == 32
    window.show_state(15)
    step = window.states[15].step
    window.detail_checkbox.setChecked(True)
    assert window.states[window.state_index].step == step
    window.show_state(0)
    window.show_state(len(window.states) - 1)
    assert window.states[-1].phase == "Resultado"
