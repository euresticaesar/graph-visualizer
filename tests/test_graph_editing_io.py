import networkx as nx
import pytest

from graph_visualizer.io import files
from graph_visualizer.io.graph_io import load_graph, save_graph_data
from graph_visualizer.io.layout_io import load_layout


def test_save_topology_and_layout_round_trip(tmp_path):
    graph = nx.MultiGraph()
    graph.add_nodes_from(["1", "2", "3"])
    graph.add_edge("2", "1", weight=0.125)
    positions = {"1": (10, 20), "2": (30, 40), "3": (-10, 5)}
    save_graph_data(tmp_path, graph, positions)
    reloaded = load_graph(tmp_path / "nodes.csv", tmp_path / "edges.csv")
    assert nx.utils.graphs_equal(reloaded, graph)
    assert load_layout(tmp_path / "layout.json", reloaded) == positions
    assert (tmp_path / "edges.csv").read_text() == "source,target,weight,id\n1,2,0.125,0\n"


def test_partial_save_failure_restores_all_original_files(tmp_path, monkeypatch):
    contents = {tmp_path / name: f"original {name}" for name in ("nodes", "edges", "layout")}
    files.atomic_write_files(contents)
    original_replace = files.os.replace
    calls = 0

    def fail_second_replace(source, target):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("Disk error")
        return original_replace(source, target)

    monkeypatch.setattr(files.os, "replace", fail_second_replace)
    with pytest.raises(OSError, match="Disk error"):
        files.atomic_write_files(dict.fromkeys(contents, "changed"))
    assert {path: path.read_text() for path in contents} == contents
    assert set(tmp_path.iterdir()) == set(contents)


def test_invalid_edit_does_not_touch_files(tmp_path):
    graph = nx.Graph()
    graph.add_edge("1", "2", weight=1)
    positions = {"1": (0, 0), "2": (100, 0)}
    save_graph_data(tmp_path, graph, positions)
    before = {path: path.read_bytes() for path in tmp_path.iterdir()}
    graph["1"]["2"]["weight"] = -1
    with pytest.raises(ValueError):
        save_graph_data(tmp_path, graph, positions)
    assert {path: path.read_bytes() for path in tmp_path.iterdir()} == before


def test_backup_is_preserved_if_rollback_also_fails(tmp_path, monkeypatch):
    first, second = tmp_path / "nodes", tmp_path / "edges"
    files.atomic_write_files({first: "original nodes", second: "original edges"})
    original_replace = files.os.replace
    calls = 0

    def fail_after_first_replace(source, target):
        nonlocal calls
        calls += 1
        if calls >= 2:
            raise OSError("Disk failure")
        return original_replace(source, target)

    monkeypatch.setattr(files.os, "replace", fail_after_first_replace)
    with pytest.raises(OSError, match="Copia anterior") as error:
        files.atomic_write_files({first: "new nodes", second: "new edges"})
    recovery = set(tmp_path.iterdir()) - {first, second}
    assert len(recovery) == 1
    backup = recovery.pop()
    assert backup.read_text() == "original nodes"
    assert str(backup) in str(error.value)
    assert second.read_text() == "original edges"


def test_new_files_are_removed_if_partial_save_fails(tmp_path, monkeypatch):
    original_replace = files.os.replace
    calls = 0

    def fail_second_replace(source, target):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("Disk error")
        return original_replace(source, target)

    monkeypatch.setattr(files.os, "replace", fail_second_replace)
    with pytest.raises(OSError):
        files.atomic_write_files({tmp_path / "nodes": "nodes", tmp_path / "edges": "edges"})
    assert list(tmp_path.iterdir()) == []
