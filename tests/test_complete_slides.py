import json
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QRectF, Qt
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QAbstractButton, QTableWidget, QTableWidgetItem

from graph_visualizer.core.astar import astar_steps
from graph_visualizer.core.bellman_ford import bellman_ford_steps
from graph_visualizer.core.floyd_warshall import floyd_warshall_steps
from graph_visualizer.core.graph import ordered_arcs
from graph_visualizer.export.image_exporter import export_graph
from graph_visualizer.export.slide_renderer import (
    SlideOptions,
    SlideRenderer,
    content_top,
    footer_height,
)
from graph_visualizer.io.presets import read_preset
from graph_visualizer.ui.state_panel import MatrixHeader
from graph_visualizer.ui.themes import PALETTES

EXAMPLE = Path("src/graph_visualizer/examples/repositorio_30.json")


def assert_complete_geometry(plan, options, algorithm):
    bottom = 1080 - footer_height(options, algorithm)
    rectangles = [plan.graph_rect]
    if plan.focus_rect:
        assert not plan.focus_rect.intersects(plan.graph_rect)
        rectangles.append(plan.focus_rect)
    for block, x, y in plan.blocks:
        rect = QRectF(x, y, block.width, block.height)
        assert rect.left() >= 32 and rect.right() <= 1888
        assert rect.top() >= content_top(options) and rect.bottom() <= bottom
        assert all(not rect.intersects(other) for other in rectangles)
        rectangles.append(rect)


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("font_scale", [0.8, 1.0, 1.5])
@pytest.mark.parametrize("show_focus", [False, True])
def test_adaptive_small_table_gives_unused_space_to_graph(qapp, theme, font_scale, show_focus):
    preset = read_preset(EXAMPLE)
    options = SlideOptions(theme=theme, font_scale=font_scale, show_focus=show_focus)
    renderer = SlideRenderer(preset.graph, preset.positions, options)
    reserved = SlideRenderer(
        preset.graph, preset.positions, replace(options, composition="side", graph_fraction=0.52)
    )
    try:
        plan = renderer.plan("A*")[0]
        baseline = reserved.plan("A*")[0]

        def graph_scale(rect):
            return min(
                rect.width() / renderer.bounds.width(), rect.height() / renderer.bounds.height()
            )

        assert graph_scale(plan.graph_rect) > graph_scale(baseline.graph_rect)
        if font_scale == 1 and not show_focus:
            assert graph_scale(plan.graph_rect) > 1.4 * graph_scale(baseline.graph_rect)
        assert [node for block, *_ in plan.blocks for node in block.entries] == sorted(preset.graph)
        assert all(block.kind == "astar" and 0 < block.scale <= 1 for block, *_ in plan.blocks)
        assert_complete_geometry(plan, options, "A*")
        left = min(x for _, x, _ in plan.blocks)
        top = min(y for _, _, y in plan.blocks)
        if left >= plan.graph_rect.right():
            assert left == pytest.approx(plan.graph_rect.right() + 12)
        else:
            assert top == pytest.approx(plan.graph_rect.bottom() + 12)
        states = astar_steps(preset.graph, "3", "12")
        for index in (0, len(states) - 1):
            image = renderer.image([(index, 0)], states, "3", "12")
            assert image.size().toTuple() == (1920, 1080)
            assert renderer.plan("A*")[0] is plan
    finally:
        renderer.close()
        reserved.close()


@pytest.mark.parametrize("composition", ["auto", "top"])
@pytest.mark.parametrize("fraction", [0.2, 0.48, 0.65])
@pytest.mark.parametrize("font_scale", [0.8, 1.0, 1.5])
def test_lower_matrices_use_full_width_with_all_cells(qapp, composition, fraction, font_scale):
    preset = read_preset(EXAMPLE)
    options = SlideOptions(composition=composition, graph_fraction=fraction, font_scale=font_scale)
    renderer = SlideRenderer(preset.graph, preset.positions, options)
    try:
        plan = renderer.plan("Floyd-Warshall")[0]
        assert_complete_geometry(plan, options, "Floyd-Warshall")
        assert len(plan.blocks) == 2
        below = min(y for _, _, y in plan.blocks) >= plan.graph_rect.bottom() + 12
        rows = {}
        for block, x, y in plan.blocks:
            assert len(block.entries) == len(block.columns) == 30
            assert block.entries == block.columns == tuple(range(30))
            if not below:
                assert x >= plan.graph_rect.right() + 12
            rows.setdefault(y, []).append(QRectF(x, y, block.width, block.height))
        if below:
            for rects in rows.values():
                assert min(rect.left() for rect in rects) == 32
                assert max(rect.right() for rect in rects) == pytest.approx(1888, abs=0.002)
        else:
            assert min(x for _, x, _ in plan.blocks) == pytest.approx(plan.graph_rect.right() + 12)
            assert max(rect.right() for rects in rows.values() for rect in rects) == pytest.approx(
                1888
            )
        if composition == "top":
            body_height = 1080 - content_top(options) - footer_height(options, "Floyd-Warshall")
            assert plan.graph_rect.height() == pytest.approx(body_height * fraction - 12)
    finally:
        renderer.close()


