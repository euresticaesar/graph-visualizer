from pathlib import Path

import pytest
from conftest import wait_idle
from PySide6.QtTest import QTest

from graph_visualizer.core.models import format_number
from graph_visualizer.ui.graph_view import GraphView


def assert_edge_labels(view, visible):
    for edge in view.edges.values():
        weight = format_number(edge.weight)
        assert edge.label.text() == (f"{weight} · #{edge.key}" if visible else weight)
        assert f"#{edge.key}" in edge.toolTip()
        assert edge.label.pos() + edge.label.boundingRect().center() == edge.path().pointAtPercent(
            0.5
        )


def test_toggle_preserves_parallel_paths_execution_and_saved_graph(window):
    assert not window.edge_ids_checkbox.isChecked()
    assert_edge_labels(window.graph_view, False)
    window.set_edge("1", "2", 0.5)
    window.target_combo.setCurrentIndex(window.target_combo.findData("2"))
    window.initialize()
    window.show_state(len(window.states) - 1)
    states, index = window.states, window.state_index
    positions = window.graph_view.positions()
    transform = window.graph_view.transform()
    history = window.history_index
    before = {p.name: p.read_bytes() for p in window.data_dir.iterdir() if p.is_file()}
    highlights = {key: edge.pen() for key, edge in window.graph_view.edges.items()}
    for visible in (True, False, True):
        window.edge_ids_checkbox.setChecked(visible)
        assert_edge_labels(window.graph_view, visible)
        assert window.states is states and window.state_index == index
        assert {key: edge.pen() for key, edge in window.graph_view.edges.items()} == highlights
    window.reset()
    assert_edge_labels(window.graph_view, True)
    assert window.graph_view.positions() == positions
    assert window.graph_view.transform() == transform
    assert window.history_index == history
    assert {p.name: p.read_bytes() for p in window.data_dir.iterdir() if p.is_file()} == before


@pytest.mark.parametrize("visible", [False, True])
def test_visibility_survives_edit_undo_redo_and_preset_load(window, visible):
    window.edge_ids_checkbox.setChecked(visible)
    window.set_edge("1", "2", 1.5)
    window.undo()
    window.redo()
    assert_edge_labels(window.graph_view, visible)
    window.preset_baseline = window.preset_fingerprint()
    window.load_preset_path(Path("src/graph_visualizer/examples/bellman_ford.json"))
    assert_edge_labels(window.graph_view, visible)
    window.initialize()
    window.show_state(2)
    assert_edge_labels(window.graph_view, visible)
    # Identity remains available in the algorithm's arc table.
    assert window.state_panel.arcs.horizontalHeaderItem(2).text() == "ID"
    assert window.state_panel.arcs.item(0, 2).text() == "0"


@pytest.mark.parametrize("kind", ["current", "all", "combined", "final"])
@pytest.mark.parametrize("visible", [False, True])
def test_png_exports_follow_connection_id_toggle(window, monkeypatch, kind, visible):
    window.edge_ids_checkbox.setChecked(visible)
    window.target_combo.setCurrentIndex(window.target_combo.findData("2"))
    window.export_style.setCurrentIndex(int(kind in {"combined", "final"}))
    window.initialize()
    calls = []
    apply_state = GraphView.apply_state

    def inspect(view, *args, **kwargs):
        result = apply_state(view, *args, **kwargs)
        assert_edge_labels(view, visible)
        calls.append(view.show_edge_ids)
        return result

    monkeypatch.setattr(GraphView, "apply_state", inspect)
    window.preview_before_export.setChecked(False)
    window.export(kind)
    wait_idle(window)
    assert calls == [visible] * (len(window.states) if kind in {"all", "combined"} else 1)
    assert window.last_export_path.exists()
    assert_edge_labels(window.graph_view, visible)


def test_weight_label_still_opens_exact_parallel_connection(window, monkeypatch):
    from PySide6.QtCore import Qt

    window.set_edge("1", "2", 0.5)
    selected = []
    window.graph_view.edge_edit_requested.connect(lambda *edge: selected.append(edge))
    monkeypatch.setattr(window, "_request_weight", lambda *args: None)
    for visible in (False, True):
        window.edge_ids_checkbox.setChecked(visible)
        for key in (0, 1):
            edge = window.graph_view.edges["1", "2", key]
            center = edge.label.mapToScene(edge.label.boundingRect().center())
            position = window.graph_view.mapFromScene(center)
            QTest.mouseClick(window.graph_view.viewport(), Qt.MouseButton.LeftButton, pos=position)
            assert selected[-1] == ("1", "2", key)
