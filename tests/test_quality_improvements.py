import json
import os
import subprocess
import sys
import time
from pathlib import Path
from xml.etree import ElementTree

import networkx as nx
import pytest
from conftest import wait_idle
from PySide6 import QtCore
from PySide6.QtCore import QItemSelectionModel, QRectF, Qt
from PySide6.QtPdf import QPdfDocument
from PySide6.QtTest import QTest

from graph_visualizer.core.astar import astar_steps
from graph_visualizer.core.bellman_ford import bellman_ford_steps
from graph_visualizer.core.dijkstra import dijkstra_steps
from graph_visualizer.core.floyd_warshall import floyd_warshall_steps
from graph_visualizer.core.models import AlgorithmCancelled, format_number
from graph_visualizer.export import image_exporter
from graph_visualizer.export.slide_renderer import (
    SlideOptions,
    SlideRenderer,
    content_top,
    footer_height,
    page_count,
)
from graph_visualizer.io.preferences import DEFAULTS, load_preferences, save_preferences
from graph_visualizer.io.presets import read_preset, write_preset
from graph_visualizer.ui.export_controls import ExportPreview
from graph_visualizer.ui.graph_data_dialog import GraphDataDialog
from graph_visualizer.ui.graph_view import GraphView
from graph_visualizer.ui.themes import PALETTES, foreground, luminance

EXAMPLES = Path("src/graph_visualizer/examples")


def export_args(window, kind="current"):
    return (
        window.graph,
        window.graph_view.positions(),
        window.states,
        window.start,
        window.target,
        window.state_index,
        kind,
        window.output_dir,
    )


@pytest.mark.parametrize("value", [1e-7, -1e-7, 1e-15, -1e-15, 0.0000012345, -0.0000012345])
def test_small_weights_keep_sign_and_value(value):
    assert float(format_number(value)) == pytest.approx(value, rel=1e-10, abs=0)
    assert format_number(value) != "0"


def test_export_current_keeps_exact_event_even_when_summary_selected(window):
    window.initialize()
    index = next(i for i, state in enumerate(window.states) if not state.summary)
    window.show_state(index)
    event = window.states[index].step
    window.export_detail.setCurrentIndex(1)
    window.preview_before_export.setChecked(False)
    window.export("current")
    wait_idle(window)
    manifest = json.loads((window.last_export_path.parent / "manifest.json").read_text())
    assert manifest["outputs"][0]["states"][0]["event"] == event
    assert manifest["events"][0]["explanation"] == window.states[index].explanation
    assert window.state_index == index


def test_floyd_negative_states_follow_queried_origin(qapp):
    graph = nx.MultiDiGraph()
    graph.add_nodes_from("ABCD")
    graph.add_weighted_edges_from([("A", "B", 1), ("B", "C", -2), ("C", "B", 1)])
    state = floyd_warshall_steps(graph)[-1]
    view = GraphView(graph, {n: (i * 200, 0) for i, n in enumerate(graph)})
    view.apply_state(state, "A", "C", True)
    assert view.nodes["B"].is_affected
    assert view.nodes["B"].label.text() == "−∞"
    assert "sin mínimo finito" in view.nodes["B"].caption.text()
    assert not view.nodes["D"].is_affected
    assert view.nodes["D"].label.text() == "∞"
    view.apply_state(state, "D", "C", True)
    assert not any(item.is_affected for item in view.nodes.values())
    assert view.nodes["B"].label.text() == "∞"
    view.close()


@pytest.mark.parametrize(
    "algorithm", [dijkstra_steps, astar_steps, bellman_ford_steps, floyd_warshall_steps]
)
def test_algorithms_stop_cooperatively(algorithm):
    graph = nx.MultiDiGraph()
    graph.add_edge("A", "B", weight=1)
    args = (
        (graph,)
        if algorithm is floyd_warshall_steps
        else (graph, "A")
        if algorithm is bellman_ford_steps
        else (graph, "A", "B")
    )
    with pytest.raises(AlgorithmCancelled):
        algorithm(*args, _cancelled=lambda: True)


