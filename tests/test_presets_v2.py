import json
from pathlib import Path

import networkx as nx
import pytest

from graph_visualizer.io.presets import Preset, parse_preset, read_preset, write_preset


def test_examples_roundtrip(tmp_path):
    for path in Path("src/graph_visualizer/examples").glob("*.json"):
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
    preset = read_preset(Path("src/graph_visualizer/examples/bellman_ford.json"))
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


def test_dirty_dialog_cancel_skip_and_save(window, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QInputDialog, QMessageBox

    destination = Path("src/graph_visualizer/examples/bellman_ford.json")
    window.add_node("nuevo")

    def choose(text):
        def execute(dialog):
            next(b for b in dialog.buttons() if b.text() == text).click()
            return 0

        monkeypatch.setattr(QMessageBox, "exec", execute)

    choose("Cancelar")
    assert not window.load_preset_path(destination)
    assert "nuevo" in window.graph
    choose("Guardar y continuar")
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("Mi copia", True))
    assert window.load_preset_path(destination)
    personal = list(window.personal_presets.glob("*.json"))
    assert len(personal) == 1 and "nuevo" in read_preset(personal[0]).graph
    window.undo()
    assert "nuevo" in window.graph
    window.add_node("otro")
    choose("Continuar sin guardar en preset")
    assert window.load_preset_path(destination)
    assert "otro" not in read_preset(personal[0]).graph
    window.undo()
    assert "otro" in window.graph


def test_failed_working_save_during_load_keeps_previous_graph(window, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    from graph_visualizer.ui import main_window

    previous = window.graph.copy()
    positions = window.graph_view.positions()
    history = window.history_index

    def fail(*args):
        raise OSError("Sin espacio")

    monkeypatch.setattr(main_window, "save_graph_data", fail)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: None)
    assert not window.load_preset_path(Path("src/graph_visualizer/examples/bellman_ford.json"))
    assert nx.utils.graphs_equal(window.graph, previous)
    assert window.graph_view.positions() == positions
    assert window.history_index == history
    assert window.preset_path is None


@pytest.mark.parametrize(
    "change",
    [
        {"version": True},
        {"nodes": "ABC"},
        {"settings": {"start": []}},
        {"settings": {"detail": "yes"}},
        {"settings": {"algorithm": "Other"}},
    ],
)
def test_malformed_import_settings_are_rejected(change):
    data = read_preset(Path("src/graph_visualizer/examples/bellman_ford.json")).document()
    with pytest.raises(ValueError):
        parse_preset(data | change)
