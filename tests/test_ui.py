import json

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QGraphicsItem

from dijkstra_visualizer.ui.main_window import MainWindow
from dijkstra_visualizer.ui.node_item import PATH


def test_playback_controls_and_reset(window, qapp):
    positions = window.graph_view.positions()
    assert window.run_button.isEnabled()
    assert not window.previous_button.isEnabled()
    assert not window.next_button.isEnabled()
    QTest.mouseClick(window.run_button, Qt.MouseButton.LeftButton)
    assert window.state_index == 0
    assert window.graph_view.nodes[1].label.text() == "[0, null]"
    assert not window.start_combo.isEnabled()
    assert not window.graph_view.nodes[1].flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable
    states = window.states
    QTest.mouseClick(window.next_button, Qt.MouseButton.LeftButton)
    assert window.state_index == 1
    assert window.graph_view.nodes[5].label.text() == "[2, 1]"
    QTest.mouseClick(window.previous_button, Qt.MouseButton.LeftButton)
    assert window.graph_view.nodes[5].label.text() == "[∞, null]"
    assert window.states is states
    window.show_state(len(states) - 1)
    assert not window.next_button.isEnabled()
    assert window.graph_view.edges[1, 5].pen().color().name() == PATH
    assert "distancia 16" in window.detail_label.text()
    window.reset()
    assert window.graph_view.positions() == positions
    assert not window.states
    assert window.start_combo.isEnabled()
    assert window.graph_view.nodes[1].label.text() == "[∞, null]"
    assert window.graph_view.edges[1, 5].pen().widthF() == 2


def test_drag_updates_edges_and_persists_on_release(window, qapp):
    view = window.graph_view
    node = view.nodes[1]
    layout_path = window.data_dir / "layout.json"
    old_contents = layout_path.read_text()
    original = node.pos()
    start = view.mapFromScene(original)
    finish = start + QPoint(45, 30)
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(view.viewport(), finish, delay=10)
    assert node.pos() != original
    assert view.edges[1, 2].line().p1() == node.pos()
    assert layout_path.read_text() == old_contents
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=finish)
    saved = json.loads(layout_path.read_text())
    assert saved["1"] == {"x": node.pos().x(), "y": node.pos().y()}
    reopened = MainWindow(window.data_dir, window.output_dir)
    assert reopened.graph_view.positions() == view.positions()
    reopened.close()


def test_algorithm_mode_prevents_dragging(window, qapp):
    window.initialize()
    view = window.graph_view
    positions = view.positions()
    start = view.mapFromScene(view.nodes[1].pos())
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(view.viewport(), start + QPoint(40, 40))
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=start + QPoint(40, 40))
    assert view.positions() == positions


def test_start_equals_target_supported(window):
    window.target_combo.setCurrentIndex(0)
    window.initialize()
    window.show_state(1)
    assert "distancia 0" in window.detail_label.text()
    assert window.graph_view.nodes[1].is_target


def test_background_drag_pans(window):
    view = window.graph_view
    old_center = view.mapToScene(view.viewport().rect().center())
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(20, 20))
    QTest.mouseMove(view.viewport(), QPoint(70, 55))
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(70, 55))
    assert view.mapToScene(view.viewport().rect().center()) != old_center


def test_unreachable_target_in_ui_and_export(qapp, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    (data / "nodes.csv").write_text("id\n1\n2\n3\n")
    (data / "edges.csv").write_text("source,target,weight\n1,2,4\n")
    window = MainWindow(data, tmp_path / "output")
    try:
        window.initialize()
        window.show_state(len(window.states) - 1)
        assert "No hay ruta" in window.detail_label.text()
        assert window.graph_view.nodes[3].label.text() == "[∞, null]"
        assert window.graph_view.nodes[3].is_target
        assert all(edge.pen().widthF() == 2 for edge in window.graph_view.edges.values())
        window.export("final")
        assert len(list(window.output_dir.glob("*/final_path.png"))) == 1
    finally:
        window.close()


def test_failed_layout_save_restores_positions_and_history(window, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from dijkstra_visualizer.ui import main_window

    warnings = []
    original = window.graph_view.positions()
    history_index = window.history_index
    layout = (window.data_dir / "layout.json").read_bytes()

    def failed_save(*args):
        raise OSError("Directorio de solo lectura")

    monkeypatch.setattr(main_window, "save_layout", failed_save)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[2]))
    window.graph_view.nodes[1].setPos(200, 150)
    window._save_layout()
    assert "No se aplicó el cambio" in warnings[0]
    assert window.graph_view.positions() == original
    assert window.history_index == history_index
    assert (window.data_dir / "layout.json").read_bytes() == layout
    assert window.close()
