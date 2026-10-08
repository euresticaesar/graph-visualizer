import json
import math
from dataclasses import replace

import networkx as nx
import pytest
from PySide6.QtCore import QRectF
from PySide6.QtGui import QFont, QImage
from PySide6.QtPdf import QPdfDocument

from graph_visualizer.core.astar import astar_steps
from graph_visualizer.core.bellman_ford import bellman_ford_steps
from graph_visualizer.core.dijkstra import dijkstra_steps
from graph_visualizer.core.floyd_warshall import floyd_warshall_steps
from graph_visualizer.core.graph import ordered_arcs
from graph_visualizer.core.models import format_number
from graph_visualizer.export.image_exporter import export_graph
from graph_visualizer.export.slide_renderer import (
    SlideOptions,
    SlideRenderer,
    cell_is_bold,
    header_geometry,
)
from graph_visualizer.ui.themes import PALETTES, luminance


@pytest.fixture(params=["Dijkstra", "A*", "Bellman-Ford", "Floyd-Warshall"])
def execution(request):
    graph = nx.MultiDiGraph()
    for source, target, key, weight in (
        ("A", "B", 17, 4),
        ("A", "B", 31, 2),
        ("A", "B", 41, 5),
        ("A", "C", 53, 10),
        ("B", "C", 67, 1),
    ):
        graph.add_edge(source, target, key=key, weight=weight)
    algorithm = request.param
    if algorithm == "Dijkstra":
        states = dijkstra_steps(graph, "A", "C", detailed=True)
    elif algorithm == "A*":
        states = astar_steps(graph, "A", "C", detailed=True)
    elif algorithm == "Bellman-Ford":
        states = bellman_ford_steps(graph, "A")
    else:
        states = floyd_warshall_steps(graph, detailed=True)
    return graph, {"A": (0, 0), "B": (300, -100), "C": (600, 0)}, states


@pytest.mark.parametrize("theme", PALETTES)
def test_comparison_emphasis_is_legible_and_matches_render_diagnostics(qapp, execution, theme):
    graph, positions, states = execution
    renderer = SlideRenderer(graph, positions, SlideOptions(theme=theme, show_focus=True))
    try:
        for improved in (True, False):
            state = next(
                state
                for state in states
                if state.comparison and state.comparison.improved == improved
            )
            comparison = state.comparison
            plan = renderer.plan(state.algorithm)[0]
            *_, y, height = header_geometry(renderer.options)
            for focus, rect, category, background in (
                (False, QRectF(32, y, 1856, height), "Explicación", renderer.palette.canvas),
                (
                    True,
                    plan.focus_rect.adjusted(12, 38, -12, -10),
                    "Comparación ampliada",
                    renderer.palette.inset,
                ),
            ):
                document = renderer.explanation_document(state, "A", "C", rect, focus=focus)
                if not focus:
                    header_document = document
                assert document.size().height() <= rect.height()
                assert document.idealWidth() <= rect.width()
                assert (
                    renderer.legibility(state, "A", "C")[category]
                    == document.defaultFont().pixelSize()
                )
                f = format_number
                for detail in (
                    f"{f(comparison.left)} + {f(comparison.right)} = {f(comparison.candidate)}",
                    f"¿Mejora estricta? {'Sí' if improved else 'No'}",
                    f"Resultante: {f(comparison.after)}",
                ):
                    cursor = document.find(detail)
                    assert not cursor.isNull()
                    assert cursor.charFormat().fontWeight() == QFont.Weight.Bold
                    color = cursor.charFormat().foreground().color().name()
                    light, dark = sorted((luminance(color), luminance(background)), reverse=True)
                    assert (light + 0.05) / (dark + 0.05) >= 4.5
                    if theme == "print":
                        assert color == renderer.palette.text
                if state.algorithm == "Floyd-Warshall":
                    assert f"Intermedio k = {state.nodes[state.k]}" in document.toPlainText()
                    assert "D[i,k] + D[k,j]" in document.toPlainText()
            image = renderer.image([(0, 0)], [state], "A", "C")
            assert image.size().toTuple() == (1920, 1080)
            # Verify that semantic colors reach the actual exported image.
            if theme != "print":
                header = image.copy(32, round(y), 1856, round(height))
                header = header.convertToFormat(QImage.Format.Format_RGBA8888)
                pixels = header.constBits().tobytes()
                decision = header_document.find(f"¿Mejora estricta? {'Sí' if improved else 'No'}")
                assert bytes(decision.charFormat().foreground().color().getRgb()) in pixels
    finally:
        renderer.close()


