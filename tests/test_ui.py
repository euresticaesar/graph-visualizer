import json

from conftest import wait_idle
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QGraphicsItem

from graph_visualizer.ui.main_window import MainWindow
from graph_visualizer.ui.node_item import PATH


def test_playback_controls_and_reset(window, qapp):
    positions = window.graph_view.positions()
    assert window.run_button.isEnabled()
    assert not window.previous_button.isEnabled()
    assert not window.next_button.isEnabled()
    window.detail_checkbox.setChecked(False)
    window.target_combo.setCurrentIndex(window.target_combo.findData("12"))
    QTest.mouseClick(window.run_button, Qt.MouseButton.LeftButton)
    assert window.state_index == 0
    assert window.graph_view.nodes["1"].label.text() == "[0, —]"
    assert not window.start_combo.isEnabled()
    assert not window.graph_view.nodes["1"].flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable
    states = window.states
    QTest.mouseClick(window.next_button, Qt.MouseButton.LeftButton)
    assert window.state_index == 1
    assert window.graph_view.nodes["5"].label.text() == "[2, 1]"
    QTest.mouseClick(window.previous_button, Qt.MouseButton.LeftButton)
    assert window.graph_view.nodes["5"].label.text() == "[∞, —]"
    assert window.states is states
    window.show_state(len(states) - 1)
    assert not window.next_button.isEnabled()
    assert window.graph_view.edges["1", "5", 0].pen().color().name() == PATH
    assert "Costo 16" in window.detail_label.text()
    window.reset()
    assert window.graph_view.positions() == positions
    assert not window.states
    assert window.start_combo.isEnabled()
    assert window.graph_view.nodes["1"].label.text() == "[∞, —]"
    assert window.graph_view.edges["1", "5", 0].pen().widthF() == 2


def test_drag_updates_edges_and_persists_on_release(window, qapp):
    view = window.graph_view
    node = view.nodes["1"]
    layout_path = window.data_dir / "layout.json"
    old_contents = layout_path.read_text()
    original = node.pos()
    start = view.mapFromScene(original)
    finish = start + QPoint(45, 30)
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(view.viewport(), finish, delay=10)
    assert node.pos() != original
    assert view.edges["1", "2", 0].path().pointAtPercent(0) == node.pos()
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
    start = view.mapFromScene(view.nodes["1"].pos())
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(view.viewport(), start + QPoint(40, 40))
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=start + QPoint(40, 40))
    assert view.positions() == positions


def test_start_equals_target_supported(window):
    window.target_combo.setCurrentIndex(0)
    window.initialize()
    window.show_state(1)
    assert "Costo 0" in window.detail_label.text()
    assert window.graph_view.nodes["1"].is_target


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
        assert window.graph_view.nodes["3"].label.text() == "[∞, —]"
        assert window.graph_view.nodes["3"].is_target
        assert all(edge.pen().widthF() == 2 for edge in window.graph_view.edges.values())
        window.preview_before_export.setChecked(False)
        window.export("final")
        wait_idle(window)
        assert len(list(window.output_dir.glob("*/resultado_final.png"))) == 1
    finally:
        window.close()


def test_failed_layout_save_restores_positions_and_history(window, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from graph_visualizer.ui import main_window

    warnings = []
    original = window.graph_view.positions()
    history_index = window.history_index
    layout = (window.data_dir / "layout.json").read_bytes()

    def failed_save(*args):
        raise OSError("Directorio de solo lectura")

    monkeypatch.setattr(main_window, "save_layout", failed_save)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[2]))
    window.graph_view.nodes["1"].setPos(200, 150)
    window._save_layout()
    assert "No se pudo guardar el cambio" in warnings[0]
    assert window.graph_view.positions() == original
    assert window.history_index == history_index
    assert (window.data_dir / "layout.json").read_bytes() == layout
    assert window.close()


def test_algorithm_results_share_the_canvas_and_release_it_on_reset(window, qapp):
    editing_width = window.graph_view.width()
    assert not window.results_panel.isVisible()
    assert not window.execution_card.isVisible()
    for algorithm in ("Bellman-Ford", "Floyd-Warshall", "Dijkstra"):
        window.algorithm_combo.setCurrentText(algorithm)
        window.initialize()
        qapp.processEvents()
        assert window.execution_card.isVisible()
        if algorithm == "Dijkstra":
            assert not window.results_panel.isVisible()
            assert window.graph_view.width() == editing_width
        else:
            assert window.results_panel.isVisible()
            assert window.graph_view.width() < editing_width
            assert window.results_panel.geometry().left() > window.graph_view.geometry().right()
            assert window.state_panel.isVisible() == (algorithm == "Bellman-Ford")
            assert window.matrix_panel.isVisible() == (algorithm == "Floyd-Warshall")
        window.reset()
        qapp.processEvents()
        assert not window.results_panel.isVisible()
        assert not window.execution_card.isVisible()
        assert window.graph_view.width() == editing_width


def test_swap_is_one_undoable_edit_and_respects_algorithm_locks(window):
    endpoints = window.start, window.target
    history = window.history_index
    window.swap_button.click()
    assert (window.start, window.target) == endpoints[::-1]
    assert window.history_index == history + 1
    window.undo()
    assert (window.start, window.target) == endpoints
    window.redo()
    assert (window.start, window.target) == endpoints[::-1]
    for algorithm in ("Dijkstra", "Bellman-Ford"):
        window.algorithm_combo.setCurrentText(algorithm)
        window.initialize()
        assert not window.swap_button.isEnabled()
        window.swap_endpoints()
        assert (window.start, window.target) == endpoints[::-1]
        window.reset()
    window.algorithm_combo.setCurrentText("Floyd-Warshall")
    window.initialize()
    states, index, history = window.states, window.state_index, window.history_index
    assert window.swap_button.isEnabled()
    window.swap_button.click()
    assert (window.start, window.target) == endpoints
    assert window.states is states and window.state_index == index
    assert window.history_index == history


def test_playback_can_repeat_after_the_final_step(window):
    window.initialize()
    window.show_state(len(window.states) - 1)
    states = window.states
    assert "Repetir" in window.play_button.text()
    window.play_button.click()
    assert window.state_index == 0
    assert window.states is states
    assert window.play_timer.isActive()
    window.play_button.click()
    assert not window.play_timer.isActive()
    assert "Reproducir" in window.play_button.text()


def test_typing_a_step_waits_for_enter(window):
    window.initialize()
    index = len(window.states) - 1
    window.jump_step.selectAll()
    QTest.keyClicks(window.jump_step, str(index))
    assert window.state_index == 0
    QTest.keyClick(window.jump_step, Qt.Key.Key_Return)
    assert window.state_index == index
