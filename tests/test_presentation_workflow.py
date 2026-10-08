import json
from copy import deepcopy
from pathlib import Path

import networkx as nx
import pytest
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt
from PySide6.QtPdf import QPdfDocument
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QLabel

from graph_visualizer.core.bellman_ford import bellman_ford_steps
from graph_visualizer.core.dijkstra import dijkstra_steps
from graph_visualizer.core.graph import graphs_equal
from graph_visualizer.export.image_exporter import export_graph
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
from graph_visualizer.ui.presentation_view import PresentationView


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


@pytest.mark.parametrize("composition", ["side", "top"])
@pytest.mark.parametrize("fraction", [0.2, 0.48, 0.65])
@pytest.mark.parametrize("algorithm", ["Bellman-Ford", "Floyd-Warshall"])
def test_manual_composition_with_focus_keeps_complete_nonoverlapping_slide(
    qapp, composition, fraction, algorithm
):
    preset = read_preset(Path("src/graph_visualizer/examples/repositorio_30.json"))
    renderer = SlideRenderer(
        preset.graph,
        preset.positions,
        SlideOptions(
            composition=composition, graph_fraction=fraction, show_focus=True, font_scale=1.5
        ),
    )
    try:
        plans = renderer.plan(algorithm)
        assert len(plans) == 1
        plan = plans[0]
        assert plan.focus_rect is not None
        rectangles = [plan.graph_rect, plan.focus_rect]
        assert not plan.graph_rect.intersects(plan.focus_rect)
        for block, x, y in plan.blocks:
            rect = QRectF(x, y, block.width, block.height)
            assert QRectF(0, 0, 1920, 1080).contains(rect)
            assert all(not rect.intersects(other) for other in rectangles)
            rectangles.append(rect)
        if algorithm == "Bellman-Ford":
            assert (
                sum(len(block.entries) for block, *_ in plan.blocks if block.kind == "arcs") == 126
            )
        else:
            assert sum(len(block.entries) * len(block.columns) for block, *_ in plan.blocks) == 1800
    finally:
        renderer.close()


def test_legibility_measures_fitted_text_and_actual_resolution(window):
    from dataclasses import replace

    state = replace(
        bellman_ford_steps(window.graph, window.start)[0], explanation="Explicación completa " * 100
    )
    renderer = SlideRenderer(window.graph, window.graph_view.positions(), SlideOptions())
    try:
        hd = renderer.legibility(state, window.start, window.target)
        assert 0 < hd["Explicación"] < 18
        renderer.options = replace(renderer.options, resolution=3840)
        high = renderer.legibility(state, window.start, window.target)
        assert high == pytest.approx({category: size * 2 for category, size in hd.items()})
    finally:
        renderer.close()


def test_focus_pdf_retains_tables_and_full_comparison(window, tmp_path):
    states = bellman_ford_steps(window.graph, window.start)
    index = next(i for i, state in enumerate(states) if state.comparison)
    path = export_graph(
        window.graph,
        window.graph_view.positions(),
        states,
        window.start,
        window.target,
        index,
        "current",
        tmp_path,
        output_format="pdf",
        show_focus=True,
        composition="top",
    )
    doc = QPdfDocument()
    assert doc.load(str(path)) == QPdfDocument.Error.None_
    assert doc.pageCount() == 1
    text = " ".join(doc.getAllText(0).text().split())
    assert "Foco del paso" in text and "Arcos ordenados" in text and "V / d / π" in text
    assert " ".join(states[index].comparison.explain().split()) in text
    doc.close()


def test_route_emphasis_preserves_connections_and_uses_redundant_strokes(window):
    renderer = SlideRenderer(
        window.graph, window.graph_view.positions(), SlideOptions(dim_unrelated=True)
    )
    states = dijkstra_steps(window.graph, window.start, window.target, detailed=True)
    try:
        renderer.image([(len(states) - 1, 0)], states, window.start, window.target)
        assert len(renderer.view.edges) == window.graph.number_of_edges()
        assert any(edge.opacity() == 0.3 for edge in renderer.view.edges.values())
        assert any(edge.opacity() == 1 for edge in renderer.view.edges.values())
        compared = next(state for state in states if state.current_edge)
        renderer.view.apply_state(compared, window.start, window.target)
        assert any(
            edge.pen().style() == Qt.PenStyle.DashLine for edge in renderer.view.edges.values()
        )
    finally:
        renderer.close()


def test_viewer_keyboard_navigation_marks_and_exit_preserve_workspace(window, qapp):
    window.initialize()
    window.show_state(2)
    window.graph_view.auto_fit = False
    window.graph_view.scale(1.2, 1.2)
    original = (window.state_index, window.graph_view.transform(), window.graph_view.positions())
    viewer = PresentationView(window)
    viewer.show()
    qapp.processEvents()
    QTest.keyClick(viewer, Qt.Key.Key_Right)
    assert viewer.index == 3 and window.state_index == 2
    QTest.keyClick(viewer, Qt.Key.Key_M)
    assert viewer.states[3].step in window.bookmarks
    viewer.mode.setCurrentIndex(2)
    assert viewer.indices() == (3,)
    QTest.keyClick(viewer, Qt.Key.Key_H)
    assert not viewer.controls.isVisible()
    QTest.keyClick(viewer, Qt.Key.Key_H)
    assert viewer.controls.isVisible()
    viewer.mode.setCurrentIndex(1)
    viewer.advance(1)
    assert viewer.index in viewer.phase_indices
    QTest.keyClick(viewer, Qt.Key.Key_Escape)
    assert viewer.closed and not viewer.timer.isActive()
    assert (
        window.state_index,
        window.graph_view.transform(),
        window.graph_view.positions(),
    ) == original
    assert not window.output_dir.exists()