def test_busy_shortcuts_and_cancel_cannot_change_graph(window, monkeypatch):
    from graph_visualizer.ui import worker

    def slow_algorithm(graph, *, detailed, _cancelled):
        while not _cancelled():
            time.sleep(0.005)
        raise AlgorithmCancelled

    monkeypatch.setattr(worker, "floyd_warshall_steps", slow_algorithm)
    window.load_preset_path(EXAMPLES / "repositorio_30.json")
    window.add_node("extra")
    window.undo()
    window.algorithm_combo.setCurrentText("Floyd-Warshall")
    revision, count = window.revision, len(window.graph)
    window.initialize()
    assert window.busy and window.worker is not None
    QTest.keyClick(window, Qt.Key.Key_Y, Qt.KeyboardModifier.ControlModifier)
    window.redo()
    window.undo()
    window.add_node("durante")
    assert window.revision == revision and len(window.graph) == count
    assert window.cancel_button.isEnabled()
    window.cancel_operation()
    wait_idle(window)
    assert not window.states
    assert window.centralWidget().isEnabled()
    assert window.revision == revision


def test_cancelled_png_export_removes_staging_and_restores_ui(window):
    window.initialize()
    window.preview_before_export.setChecked(False)
    window.export("all")
    window.advance_export()
    assert list(window.output_dir.glob(".exportando_*"))
    window.cancel_operation()
    QTest.qWait(10)
    assert not list(window.output_dir.iterdir())
    assert window.centralWidget().isEnabled() and not window.busy


def test_failed_second_png_write_removes_all_partial_outputs(window, monkeypatch):
    window.initialize()
    original = image_exporter.save_image
    calls = 0

    def fail_second(image, path):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("Sin espacio")
        original(image, path)

    monkeypatch.setattr(image_exporter, "save_image", fail_second)
    with pytest.raises(OSError, match="Sin espacio"):
        image_exporter.export_graph(*export_args(window, "all"))
    assert not list(window.output_dir.iterdir())


@pytest.mark.parametrize("output_format", ["pdf", "svg"])
def test_failed_document_commit_is_never_reported_as_success(window, monkeypatch, output_format):
    window.initialize()
    original = QtCore.QSaveFile

    class FailedCommit(original):
        def commit(self):
            return False

    monkeypatch.setattr(QtCore, "QSaveFile", FailedCommit)
    with pytest.raises(OSError):
        image_exporter.export_graph(*export_args(window), output_format=output_format)
    assert not list(window.output_dir.iterdir())


def test_pdf_contains_selectable_text_and_svg_is_vector(window):
    window.initialize()
    pdf = image_exporter.export_graph(
        *export_args(window), output_format="pdf", title="Prueba vectorial"
    )
    document = QPdfDocument()
    assert document.load(str(pdf)) == QPdfDocument.Error.None_
    text = document.getAllText(0).text()
    assert "Prueba vectorial" in text and "Dijkstra" in text
    document.close()
    svg = image_exporter.export_graph(*export_args(window), output_format="svg", theme="dark")
    root = ElementTree.parse(svg).getroot()
    assert root.tag.endswith("svg")
    assert any(element.tag.endswith("text") for element in root.iter())
    assert not any(element.tag.endswith("image") for element in root.iter())
    assert PALETTES["dark"].canvas in svg.read_text()


@pytest.mark.parametrize("scale", [0.8, 1.0, 1.5])
@pytest.mark.parametrize("layout", ["balanced", "graph", "tables"])
def test_single_slide_preserves_both_full_matrices_and_count(qapp, scale, layout):
    preset = read_preset(EXAMPLES / "repositorio_30.json")
    options = SlideOptions(
        font_scale=scale, graph_font_scale=scale, layout=layout, title="Matrices"
    )
    renderer = SlideRenderer(preset.graph, preset.positions, options)
    try:
        plans = renderer.plan("Floyd-Warshall")
        assert len(plans) == 1 and plans[0].graph
        assert len(plans) == page_count(preset.graph, "Floyd-Warshall", options)
        for kind in ("matrix", "intermediates"):
            cells = [
                (i, j)
                for plan in plans
                for block, x, y in plan.blocks
                if block.kind == kind
                for i in block.entries
                for j in block.columns
            ]
            assert len(cells) == 900 and len(set(cells)) == 900
        for plan in plans:
            rectangles = [plan.graph_rect]
            for block, x, y in plan.blocks:
                rect = QRectF(x, y, block.width, block.height)
                assert rect.left() >= 32 and rect.right() <= 1888
                assert rect.top() >= content_top(options)
                assert rect.bottom() <= 1080 - footer_height(options, "Floyd-Warshall")
                assert all(not rect.intersects(other) for other in rectangles)
                rectangles.append(rect)
    finally:
        renderer.close()


