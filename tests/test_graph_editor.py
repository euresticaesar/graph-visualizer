import networkx as nx
import pytest
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMenuBar, QMessageBox

from dijkstra_visualizer.io.graph_io import load_graph
from dijkstra_visualizer.io.layout_io import load_layout
from dijkstra_visualizer.ui import main_window
from dijkstra_visualizer.ui.main_window import MainWindow


def assert_saved(window):
    graph = load_graph(window.data_dir / "nodes.csv", window.data_dir / "edges.csv")
    assert nx.utils.graphs_equal(graph, window.graph)
    assert load_layout(window.data_dir / "layout.json", graph) == window.graph_view.positions()


def test_editor_buttons_add_rename_connect_and_change_weight(window, qapp):
    window.tabs.setCurrentIndex(1)
    editor = window.editor
    editor.node_id.setText("13")
    QTest.mouseClick(editor.add_button, Qt.MouseButton.LeftButton)
    assert 13 in window.graph_view.nodes
    editor.source_combo.setCurrentIndex(editor.source_combo.findData(12))
    editor.target_combo.setCurrentIndex(editor.target_combo.findData(13))
    editor.weight_input.setText("2.5")
    QTest.mouseClick(editor.save_edge_button, Qt.MouseButton.LeftButton)
    assert window.graph[12][13]["weight"] == 2.5
    editor.weight_input.setText("1.25")
    QTest.mouseClick(editor.save_edge_button, Qt.MouseButton.LeftButton)
    assert window.graph[12][13]["weight"] == 1.25
    editor.node_combo.setCurrentIndex(editor.node_combo.findData(13))
    editor.node_id.setText("14")
    QTest.mouseClick(editor.rename_button, Qt.MouseButton.LeftButton)
    assert 13 not in window.graph
    assert window.graph[12][14]["weight"] == 1.25
    editor.source_combo.setCurrentIndex(editor.source_combo.findData(12))
    editor.target_combo.setCurrentIndex(editor.target_combo.findData(14))
    QTest.mouseClick(editor.delete_edge_button, Qt.MouseButton.LeftButton)
    assert not window.graph.has_edge(12, 14)
    QTest.mouseClick(editor.delete_button, Qt.MouseButton.LeftButton)
    assert 14 not in window.graph
    assert_saved(window)


def test_history_restores_topology_positions_and_endpoints(window):
    original_graph = window.graph.copy()
    original_positions = window.graph_view.positions()
    assert window.add_node(13)
    assert window.set_edge(12, 13, 2.5)
    assert window.rename_node(1, 101)
    assert window.start == 101
    assert window.delete_node(12)
    assert window.target in window.graph
    final_graph = window.graph.copy()
    final_positions = window.graph_view.positions()
    for _ in range(4):
        window.undo()
        assert_saved(window)
    assert nx.utils.graphs_equal(window.graph, original_graph)
    assert window.graph_view.positions() == original_positions
    assert (window.start, window.target) == (1, 12)
    assert not window.undo_button.isEnabled()
    for _ in range(4):
        window.redo()
        assert_saved(window)
    assert nx.utils.graphs_equal(window.graph, final_graph)
    assert window.graph_view.positions() == final_positions
    assert not window.redo_button.isEnabled()
    reopened = MainWindow(window.data_dir, window.output_dir)
    assert nx.utils.graphs_equal(reopened.graph, final_graph)
    assert reopened.graph_view.positions() == final_positions
    reopened.close()


def test_drag_is_one_undoable_action(window, qapp):
    view = window.graph_view
    original = view.positions()
    start = view.mapFromScene(view.nodes[1].pos())
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    for offset in range(10, 50, 10):
        QTest.mouseMove(view.viewport(), start + QPoint(offset, offset))
    assert window.history_index == 0
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=start + QPoint(40, 40))
    moved = view.positions()
    assert moved != original
    assert window.history_index == 1
    window.undo()
    assert view.positions() == original
    assert_saved(window)
    window.redo()
    assert view.positions() == moved
    assert_saved(window)


def test_undo_redo_buttons_and_shortcuts(window, qapp):
    window.add_node(13)
    QTest.mouseClick(window.undo_button, Qt.MouseButton.LeftButton)
    assert 13 not in window.graph
    QTest.mouseClick(window.redo_button, Qt.MouseButton.LeftButton)
    assert 13 in window.graph
    window.activateWindow()
    window.graph_view.setFocus()
    qapp.processEvents()
    QTest.keyClick(window.graph_view, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert 13 not in window.graph
    QTest.keyClick(window.graph_view, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
    assert 13 in window.graph


def test_new_edit_clears_redo_and_selection_is_undoable(window):
    window.start_combo.setCurrentIndex(window.start_combo.findData(5))
    assert window.start == 5
    window.undo()
    assert window.start == 1
    window.redo()
    assert window.start == 5
    window.add_node(13)
    window.undo()
    window.add_node(14)
    assert not window.redo_action.isEnabled()
    assert 13 not in window.graph and 14 in window.graph


@pytest.mark.parametrize("value", ["-1", "0", "nan", "inf", "abc", ""])
def test_editor_rejects_invalid_weight(window, value):
    original = window.graph.copy()
    window.editor.weight_input.setText(value)
    window.editor.save_edge_button.click()
    assert window.editor.error_label.text()
    assert window.history_index == 0
    assert nx.utils.graphs_equal(window.graph, original)


def test_duplicate_id_and_last_node_are_rejected(window):
    assert not window.add_node(1)
    assert not window.rename_node(2, 1)
    assert window.history_index == 0
    for node in list(window.graph)[1:]:
        window.delete_node(node)
    assert not window.delete_node(1)
    assert set(window.graph) == {1}
    assert_saved(window)


def test_algorithm_locks_editing_and_history_survives_reset(window):
    window.add_node(13)
    window.initialize()
    assert not window.editor.isEnabled()
    assert not window.tabs.isTabEnabled(1)
    assert not window.undo_action.isEnabled()
    assert not window.add_node(14)
    assert not window.delete_node(1)
    assert not window.set_edge(1, 13, 4)
    window.undo()
    assert 13 in window.graph
    window.reset()
    assert window.editor.isEnabled()
    window.undo()
    assert 13 not in window.graph


def test_failed_undo_keeps_history_and_graph(window, monkeypatch):
    window.add_node(13)
    original_index = window.history_index
    before = {path: path.read_bytes() for path in window.data_dir.iterdir()}
    warnings = []

    def failed_save(*args):
        raise OSError("Sin espacio")

    monkeypatch.setattr(main_window, "save_graph_data", failed_save)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[2]))
    window.undo()
    assert window.history_index == original_index
    assert 13 in window.graph
    assert "No se pudo guardar el cambio" in warnings[0]
    assert {path: path.read_bytes() for path in window.data_dir.iterdir()} == before


def test_visible_actions_legend_and_exit(window):
    assert window.findChild(QMenuBar) is None
    assert window.legend_grid.rowCount() == 3
    assert window.legend_grid.columnCount() == 2
    assert all(window.legend_grid.itemAtPosition(row, col) for row in range(3) for col in range(2))
    assert window.exit_button.isVisible()
    assert window.exit_button.text() == "Salir"
    QTest.mouseClick(window.exit_button, Qt.MouseButton.LeftButton)
    assert not window.isVisible()