def test_preview_4k_updates_real_output_resolution(window):
    from graph_visualizer.ui.export_controls import ExportPreview

    window.initialize()
    preview = ExportPreview(
        window,
        window.graph,
        window.graph_view.positions(),
        window.states,
        window.start,
        window.target,
        window.state_index,
        "current",
        window.export_options(),
    )
    before = dict(preview.measurements)
    preview.set_4k()
    assert preview.images[0].width() == 3840
    assert window.export_options()["resolution"] == 3840
    assert preview.measurements == pytest.approx(
        {category: size * 2 for category, size in before.items()}
    )
    preview.reject()


def test_accessible_errors_and_state_announcements(window, monkeypatch):
    from graph_visualizer.ui import accessibility

    announcements = []
    monkeypatch.setattr(accessibility.QAccessible, "isActive", lambda: True)
    monkeypatch.setattr(
        accessibility.QAccessible,
        "updateAccessibility",
        lambda event: announcements.append(event.message()),
    )
    window.editor.node_id.setText("")
    window.editor.add_button.click()
    assert "El ID debe ser un texto no vacío." in announcements
    window.initialize()
    assert any("Dijkstra" in message and "Paso" in message for message in announcements)
    assert window.editor.node_id.accessibleName()
    assert window.editor.source_combo.accessibleName()


def test_keyboard_can_edit_navigate_and_open_export_without_mouse(window, qapp):
    QTest.keyClick(window, Qt.Key.Key_2, Qt.KeyboardModifier.ControlModifier)
    assert window.tabs.currentIndex() == 1
    editor = window.editor
    editor.node_id.setFocus()
    editor.node_id.setText("Teclado")
    editor.add_button.setFocus()
    QTest.keyClick(editor.add_button, Qt.Key.Key_Space)
    assert "Teclado" in window.graph
    QTest.keyClick(window, Qt.Key.Key_1, Qt.KeyboardModifier.ControlModifier)
    window.run_button.setFocus()
    QTest.keyClick(window.run_button, Qt.Key.Key_Space)
    assert window.states
    QTest.keyClick(window, Qt.Key.Key_Right, Qt.KeyboardModifier.AltModifier)
    assert window.state_index == 1
    QTest.keyClick(window, Qt.Key.Key_2, Qt.KeyboardModifier.ControlModifier)
    assert window.tabs.currentIndex() == 0
    QTest.keyClick(window, Qt.Key.Key_4, Qt.KeyboardModifier.ControlModifier)
    assert window.tabs.currentIndex() == 3
    window.export_buttons[0].setFocus()
    QTest.keyClick(window.export_buttons[0], Qt.Key.Key_Space)
    qapp.processEvents()
    from graph_visualizer.ui.export_controls import ExportPreview

    dialog = next(dialog for dialog in window.findChildren(ExportPreview) if dialog.isVisible())
    assert dialog.diagnosis.accessibleName()
    QTest.keyClick(dialog, Qt.Key.Key_Escape)
    assert not window.output_dir.exists()


def test_matrix_keyboard_navigation_describes_original_rows_and_columns(window):
    window.algorithm_combo.setCurrentText("Floyd-Warshall")
    window.initialize()
    for table in window.matrix_panel.tables:
        table.setFocus()
        table.setCurrentCell(0, 0)
        QTest.keyClick(table, Qt.Key.Key_Right)
        QTest.keyClick(table, Qt.Key.Key_Down)
        assert (table.currentRow(), table.currentColumn()) == (1, 1)
        assert len(table.selectedItems()) == 1
        description = table.currentItem().data(Qt.ItemDataRole.AccessibleDescriptionRole)
        node = window.states[0].nodes[1]
        assert table.accessibleName() in description
        assert f"fila {node}, columna {node}" in description


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("kind", ["current", "all"])
def test_preview_fit_and_empty_surface_follow_window_theme(window, theme, kind):
    from graph_visualizer.ui.export_controls import ExportPreview

    window.preferences["theme"] = theme
    window.apply_appearance()
    window.initialize()
    preview = ExportPreview(
        window,
        window.graph,
        window.graph_view.positions(),
        window.states,
        window.start,
        window.target,
        0,
        kind,
        window.export_options(),
    )
    preview.show()
    fit_updates = QSignalSpy(preview.fit_timer.timeout)
    for zoom in (0, 1, 2, 0):
        preview.zoom.setCurrentIndex(zoom)
        for width, height in ((1030, 780), (900, 660), (1120, 1000)):
            preview.resize(width, height)
            QTest.qWait(20)
            viewport = preview.scroll.viewport()
            labels = preview.labels[: len(preview.images)]
            for label, image in zip(labels, preview.images, strict=True):
                pixmap = label.pixmap()
                expected_width = (
                    min(image.width(), viewport.width() - 40)
                    if zoom == 0
                    else image.width() // 2
                    if zoom == 1
                    else image.width()
                )
                assert pixmap.width() == expected_width
                assert abs(pixmap.height() - image.height() * expected_width / image.width()) <= 1
                assert label.size() == pixmap.size()
                assert label.contentsRect().size() == pixmap.size()
                if zoom == 0:
                    left = label.mapTo(viewport, QPoint()).x()
                    assert abs(left - (viewport.width() - label.width()) / 2) <= 1
            vertical = preview.scroll.verticalScrollBar()
            vertical.setValue(0)
            assert 0 <= labels[0].mapTo(viewport, QPoint()).y() < viewport.height()
            vertical.setValue(vertical.maximum())
            bottom = labels[-1].mapTo(viewport, labels[-1].rect().bottomLeft()).y()
            assert 0 <= bottom < viewport.height()
            if vertical.maximum():
                surface = viewport.grab().toImage()
                assert surface.pixelColor(2, 2).name() == window.palette.canvas
            settled = fit_updates.count()
            QTest.qWait(20)
            assert fit_updates.count() == settled  # No scrollbar/fit resize loop.
    preview.reject()


