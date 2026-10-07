import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QInputDialog, QMessageBox


def answers(monkeypatch, values):
    responses = iter(values)
    monkeypatch.setattr(QInputDialog, "getText", lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: None)


def drag_connection(view, source="1", target="2"):
    start = view.mapFromScene(view.nodes[source].pos() + QPointF(25, 0))
    finish = view.mapFromScene(view.nodes[target].pos() + QPointF(-25, 0))
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(view.viewport(), finish, delay=10)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=finish)


def test_double_click_creates_node_at_position_and_undo(window, monkeypatch):
    answers(monkeypatch, [(" ", True), ("1", True), ("0", True)])
    view = window.graph_view
    click = QPoint(30, 30)
    expected = view.mapToScene(click)
    assert view.itemAt(click) is None
    QTest.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton, pos=click)
    assert view.nodes["0"].pos() == expected
    window.undo()
    assert "0" not in window.graph
    window.redo()
    assert view.nodes["0"].pos() == expected


def test_double_click_cancel_does_not_write(window, monkeypatch):
    answers(monkeypatch, [("13", False)])
    before = {p: p.read_bytes() for p in window.data_dir.iterdir()}
    QTest.mouseDClick(window.graph_view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(30, 30))
    assert len(window.graph) == 12
    assert {p: p.read_bytes() for p in window.data_dir.iterdir()} == before


def test_rim_drag_adds_parallel_edge_without_moving_nodes(window, monkeypatch):
    answers(monkeypatch, [("-1", True), ("nan", True), ("1.25", True)])
    view = window.graph_view
    positions = view.positions()
    drag_connection(view)
    assert view.positions() == positions
    assert window.graph["1"]["2"][1]["weight"] == 1.25
    assert view.connection_preview is None
    window.undo()
    assert window.graph.number_of_edges("1", "2") == 1
    window.redo()
    assert window.graph.number_of_edges("1", "2") == 2


@pytest.mark.parametrize("label", [True, False])
def test_click_edits_only_selected_parallel_edge(window, monkeypatch, label):
    window.set_edge("1", "2", 8)
    view = window.graph_view
    edge = view.edges["1", "2", 1]
    location = (
        edge.label.mapToScene(edge.label.boundingRect().center())
        if label
        else edge.path().pointAtPercent(0.35)
    )
    answers(monkeypatch, [("2.75", True)])
    QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=view.mapFromScene(location))
    assert window.graph["1"]["2"][1]["weight"] == 2.75
    assert window.graph["1"]["2"][0]["weight"] == 4
    window.undo()
    assert window.graph["1"]["2"][1]["weight"] == 8


def test_cancel_connection_and_weight_leave_history_unchanged(window, monkeypatch):
    answers(monkeypatch, [("1", False), ("4", False)])
    drag_connection(window.graph_view)
    edge = window.graph_view.edges["1", "2", 0]
    QTest.mouseClick(
        window.graph_view.viewport(),
        Qt.MouseButton.LeftButton,
        pos=window.graph_view.mapFromScene(edge.path().pointAtPercent(0.5)),
    )
    assert window.history_index == 0
    assert window.graph["1"]["2"][0]["weight"] == 4


def test_escape_and_invalid_drop_cancel_connection(window):
    view = window.graph_view
    start = view.mapFromScene(view.nodes["1"].pos() + QPointF(25, 0))
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseMove(view.viewport(), QPoint(30, 30))
    assert view.connection_preview is not None
    QTest.keyClick(view, Qt.Key.Key_Escape)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(30, 30))
    assert view.connection_preview is None
    assert window.history_index == 0
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    assert view.connection_preview is None
    assert window.history_index == 0


def test_algorithm_mode_blocks_canvas_editing(window, monkeypatch):
    def unexpected_dialog(*args, **kwargs):
        pytest.fail("No debe abrir un editor durante el recorrido")

    monkeypatch.setattr(QInputDialog, "getText", unexpected_dialog)
    window.initialize()
    view = window.graph_view
    positions = view.positions()
    QTest.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(30, 30))
    edge = view.edges["1", "2", 0]
    QTest.mouseClick(
        view.viewport(),
        Qt.MouseButton.LeftButton,
        pos=view.mapFromScene(edge.path().pointAtPercent(0.5)),
    )
    drag_connection(view)
    assert view.positions() == positions
    assert window.graph.number_of_edges("1", "2") == 1


def test_connection_from_node_zero(window, monkeypatch):
    window.rename_node("1", "0")
    answers(monkeypatch, [("2", True)])
    drag_connection(window.graph_view, source="0")
    assert window.graph["0"]["2"][1]["weight"] == 2