def test_pdf_omits_connection_ids_but_retains_operands_routes_and_source_events(
    qapp, tmp_path, execution
):
    graph, positions, states = execution
    index = next(
        i for i, state in enumerate(states) if state.comparison and state.comparison.improved
    )
    path = export_graph(
        graph,
        positions,
        states,
        "A",
        "C",
        index,
        "current",
        tmp_path,
        output_format="pdf",
        show_focus=True,
    )
    document = QPdfDocument()
    try:
        assert document.load(str(path)) == QPdfDocument.Error.None_
        assert document.pageCount() == 1
        text = " ".join(document.getAllText(0).text().split())
        comparison = states[index].comparison
        f = format_number
        assert "#" not in text and "ID" not in text
        assert f"{f(comparison.left)} + {f(comparison.right)} = {f(comparison.candidate)}" in text
        assert f"Resultante: {f(comparison.after)}" in text
        assert "Foco del paso" in text
        assert "Sin ruta confirmada" in text or "Ruta del estado actual" in text
    finally:
        document.close()
    manifest = json.loads((path.parent / "manifest.json").read_text())
    assert manifest["events"][0]["explanation"] == states[index].explanation
    renderer = SlideRenderer(graph, positions, SlideOptions())
    try:
        initial = renderer.explanation(states[0], "A", "C")
        final = renderer.explanation(states[-1], "A", "C")
        assert "ID" not in initial
        assert "Ruta mínima: A → B → C · Costo 3" in final
    finally:
        renderer.close()


@pytest.mark.parametrize("show_ids", [False, True])
def test_hiding_arc_ids_keeps_all_parallel_arcs_and_the_exact_highlight(qapp, show_ids):
    graph = nx.MultiDiGraph()
    graph.add_edge("A", "B", key=17, weight=2)
    graph.add_edge("A", "B", key=31, weight=2)
    states = bellman_ford_steps(graph, "A")
    state = next(state for state in states if state.current_edge == ("A", "B", 31))
    renderer = SlideRenderer(
        graph, {"A": (0, 0), "B": (400, 0)}, SlideOptions(show_edge_ids=show_ids)
    )
    try:
        plan = renderer.plan("Bellman-Ford")[0]
        blocks = [block for block, *_ in plan.blocks if block.kind == "arcs"]
        assert tuple(entry for block in blocks for entry in block.entries) == ordered_arcs(graph)
        for block in blocks:
            assert ("ID" in block.headers) == show_ids
            for entry in block.entries:
                values = block.values(state, entry)
                assert len(values) == len(block.headers) == (4 if show_ids else 3)
                assert all(
                    cell_is_bold(block, state, entry, col, values) == (entry[2] == 31)
                    for col in range(len(values))
                )
        image = renderer.image([(0, 0)], [state], "A", "B")
        for block, x, y in plan.blocks:
            if block.kind == "arcs":
                for row, entry in enumerate(block.entries):
                    top = (
                        y
                        + (block.title_height + block.header_height + row * block.row_height)
                        * block.scale
                    )
                    color = image.pixelColor(
                        round(x + 2 * block.scale), round(top + 2 * block.scale)
                    ).name()
                    assert color == (
                        renderer.palette.comparison_fill
                        if entry[2] == 31
                        else renderer.palette.surface
                    )
        assert "#31" not in renderer.explanation(state, "A", "B")
    finally:
        renderer.close()


def test_literal_node_names_survive_emphasis_without_html_or_id_stripping(qapp):
    source, target = "<b>A & #17</b>", "<i>B</i>"
    graph = nx.MultiDiGraph()
    graph.add_edge(source, target, key=17, weight=1)
    state = next(
        state for state in dijkstra_steps(graph, source, target, detailed=True) if state.comparison
    )
    renderer = SlideRenderer(graph, {source: (0, 0), target: (400, 0)}, SlideOptions())
    try:
        document = renderer.explanation_document(state, source, target, QRectF(0, 0, 1856, 90))
        assert source in document.toPlainText() and target in document.toPlainText()
        assert "Conexión #17." not in document.toPlainText()
    finally:
        renderer.close()


def test_negative_cycle_warning_has_emphasis_without_a_false_finite_route(qapp):
    graph = nx.MultiDiGraph()
    graph.add_weighted_edges_from([("A", "B", 1), ("B", "C", -3), ("C", "B", 1)])
    state = bellman_ford_steps(graph, "A")[-1]
    renderer = SlideRenderer(graph, {"A": (0, 0), "B": (300, -100), "C": (600, 0)}, SlideOptions())
    try:
        document = renderer.explanation_document(state, "A", "C", QRectF(0, 0, 1856, 90))
        warning = document.find("no existe costo mínimo finito")
        assert not warning.isNull() and warning.charFormat().fontWeight() == QFont.Weight.Bold
        assert warning.charFormat().foreground().color().name() == renderer.palette.error
        assert "Ruta mínima" not in document.toPlainText()
        assert state.distances["C"] == -math.inf
        # Unbounded prose still fits and keeps the final word at the chosen font.
        long = replace(state, explanation="Explicación extensa " * 150 + "FIN_DE_EXPLICACION")
        fitted = renderer.explanation_document(long, "A", "C", QRectF(0, 0, 1856, 90))
        assert fitted.size().height() <= 90
        assert "FIN_DE_EXPLICACION" in fitted.toPlainText()
    finally:
        renderer.close()