def assert_workspace_panels_are_separated(window):
    splitter = window.visual_splitter

    def rect(widget):
        return QRect(widget.mapTo(splitter, QPoint()), widget.size())

    graph, results = rect(window.graph_view), rect(window.results_panel)
    assert not graph.intersects(results)
    assert splitter.rect().contains(graph) and splitter.rect().contains(results)
    assert results.height() >= window.results_panel.minimumSizeHint().height()
    if splitter.orientation() == Qt.Orientation.Vertical:
        assert graph.bottom() + splitter.handleWidth() < results.top()
    else:
        assert graph.right() + splitter.handleWidth() < results.left()
    panel = (
        window.matrix_panel
        if window.algorithm_combo.currentText() == "Floyd-Warshall"
        else window.state_panel
    )
    widgets = [window.results_title]
    for index in range(panel.splitter.count()):
        card = panel.splitter.widget(index)
        if card.isVisible():
            widgets += [card.findChild(QLabel, "section")]
    tables = panel.tables if hasattr(panel, "tables") else (panel.table, panel.arcs)
    for table in tables:
        if table.isVisible():
            widgets += [table, table.horizontalHeader(), table.viewport()]
            assert table.viewport().height() > 0
    for widget in widgets:
        assert widget.isVisible() and not widget.size().isEmpty()
        assert results.contains(rect(widget))
        assert not graph.intersects(rect(widget))


def test_short_bottom_layout_preserves_graph_area(window):
    window.algorithm_combo.setCurrentText("Bellman-Ford")
    window.initialize()
    window.preferences["ui_layout"] = "bottom"
    window.apply_appearance()
    window.resize(940, 680)
    QTest.qWait(20)
    assert window.graph_view.height() >= 150
    assert window.state_panel.table.minimumHeight() == 64
    assert not window.state_panel.hint.isVisible()
    assert_workspace_panels_are_separated(window)
    window.resize(940, 940)
    QTest.qWait(20)
    assert window.state_panel.hint.isVisible()
    assert window.state_panel.table.minimumHeight() == 100
    assert_workspace_panels_are_separated(window)
    # A valid manual split survives a refit without resetting the user's proportions.
    window.visual_splitter.setSizes([300, 270])
    sizes = window.visual_splitter.sizes()
    window.refit_workspace()
    assert window.visual_splitter.sizes() == sizes
    for algorithm in ("Floyd-Warshall", "A*", "Bellman-Ford"):
        window.reset()
        window.algorithm_combo.setCurrentText(algorithm)
        window.initialize()
        for layout in ("classic", "bottom", "right", "bottom"):
            window.preferences["ui_layout"] = layout
            window.apply_appearance()
            for height in (680, 940, 680):
                window.resize(940, height)
                QTest.qWait(20)
                assert_workspace_panels_are_separated(window)


def test_floyd_summary_focus_shows_a_real_improved_cell(window, tmp_path):
    from graph_visualizer.core.floyd_warshall import floyd_warshall_steps

    states = floyd_warshall_steps(window.graph)
    index = next(i for i, state in enumerate(states) if state.changed)
    state = states[index]
    path = export_graph(
        window.graph,
        window.graph_view.positions(),
        states,
        window.start,
        window.target,
        index,
        "current",
        tmp_path,
        output_format="pdf",
        show_focus=True,
    )
    doc = QPdfDocument()
    assert doc.load(str(path)) == QPdfDocument.Error.None_
    text = " ".join(doc.getAllText(0).text().split())
    i, j = min(state.changed)
    assert f"D[{state.nodes[i]}, {state.nodes[j]}] =" in text
    assert "Intermedio k:" in text and "Foco del paso" in text
    doc.close()
