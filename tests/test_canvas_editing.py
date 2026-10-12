import networkx as nx
import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QInputDialog, QMessageBox

from graph_visualizer.io.graph_io import load_graph
from graph_visualizer.ui import main_window


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


@pytest.mark.parametrize("weight", [-1, 1.25])
def test_rim_drag_adds_parallel_edge_without_moving_nodes(window, monkeypatch, weight):
    answers(monkeypatch, [("inf", True), ("nan", True), (str(weight), True)])
    view = window.graph_view
    positions = view.positions()
    drag_connection(view)
    assert view.positions() == positions
    assert window.graph["1"]["2"][1]["weight"] == weight
    assert window.run_button.isEnabled() == (weight >= 0)
    assert view.connection_preview is None
    window.undo()
    assert window.graph.number_of_edges("1", "2") == 1
    window.redo()
    assert window.graph.number_of_edges("1", "2") == 2
    assert window.graph["1"]["2"][1]["weight"] == weight


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


@pytest.mark.parametrize("directed", [False, True])
@pytest.mark.parametrize("label", [False, True])
@pytest.mark.parametrize("key", [0, 1])
def test_right_click_deletes_exact_connection_and_undo_redo(window, directed, label, key):
    if directed:
        window.change_graph_type(True)
    source, target = ("2", "1") if directed else ("1", "2")
    window.set_edge(source, target, 8)
    view = window.graph_view
    original = window.graph.copy()
    positions = view.positions()
    history_index = window.history_index
    edge = view.edges[source, target, key]
    location = (
        edge.label.mapToScene(edge.label.boundingRect().center())
        if label
        else edge.path().pointAtPercent(0.65)
    )
    assert view._graph_item_at(view.mapFromScene(location)) is edge
    QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=view.mapFromScene(location))
    deleted = original.copy()
    deleted.remove_edge(source, target, key)
    assert window.history_index == history_index + 1
    assert (source, target, key) not in view.edges
    assert nx.utils.graphs_equal(window.graph, deleted)
    assert nx.utils.graphs_equal(
        load_graph(window.data_dir / "nodes.csv", window.data_dir / "edges.csv"), deleted
    )
    window.undo_button.click()
    assert window.history_index == history_index
    assert (source, target, key) in view.edges
    assert nx.utils.graphs_equal(window.graph, original)
    assert nx.utils.graphs_equal(
        load_graph(window.data_dir / "nodes.csv", window.data_dir / "edges.csv"), original
    )
    window.redo_button.click()
    assert window.history_index == history_index + 1
    assert (source, target, key) not in view.edges
    assert nx.utils.graphs_equal(window.graph, deleted)
    assert nx.utils.graphs_equal(
        load_graph(window.data_dir / "nodes.csv", window.data_dir / "edges.csv"), deleted
    )
    assert view.positions() == positions


def test_repeated_right_click_deletions_support_history_shortcuts(window, qapp):
    view = window.graph_view
    original = window.graph.copy()
    for source, target in (("1", "2"), ("1", "5")):
        edge = view.edges[source, target, 0]
        location = edge.label.mapToScene(edge.label.boundingRect().center())
        QTest.mouseClick(
            view.viewport(), Qt.MouseButton.RightButton, pos=view.mapFromScene(location)
        )
    assert window.history_index == 2
    assert not window.graph.has_edge("1", "2")
    assert not window.graph.has_edge("1", "5")
    window.activateWindow()
    view.setFocus()
    qapp.processEvents()
    QTest.keyClick(view, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert not window.graph.has_edge("1", "2")
    assert window.graph.has_edge("1", "5")
    QTest.keyClick(view, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier)
    assert nx.utils.graphs_equal(window.graph, original)
    QTest.keyClick(
        view, Qt.Key.Key_Z, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier
    )
    assert not window.graph.has_edge("1", "2")
    assert window.graph.has_edge("1", "5")
    QTest.keyClick(view, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
    assert not window.graph.has_edge("1", "2")
    assert not window.graph.has_edge("1", "5")


def test_right_click_on_background_or_node_does_not_edit(window):
    view = window.graph_view
    original = window.graph.copy()
    before = {p: p.read_bytes() for p in window.data_dir.iterdir()}
    for location in (QPoint(30, 30), view.mapFromScene(view.nodes["1"].pos())):
        QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=location)
    assert nx.utils.graphs_equal(window.graph, original)
    assert window.history_index == 0
    assert {p: p.read_bytes() for p in window.data_dir.iterdir()} == before


def test_failed_right_click_deletion_preserves_graph_and_history(window, monkeypatch):
    def failed_save(*args):
        raise OSError("Directorio de solo lectura")

    warnings = []
    monkeypatch.setattr(main_window, "save_graph_data", failed_save)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: warnings.append(args[2]))
    original = window.graph.copy()
    before = {p: p.read_bytes() for p in window.data_dir.iterdir()}
    view = window.graph_view
    edge = view.edges["1", "2", 0]
    location = edge.label.mapToScene(edge.label.boundingRect().center())
    QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=view.mapFromScene(location))
    assert "No se pudo guardar el cambio" in warnings[0]
    assert nx.utils.graphs_equal(window.graph, original)
    assert ("1", "2", 0) in view.edges
    assert window.history_index == 0
    assert {p: p.read_bytes() for p in window.data_dir.iterdir()} == before


@pytest.mark.parametrize("gesture", ["connection", "edge"])
def test_right_click_deletion_cancels_pending_gesture(window, monkeypatch, gesture):
    def unexpected_dialog(*args, **kwargs):
        pytest.fail("Eliminar una conexión no debe abrir un diálogo")

    monkeypatch.setattr(QInputDialog, "getText", unexpected_dialog)
    view = window.graph_view
    edge = view.edges["1", "2", 0]
    location = view.mapFromScene(edge.label.mapToScene(edge.label.boundingRect().center()))
    start = (
        view.mapFromScene(view.nodes["1"].pos() + QPointF(25, 0))
        if gesture == "connection"
        else location
    )
    QTest.mousePress(view.viewport(), Qt.MouseButton.LeftButton, pos=start)
    assert view.connection_source is not None or view.pressed_edge is not None
    QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=location)
    QTest.mouseRelease(view.viewport(), Qt.MouseButton.LeftButton, pos=location)
    assert not window.graph.has_edge("1", "2")
    assert window.history_index == 1
    assert view.connection_source is None
    assert view.connection_preview is None
    assert view.pressed_edge is None


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
    original = window.graph.copy()
    history_index = window.history_index
    QTest.mouseDClick(view.viewport(), Qt.MouseButton.LeftButton, pos=QPoint(30, 30))
    edge = view.edges["1", "2", 0]
    QTest.mouseClick(
        view.viewport(),
        Qt.MouseButton.LeftButton,
        pos=view.mapFromScene(edge.path().pointAtPercent(0.5)),
    )
    QTest.mouseClick(
        view.viewport(),
        Qt.MouseButton.RightButton,
        pos=view.mapFromScene(edge.path().pointAtPercent(0.5)),
    )
    drag_connection(view)
    assert view.positions() == positions
    assert window.graph.number_of_edges("1", "2") == 1
    assert nx.utils.graphs_equal(window.graph, original)
    assert window.history_index == history_index


def test_connection_from_node_zero(window, monkeypatch):
    window.rename_node("1", "0")
    answers(monkeypatch, [("2", True)])
    drag_connection(window.graph_view, source="0")
    assert window.graph["0"]["2"][1]["weight"] == 2
