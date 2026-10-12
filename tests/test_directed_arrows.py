import networkx as nx
import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from graph_visualizer.io.graph_io import load_graph, save_graph_data
from graph_visualizer.ui.graph_view import GraphView
from graph_visualizer.ui.main_window import MainWindow


def assert_visible_arrows(view):
    for edge in view.edges.values():
        assert edge.directed
        with_arrow = view.viewport().grab().toImage()
        try:
            edge.directed = False
            edge.update()
            without_arrow = view.viewport().grab().toImage()
        finally:
            edge.directed = True
            edge.update()
        different_pixels = sum(
            left != right
            for left, right in zip(
                with_arrow.constBits().cast("I"), without_arrow.constBits().cast("I"), strict=True
            )
        )
        scale = view.transform().m11() * with_arrow.devicePixelRatio()
        assert different_pixels >= 70 * scale**2, (
            f"La flecha quedó oculta detrás de las etiquetas: {different_pixels} píxeles visibles"
        )


@pytest.mark.parametrize("target_position", [(220, 0), (0, 220), (0, -220), (120, 220)])
@pytest.mark.parametrize("removed", [("A", "B"), ("B", "A")])
def test_surviving_directed_arrow_stays_visible_after_delete_undo_redo(
    qapp, tmp_path, target_position, removed
):
    graph = nx.MultiDiGraph()
    graph.add_edge("A", "B", weight=4)
    graph.add_edge("B", "A", weight=2)
    data_dir = tmp_path / "data"
    save_graph_data(data_dir, graph, {"A": (0, 0), "B": target_position})
    window = MainWindow(data_dir, tmp_path / "output")
    try:
        window.show()
        qapp.processEvents()
        view = window.graph_view
        edge = view.edges[*removed, 0]
        click_position = view.mapFromScene(
            edge.label.mapToScene(edge.label.boundingRect().center())
        )
        QTest.mouseClick(view.viewport(), Qt.MouseButton.RightButton, pos=click_position)
        assert window.graph.is_directed()
        assert not window.graph.has_edge(*removed)
        assert window.graph.has_edge(*reversed(removed), 0)
        assert load_graph(data_dir / "nodes.csv", data_dir / "edges.csv").is_directed()
        assert_visible_arrows(view)
        window.undo()
        assert window.graph.number_of_edges() == 2
        assert_visible_arrows(view)
        window.redo()
        assert window.graph.number_of_edges() == 1
        assert_visible_arrows(view)
    finally:
        window.close()
        window.deleteLater()
        qapp.processEvents()


@pytest.mark.parametrize("font_scale", [0.8, 1.0, 1.5])
@pytest.mark.parametrize("state_labels", [False, True])
def test_vertical_arrow_remains_visible_with_scaled_node_labels(qapp, font_scale, state_labels):
    graph = nx.MultiDiGraph()
    graph.add_edge("B", "A", weight=2)
    view = GraphView(graph, {"A": (0, 0), "B": (0, 260)}, font_scale=font_scale)
    try:
        view.resize(640, 640)
        view.set_state_labels_visible(state_labels)
        view.apply_state(None, "A", "B")
        view.show()
        view.fit_graph()
        qapp.processEvents()
        assert_visible_arrows(view)
    finally:
        view.close()
        view.deleteLater()
        qapp.processEvents()