def test_dijkstra_tables_layout_contains_all_distances(window):
    window.initialize()
    renderer = SlideRenderer(
        window.graph, window.graph_view.positions(), SlideOptions(layout="tables")
    )
    try:
        plans = renderer.plan("Dijkstra")
        assert len(plans) == 1 and plans[0].graph
        rows = [entry for plan in plans for block, *_ in plan.blocks for entry in block.entries]
        assert set(rows) == set(window.graph)
    finally:
        renderer.close()


def test_single_slide_matrix_highlights_keep_original_cell_indices(qapp, monkeypatch):
    from dataclasses import replace

    from graph_visualizer.export import slide_renderer

    preset = read_preset(EXAMPLES / "repositorio_30.json")
    state = replace(
        floyd_warshall_steps(preset.graph)[0], k=29, cell=(29, 29), changed=frozenset({(29, 29)})
    )
    renderer = SlideRenderer(preset.graph, preset.positions, SlideOptions())
    calls = []
    colors = slide_renderer.matrix_colors

    def inspect(state, row, col, palette):
        result = colors(state, row, col, palette)
        if result[2]:
            calls.append((row, col, result))
        return result

    monkeypatch.setattr(slide_renderer, "matrix_colors", inspect)
    try:
        part = next(
            i
            for i, plan in enumerate(renderer.plan(state.algorithm))
            if any(
                block.kind == "matrix" and 29 in block.entries and 29 in block.columns
                for block, *_ in plan.blocks
            )
        )
        renderer.image([(0, part)], [state], "1", "666")
        assert calls
        assert all(
            (row, col) == (29, 29) and result[0] == renderer.palette.improvement and result[1]
            for row, col, result in calls
        )
    finally:
        renderer.close()


def test_long_ids_have_unique_aliases_correct_hit_areas_and_full_reference(qapp):
    nodes = ["un_inicio_" + "centro" * 10 + ending + "_final" for ending in ("A", "B")]
    graph = nx.MultiDiGraph()
    graph.add_edge(*nodes, weight=-1e-7)
    renderer = SlideRenderer(graph, {nodes[0]: (0, 0), nodes[1]: (400, 0)}, SlideOptions())
    try:
        assert len(set(renderer.aliases.values())) == 2
        for item in renderer.view.nodes.values():
            point = QtCore.QPointF(item.node_width / 2, 0)
            assert item.shape().contains(point) and item.connection_zone(point)
            assert item.node_id in item.toolTip()
        glossary = [
            entry
            for plan in renderer.plan("Dijkstra")
            for block, *_ in plan.blocks
            if block.kind == "glossary"
            for entry in block.entries
        ]
        assert {entry[1] for entry in glossary} == set(nodes)
        assert len(renderer.plan("Dijkstra")) == page_count(graph, "Dijkstra", SlideOptions())
    finally:
        renderer.close()


def test_presets_restore_execution_settings_even_with_identical_graph(window, tmp_path):
    original = window.current_preset()
    modified = window.current_preset("Otra configuración")
    modified.settings.update(algorithm="Bellman-Ford", detail=False, early_stop=True)
    path = tmp_path / "settings.json"
    write_preset(path, modified)
    assert window.load_preset_path(path)
    assert window.current_preset().settings == modified.settings
    window.undo()
    assert window.current_preset().settings == original.settings
    window.redo()
    assert window.current_preset().settings == modified.settings


