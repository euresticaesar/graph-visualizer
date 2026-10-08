import pytest
from conftest import wait_idle

from graph_visualizer.export import image_exporter
from graph_visualizer.ui.node_item import NodeItem


def data_contents(window):
    return {
        path.name: path.read_bytes()
        for path in window.data_dir.iterdir()
        if path.is_file() and path.name != "preferences.json"
    }


def assert_roles_only(view, start, target):
    for node, item in view.nodes.items():
        roles = (["INICIO"] if node == start else []) + (["DESTINO"] if node == target else [])
        assert item.caption.text() == " · ".join(roles)
        assert item.caption.isVisible() == bool(roles)
        assert item.label.isVisible()


def test_toggle_preserves_roles_distances_and_execution(window):
    before = data_contents(window)
    history = window.history_index
    positions = window.graph_view.positions()
    window.state_labels_checkbox.setChecked(False)
    assert_roles_only(window.graph_view, window.start, window.target)
    window.initialize()
    states = window.states
    for index in (0, 1, 4, len(states) - 1, 0):
        window.show_state(index)
        assert_roles_only(window.graph_view, window.start, window.target)
        labels = {node: item.label.text() for node, item in window.graph_view.nodes.items()}
        window.state_labels_checkbox.setChecked(True)
        assert all(item.caption.isVisible() for item in window.graph_view.nodes.values())
        assert any(
            "sin alcanzar" in item.caption.text() or "actual" in item.caption.text()
            for item in window.graph_view.nodes.values()
        )
        assert {node: item.label.text() for node, item in window.graph_view.nodes.items()} == labels
        window.state_labels_checkbox.setChecked(False)
    assert window.states is states
    window.reset()
    assert_roles_only(window.graph_view, window.start, window.target)
    assert window.history_index == history
    assert window.graph_view.positions() == positions
    assert data_contents(window) == before


def test_hidden_labels_survive_scene_rebuild_undo_and_shared_endpoint(window):
    window.state_labels_checkbox.setChecked(False)
    window.add_node("13")
    assert_roles_only(window.graph_view, window.start, window.target)
    window.undo()
    assert_roles_only(window.graph_view, window.start, window.target)
    window.redo()
    assert_roles_only(window.graph_view, window.start, window.target)
    window.target_combo.setCurrentIndex(window.target_combo.findData(window.start))
    window.initialize()
    window.show_state(len(window.states) - 1)
    assert window.graph_view.nodes[window.start].caption.text() == "INICIO · DESTINO"
    assert_roles_only(window.graph_view, window.start, window.target)


@pytest.mark.parametrize("kind", ["current", "all", "combined", "final"])
def test_exports_follow_checkbox_without_modifying_graph(window, monkeypatch, kind):
    before = data_contents(window)
    window.target_combo.setCurrentIndex(window.target_combo.findData("2"))
    window.state_labels_checkbox.setChecked(False)
    window.initialize()
    calls = []
    render = image_exporter.GraphView.apply_state

    def inspect_scene(view, *args, **kwargs):
        result = render(view, *args, **kwargs)
        scene = view.scene()
        nodes = [item for item in scene.items() if isinstance(item, NodeItem)]
        assert nodes
        for item in nodes:
            expected = (
                "INICIO"
                if item.node_id == window.start
                else ("DESTINO" if item.node_id == window.target else "")
            )
            assert item.caption.text() == expected
            assert item.caption.isVisible() == bool(expected)
            assert item.label.isVisible()
        calls.append(scene)
        return result

    monkeypatch.setattr(image_exporter.GraphView, "apply_state", inspect_scene)
    window.preview_before_export.setChecked(False)
    window.export(kind)
    wait_idle(window)
    assert len(calls) == (len(window.states) if kind in {"all", "combined"} else 1)
    assert window.last_export_path.exists()
    assert_roles_only(window.graph_view, window.start, window.target)
    assert data_contents(window) == before
