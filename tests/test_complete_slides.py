import json
from dataclasses import replace
from pathlib import Path

import pytest
from PySide6.QtCore import QRectF, Qt
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QAbstractButton, QTableWidget, QTableWidgetItem

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
    finally:
        table.close()
        table.deleteLater()