def test_preferences_validate_and_roundtrip(tmp_path):
    path = tmp_path / "preferences.json"
    save_preferences(path, DEFAULTS | {"theme": "dark", "ui_layout": "right", "accent": "#123abc"})
    values = load_preferences(path)
    assert (values["theme"], values["ui_layout"], values["accent"]) == ("dark", "right", "#123abc")
    path.write_text(json.dumps({"theme": [], "export_resolution": True, "ui_font_size": 999}))
    assert load_preferences(path) == DEFAULTS
    path.write_text("{broken")
    assert load_preferences(path) == DEFAULTS


@pytest.mark.parametrize("theme", PALETTES)
def test_theme_text_and_state_colors_are_legible(theme):
    palette = PALETTES[theme]

    def contrast(fg, bg):
        a, b = sorted((luminance(fg), luminance(bg)))
        return (b + 0.05) / (a + 0.05)

    for background in (
        palette.canvas,
        palette.surface,
        palette.visited,
        palette.unreached,
        palette.tentative,
        palette.error_fill,
        palette.improvement,
        palette.k_fill,
    ):
        assert contrast(palette.text, background) >= 4.5
    assert contrast(palette.current_text, palette.current) >= 4.5
    for accent in ("#ffffff", "#000000", "#ffcc00", "#999999", "#ff0000"):
        assert contrast(foreground(accent), accent) >= 4.5


def test_custom_layouts_preserve_graph_and_saved_preferences(window):
    graph = window.current_preset().document()
    window.preferences.update(theme="dark", ui_layout="right", ui_font_size=15)
    window.apply_appearance()
    window.persist_preferences()
    assert window.workspace_splitter.widget(1) is window.sidebar
    assert window.current_preset().document() == graph
    values = load_preferences(window.data_dir / "preferences.json")
    assert values["theme"] == "dark" and values["ui_layout"] == "right"
    window.preferences["ui_layout"] = "bottom"
    window.apply_appearance()
    assert window.visual_splitter.orientation() == Qt.Orientation.Vertical
    window.toggle_focus_layout()
    assert not window.sidebar.isVisible()
    window.toggle_focus_layout()
    assert window.sidebar.isVisible() and window.preferences["ui_layout"] == "bottom"


def test_preview_navigation_and_full_size_uses_export_image(window):
    window.initialize()
    dialog = ExportPreview(
        window,
        window.graph,
        window.graph_view.positions(),
        window.states,
        window.start,
        window.target,
        0,
        "all",
        window.export_options(),
    )
    dialog.page_input.setValue(dialog.total_pages)
    dialog.zoom.setCurrentIndex(2)
    assert len(dialog.images) == 1
    actual = dialog.labels[0].pixmap().toImage()
    expected = image_exporter.render_state(
        window.graph,
        window.graph_view.positions(),
        window.states[-1],
        window.start,
        window.target,
        len(window.states) - 1,
        len(window.states),
        **window.export_options(),
    )
    assert dialog.images[0] == expected
    assert actual == expected.convertToFormat(actual.format())
    dialog.close()


def test_coordinate_edit_and_alignment_are_undoable(window):
    before = window.graph_view.positions()
    dialog = GraphDataDialog(window)
    rows = range(3)
    selection = dialog.node_table.selectionModel()
    for row in rows:
        selection.select(
            dialog.node_table.model().index(row, 0),
            QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows,
        )
    dialog.arrange(1, False)
    dialog.apply()
    after = window.graph_view.positions()
    assert len({after[dialog.nodes[row]][1] for row in rows}) == 1
    assert before != after
    window.undo()
    assert window.graph_view.positions() == before
    dialog.node_table.item(0, 1).setText("nan")
    dialog.apply()
    assert window.graph_view.positions() == before
    assert "finitos" in dialog.error.text()
    dialog.close()


def test_cli_batch_export_does_not_modify_working_data(tmp_path):
    data = tmp_path / "data"
    output = tmp_path / "output"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "graph_visualizer",
            "--export-preset",
            str((EXAMPLES / "bellman_ford.json").resolve()),
            "--format",
            "svg",
            "--output-dir",
            str(output),
            "--data-dir",
            str(data),
        ],
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert Path(result.stdout.strip()).exists()
    assert list(output.rglob("*.svg"))
    assert not data.exists()
