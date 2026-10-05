from pathlib import Path

import pytest
from PySide6.QtGui import QDesktopServices, QImage
from PySide6.QtWidgets import QMessageBox

from dijkstra_visualizer.export.composite_exporter import combine_phases
from dijkstra_visualizer.export.image_exporter import export_graph, save_image


def test_all_export_actions_preserve_live_view(window):
    assert all(not action.isEnabled() for action in window.export_actions)
    window.initialize()
    assert all(action.isEnabled() for action in window.export_actions)
    window.show_state(3)
    positions = window.graph_view.positions()
    labels = {node: item.label.text() for node, item in window.graph_view.nodes.items()}
    transform = window.graph_view.transform()
    saved_layout = (window.data_dir / "layout.json").read_bytes()
    for action in window.export_actions:
        action.trigger()
        assert "Export completed" in window.statusBar().currentMessage()
        assert window.state_index == 3
        assert window.graph_view.positions() == positions
        assert window.graph_view.transform() == transform
        assert {node: item.label.text() for node, item in window.graph_view.nodes.items()} == labels
    assert (window.data_dir / "layout.json").read_bytes() == saved_layout
    runs = list(window.output_dir.iterdir())
    assert len(runs) == 4
    images = list(window.output_dir.rglob("*.png"))
    assert len(images) == len(window.states) + 3
    assert len(list(window.output_dir.glob("*/steps/step_*.png"))) == len(window.states)
    for path in images:
        image = QImage(str(path))
        assert not image.isNull(), path
        if path.name == "all_steps.png":
            assert image.width() == 3680
            assert image.height() == 4420
        else:
            assert (image.width(), image.height()) == (1600, 1100)
    window.reset()
    assert all(not action.isEnabled() for action in window.export_actions)


def test_export_dimensions_independent_of_window_size(window):
    window.initialize()
    paths = []
    for width, height in [(900, 620), (1440, 900)]:
        window.resize(width, height)
        paths.append(
            export_graph(
                window.graph,
                window.graph_view.positions(),
                window.states,
                window.start,
                window.target,
                0,
                "current",
                window.output_dir,
            )
        )
    assert paths[0] != paths[1]
    assert QImage(str(paths[0])) == QImage(str(paths[1]))


def test_export_failure_is_reported(window, monkeypatch):
    window.initialize()
    window.output_dir.write_text("A file blocks this output directory")
    messages = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *args: messages.append(args[2]))
    window.export("current")
    assert messages
    assert window.statusBar().currentMessage() == "Export failed"
    assert window.state_index == 0


def test_open_output_folder_uses_local_url(window, monkeypatch):
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url) or True)
    window.open_output_folder()
    assert window.output_dir.is_dir()
    assert len(opened) == 1
    assert Path(opened[0].toLocalFile()) == window.output_dir


def test_png_write_failure(tmp_path, qapp):
    image = QImage(10, 10, QImage.Format.Format_RGB32)
    with pytest.raises(OSError, match="Could not write"):
        save_image(image, tmp_path / "missing" / "image.png")


def test_combined_single_phase_and_invalid_count(qapp):
    image = QImage(100, 60, QImage.Format.Format_RGB32)
    image.fill(0)
    combined = combine_phases([image], 1)
    assert (combined.width(), combined.height()) == (140, 100)
    with pytest.raises(ValueError):
        combine_phases([], 0)
    with pytest.raises(ValueError):
        combine_phases([image], 2)
