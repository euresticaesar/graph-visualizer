import json
from pathlib import Path

import networkx as nx
import pytest

from dijkstra_visualizer.io.presets import Preset, parse_preset, read_preset, write_preset


def test_examples_roundtrip(tmp_path):
    for path in Path("src/dijkstra_visualizer/examples").glob("*.json"):
        preset = read_preset(path)
        write_preset(tmp_path / path.name, preset)
        loaded = read_preset(tmp_path / path.name)
        assert loaded.document() == preset.document()


def test_validation_and_failed_write_preserves_file(tmp_path):
    graph = nx.MultiGraph()
    graph.add_node("A")
    preset = Preset("Prueba", graph, {"A": (0, 0)})
    path = tmp_path / "p.json"
    write_preset(path, preset)
    before = path.read_bytes()
    for change in [{"version": 2}, {"nodes": ["A", " A "]}, {"positions": {}}]:
        with pytest.raises(ValueError):
            parse_preset(preset.document() | change)
    preset.positions["A"] = (float("nan"), 0)
    with pytest.raises(ValueError):
        write_preset(path, preset)
    assert path.read_bytes() == before
    assert json.loads(before)["name"] == "Prueba"


def test_load_is_undoable_and_invalid_load_preserves_work(window, tmp_path):
    before = window.graph.copy()
    preset = read_preset(Path("src/dijkstra_visualizer/examples/bellman_ford.json"))
    path = tmp_path / "valid.json"
    write_preset(path, preset)
    assert window.load_preset_path(path)
    assert nx.utils.graphs_equal(window.graph, preset.graph)
    window.undo()
    assert nx.utils.graphs_equal(window.graph, before)
    path.write_text("{}")
    with pytest.raises(ValueError):
        window.load_preset_path(path)
    assert nx.utils.graphs_equal(window.graph, before)
