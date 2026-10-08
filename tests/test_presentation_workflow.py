import json
from copy import deepcopy

import networkx as nx
import pytest
from PySide6.QtCore import QPointF, Qt

from graph_visualizer.core.graph import graphs_equal
from graph_visualizer.export.slide_renderer import SlideOptions, SlideRenderer
from graph_visualizer.io.edge_labels import apply_edge_labels, edge_label_records
from graph_visualizer.io.graph_io import load_graph, save_graph_data
from graph_visualizer.io.preferences import DEFAULTS
from graph_visualizer.io.presentation_profiles import (
    parse_profile,
    profile_document,
    read_profile,
    write_profile,
)
from graph_visualizer.io.presets import Preset, read_preset, write_preset
from graph_visualizer.ui.graph_data_dialog import GraphDataDialog
from graph_visualizer.ui.presentation_profiles import PresentationProfilesDialog


def test_profile_roundtrip_keeps_graph_and_selected_event(window, tmp_path):
    original = window.current_preset().document()
    window.initialize()
    window.show_state(2)
    event = window.states[window.state_index].step
    document = profile_document(
        "Clase",
        DEFAULTS
        | {
            "theme": "colorblind",
            "ui_layout": "bottom",
            "export_resolution": 3840,
        },
    )
    path = tmp_path / "perfil.json"
    write_profile(path, document)
    assert read_profile(path) == document
    assert "window_size" not in document["preferences"]
    window.apply_presentation_profile(read_profile(path))
    assert window.current_preset().document() == original
    assert window.states[window.state_index].step == event
    assert window.export_resolution.currentData() == 3840
    assert window.visual_splitter.orientation() == Qt.Orientation.Vertical


@pytest.mark.parametrize(
    "key,value",
    [
        ("theme", "missing"),
        ("export_resolution", True),
        ("ui_font_size", 100),
        ("export_legend", 0),
        ("accent", "red"),
        ("export_font_scale", float("nan")),
        ("nodes", []),
        ("window_size", [1024, 768]),
    ],
)
def test_invalid_profile_does_not_modify_preferences(window, key, value):
    document = profile_document("Perfil", DEFAULTS)
    document["preferences"][key] = value
    before = deepcopy(window.preferences)
    with pytest.raises(ValueError):
        window.apply_presentation_profile(document)
    assert window.preferences == before


def test_profile_library_save_rename_share(window, tmp_path, monkeypatch):
    dialog = PresentationProfilesDialog(window)
    dialog.name.setText("Clase original")
    dialog.save_profile()
    path = dialog.profiles.currentData()
    dialog.name.setText("Clase renombrada")
    dialog.rename_profile()
    assert read_profile(path)["name"] == "Clase renombrada"
    exported = tmp_path / "compartido.json"
    monkeypatch.setattr(
        "graph_visualizer.ui.presentation_profiles.QFileDialog.getSaveFileName",
        lambda *_: (str(exported), ""),
    )
    monkeypatch.setattr(
        "graph_visualizer.ui.presentation_profiles.QFileDialog.getOpenFileName",
        lambda *_: (str(exported), ""),
    )
    dialog.export_profile()
    dialog.import_profile()
    assert dialog.profiles.count() == 2
    assert read_profile(dialog.profiles.currentData()) == read_profile(exported)
    dialog.close()


def test_label_offsets_persist_undo_and_export(window):
    dialog = GraphDataDialog(window)
    u, v, key, _ = dialog.edge_rows[0]
    dialog.connections.item(0, 4).setText("75")
    dialog.connections.item(0, 5).setText("-35")
    dialog.apply()
    assert window.graph[u][v][key]["label_offset"] == (75, -35)
    loaded = load_graph(window.data_dir / "nodes.csv", window.data_dir / "edges.csv")
    assert graphs_equal(window.graph, loaded)
    assert edge_label_records(loaded)[0]["offset"] == [75, -35]
    renderer = SlideRenderer(window.graph, window.graph_view.positions(), SlideOptions())
    try:
        edge = next(
            item
            for item in renderer.view.edges.values()
            if item.source.node_id == u and item.target.node_id == v and item.key == key
        )
        assert edge.label_offset == QPointF(75, -35)
        expected = (
            edge.path().pointAtPercent(0.5) - edge.label.boundingRect().center() + QPointF(75, -35)
        )
        assert edge.label.pos() == expected
    finally:
        renderer.close()
    window.undo()
    assert "label_offset" not in window.graph[u][v][key]
    window.redo()
    assert window.graph[u][v][key]["label_offset"] == (75, -35)
    dialog.close()


def test_label_positions_distinguish_parallel_and_reverse_edges(tmp_path):
    graph = nx.MultiDiGraph()
    graph.add_edge("A", "B", key=0, weight=1, label_offset=(40, -20))
    graph.add_edge("A", "B", key=1, weight=3, label_offset=(-40, 20))
    graph.add_edge("B", "A", key=0, weight=2, label_offset=(5, 10))
    positions = {"A": (0, 0), "B": (300, 100)}
    path = tmp_path / "preset.json"
    write_preset(path, Preset("Etiquetas", graph, positions))
    assert graphs_equal(read_preset(path).graph, graph)
    save_graph_data(tmp_path, graph, positions)
    assert graphs_equal(load_graph(tmp_path / "nodes.csv", tmp_path / "edges.csv"), graph)
    broken = deepcopy(edge_label_records(graph))
    broken[-1]["offset"] = [float("inf"), 0]
    before = graph.copy()
    with pytest.raises(ValueError):
        apply_edge_labels(graph, broken)
    assert graphs_equal(graph, before)


def test_old_profile_and_preset_remain_compatible(tmp_path):
    profile = {
        "version": 1,
        "kind": "graph-visualizer-presentation",
        "name": "Viejo",
        "preferences": {"theme": "dark"},
    }
    assert parse_profile(profile)["preferences"]["export_resolution"] == 1920
    path = tmp_path / "preset.json"
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "name": "Sin etiquetas",
                "directed": False,
                "nodes": ["A", "B"],
                "edges": [{"source": "A", "target": "B", "id": 0, "weight": 1}],
                "positions": {"A": [0, 0], "B": [100, 100]},
            }
        )
    )
    assert edge_label_records(read_preset(path).graph) == []