@pytest.mark.parametrize("layout", ["balanced", "graph", "tables"])
@pytest.mark.parametrize("font_scale", [0.8, 1.0, 1.5])
def test_all_arcs_and_distances_share_one_slide_without_overlap(qapp, layout, font_scale):
    preset = read_preset(EXAMPLE)
    options = SlideOptions(layout=layout, font_scale=font_scale, title="Diapositiva completa")
    renderer = SlideRenderer(preset.graph, preset.positions, options)
    try:
        plans = renderer.plan("Bellman-Ford")
        assert len(plans) == 1
        plan = plans[0]
        assert plan.graph
        arcs = [
            entry for block, *_ in plan.blocks if block.kind == "arcs" for entry in block.entries
        ]
        nodes = [
            entry
            for block, *_ in plan.blocks
            if block.kind == "distances"
            for entry in block.entries
        ]
        assert tuple(arcs) == ordered_arcs(preset.graph)
        assert nodes == sorted(preset.graph)
        rects = [plan.graph_rect]
        for block, x, y in plan.blocks:
            rect = QRectF(x, y, block.width, block.height)
            assert rect.left() >= 32 and rect.right() <= 1888
            assert rect.top() >= content_top(options)
            assert rect.bottom() <= 1080 - footer_height(options, "Bellman-Ford")
            assert all(not rect.intersects(other) for other in rects)
            rects.append(rect)
    finally:
        renderer.close()


@pytest.mark.parametrize("algorithm", ["Bellman-Ford", "Floyd-Warshall"])
@pytest.mark.parametrize("output_format", ["png", "pdf", "svg"])
def test_one_large_state_exports_one_complete_landscape_slide(
    qapp, tmp_path, algorithm, output_format
):
    preset = read_preset(EXAMPLE)
    states = (
        bellman_ford_steps(preset.graph, "1")
        if algorithm == "Bellman-Ford"
        else floyd_warshall_steps(preset.graph)
    )
    path = export_graph(
        preset.graph,
        preset.positions,
        states,
        "1",
        "666",
        0,
        "final",
        tmp_path,
        output_format=output_format,
    )
    assert path.is_file()
    manifest = json.loads((path.parent / "manifest.json").read_text())
    assert manifest["output_count"] == 1
    assert manifest["outputs"][0]["size"] == [1920, 1080]
    assert manifest["outputs"][0]["states"][0]["parts"] == 1
    if output_format == "pdf":
        document = QPdfDocument()
        assert document.load(str(path)) == QPdfDocument.Error.None_
        assert document.pageCount() == 1
        text = " ".join(document.getAllText(0).text().split())
        assert "Ruta mínima" in text
        if algorithm == "Floyd-Warshall":
            assert "Distancias D" in text and "intermedios" in text
        else:
            assert "Arcos ordenados" in text and "V / d / π" in text
        document.close()


def test_full_explanation_is_present_in_slide_including_last_word(qapp, tmp_path):
    preset = read_preset(EXAMPLE)
    state = replace(
        bellman_ford_steps(preset.graph, "1")[-1],
        explanation="Texto completo " * 180 + "FIN_DE_EXPLICACION",
    )
    path = export_graph(
        preset.graph,
        preset.positions,
        [state],
        "1",
        "666",
        0,
        "current",
        tmp_path,
        output_format="pdf",
    )
    document = QPdfDocument()
    assert document.load(str(path)) == QPdfDocument.Error.None_
    text = document.getAllText(0).text()
    assert "FIN_DE_EXPLICACION" in text
    assert "…" not in text
    document.close()


@pytest.mark.parametrize("theme", PALETTES)
@pytest.mark.parametrize("custom_header", [False, True])
def test_table_corner_and_unused_header_follow_theme(window, qapp, theme, custom_header):
    window.preferences["theme"] = theme
    window.apply_appearance()
    table = QTableWidget(1, 1, window)
    if custom_header:
        header = MatrixHeader(Qt.Orientation.Horizontal, table)
        header.palette = window.palette
        table.setHorizontalHeader(header)
    table.setHorizontalHeaderLabels(["Nodo"])
    table.setItem(0, 0, QTableWidgetItem("A"))
    table.resize(440, 160)
    table.show()
    qapp.processEvents()
    try:
        expected = window.palette.header
        header = table.horizontalHeader()
        image = header.viewport().grab().toImage()
        x, y = header.length() + 8, image.height() // 2
        assert x < image.width()
        assert image.pixelColor(x, y).name() == expected
        corner = next(
            button
            for button in table.findChildren(QAbstractButton)
            if button.metaObject().className() == "QTableCornerButton"
        )
        image = corner.grab().toImage()
        assert image.pixelColor(image.width() // 2, image.height() // 2).name() == expected
        image = table.viewport().grab().toImage()
        assert (
            image.pixelColor(image.width() - 8, image.height() - 8).name() == window.palette.surface
        )
        table.setRowCount(40)
        table.setColumnCount(20)
        qapp.processEvents()
        horizontal, vertical = table.horizontalScrollBar(), table.verticalScrollBar()
        assert horizontal.isVisible() and vertical.isVisible()
        image = table.grab().toImage()
        x = table.width() - vertical.width() // 2 - table.frameWidth()
        y = table.height() - horizontal.height() // 2 - table.frameWidth()
        assert image.pixelColor(x, y).name() == window.palette.inset
    finally:
        table.close()
        table.deleteLater()
