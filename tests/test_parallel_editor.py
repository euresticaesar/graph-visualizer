import networkx as nx
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from graph_visualizer.io.graph_io import load_graph
from graph_visualizer.ui.node_item import PATH


def test_parallel_edges_edit_delete_undo_and_reload(window):
    editor = window.editor
    window.tabs.setCurrentIndex(1)
    editor.select_edge("1", "2", 0)
    editor.weight_input.setText("1.5")
    QTest.mouseClick(editor.add_edge_button, Qt.MouseButton.LeftButton)
    assert window.graph.number_of_edges("1", "2") == 2
    assert editor.edge_combo.currentData() == 1
    editor.weight_input.setText("0.5")
    QTest.keyClick(editor.weight_input, Qt.Key.Key_Return)
    assert window.graph["1"]["2"][1]["weight"] == 0.5
    assert window.graph["1"]["2"][0]["weight"] == 4
    editor.select_edge("1", "2", 0)
    editor.delete_edge_button.click()
    assert list(window.graph["1"]["2"]) == [1]
    reloaded = load_graph(window.data_dir / "nodes.csv", window.data_dir / "edges.csv")
    assert nx.utils.graphs_equal(reloaded, window.graph)
    window.undo()
    assert set(window.graph["1"]["2"]) == {0, 1}
    window.redo()
    assert list(window.graph["1"]["2"]) == [1]


def test_parallel_curves_and_exact_final_path(window):
    window.set_edge("1", "2", 0.5)
    view = window.graph_view
    first, second = view.edges["1", "2", 0], view.edges["1", "2", 1]
    assert first.path().pointAtPercent(0.5) != second.path().pointAtPercent(0.5)
    view.nodes["1"].setPos(50, 80)
    for edge in (first, second):
        assert edge.path().pointAtPercent(0) == view.nodes["1"].pos()
        assert edge.label.pos() + edge.label.boundingRect().center() == edge.path().pointAtPercent(
            0.5
        )
    window.target_combo.setCurrentIndex(window.target_combo.findData("2"))
    window.initialize()
    window.show_state(len(window.states) - 1)
    assert view.edges["1", "2", 1].pen().color().name() == PATH
    assert view.edges["1", "2", 0].pen().color().name() != PATH
