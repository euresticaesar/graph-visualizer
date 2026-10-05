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
    assert "distance 16" in window.detail_label.text()
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
    assert "distance 0" in window.detail_label.text()
    assert window.graph_view.nodes[1].is_target


def test_background_drag_pans(window):
    view = window.graph_view
    old_center = view.mapToScene(view.viewport().rect().center())
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(20, 20))
    QTest.mouseMove(view.viewport(), QPoint(70, 55))
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(70, 55))
    assert view.mapToScene(view.viewport().rect().center()) != old_center
