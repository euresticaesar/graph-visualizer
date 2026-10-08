"""Controlled slide fixtures shared by regression tests and the update command."""

import json
from contextlib import contextmanager
from pathlib import Path

import networkx as nx
from PySide6.QtCore import QRectF, qVersion
from PySide6.QtGui import QFont, QFontInfo, QFontMetricsF

from graph_visualizer.core.bellman_ford import bellman_ford_steps
from graph_visualizer.core.floyd_warshall import floyd_warshall_steps
from graph_visualizer.export.slide_renderer import SlideOptions, SlideRenderer, text_font
from graph_visualizer.io.presets import read_preset

REPOSITORY = Path(__file__).resolve().parents[1]


@contextmanager
def reference_font():
    """Use the CI font for controlled renders without changing the application's theme."""
    previous = QFont.substitutes("Sans Serif")
    QFont.removeSubstitutions("Sans Serif")
    QFont.insertSubstitution("Sans Serif", "DejaVu Sans")
    try:
        yield
    finally:
        QFont.removeSubstitutions("Sans Serif")
        QFont.insertSubstitutions("Sans Serif", previous)


def fingerprint():
    font = text_font(18)
    metrics = QFontMetricsF(font)
    return {
        "qt": qVersion(),
        "font": QFontInfo(font).family(),
        "height": metrics.height(),
        "sample_width": metrics.horizontalAdvance("−∞ 1e-07 π abc 123"),
    }


def cases():
    preset = read_preset(REPOSITORY / "src/graph_visualizer/examples/floyd_warshall.json")
    states = floyd_warshall_steps(preset.graph)
    state = next(state for state in states if state.changed)
    yield (
        "matrix_highlights",
        preset.graph,
        preset.positions,
        state,
        preset.settings["start"],
        preset.settings["target"],
        SlideOptions(),
    )
    graph = nx.MultiDiGraph()
    graph.add_weighted_edges_from([("A", "B", 1), ("B", "C", -3), ("C", "B", 1)])
    yield (
        "negative_cycle",
        graph,
        {"A": (0, 0), "B": (300, -100), "C": (600, 0)},
        bellman_ford_steps(graph, "A")[-1],
        "A",
        "C",
        SlideOptions(theme="contrast"),
    )
    names = ["referencia_" + "identificador_muy_largo_" * 4 + suffix for suffix in ("A", "B", "C")]
    graph = nx.MultiDiGraph()
    graph.add_weighted_edges_from([(names[0], names[1], -1e-7), (names[1], names[2], 1e-8)])
    yield (
        "long_ids_dark",
        graph,
        {node: (i * 500, 0) for i, node in enumerate(names)},
        bellman_ford_steps(graph, names[0])[-1],
        names[0],
        names[-1],
        SlideOptions(theme="dark", font_scale=1.5, graph_font_scale=1.5),
    )
    preset = read_preset(REPOSITORY / "src/graph_visualizer/examples/bellman_ford.json")
    states = bellman_ford_steps(preset.graph, preset.settings["start"])
    state = next(state for state in states if state.comparison)
    yield (
        "colorblind_focus",
        preset.graph,
        preset.positions,
        state,
        preset.settings["start"],
        preset.settings["target"],
        SlideOptions(theme="colorblind", show_focus=True, composition="side", graph_fraction=0.4),
    )


def render_case(case):
    name, graph, positions, state, start, target, options = case
    renderer = SlideRenderer(graph, positions, options)
    try:
        image = renderer.image([(0, 0)], [state], start, target)
        plan = renderer.plan(state.algorithm)[0]
        regions = [QRectF(32, 22, 1856, 140), plan.graph_rect, QRectF(32, 1020, 1856, 60)]
        if plan.focus_rect:
            regions.append(plan.focus_rect)
        for block, x, y in plan.blocks:
            regions.append(QRectF(x, y, block.width, block.title_height * block.scale))
            for row in range(len(block.entries) + 1):
                top = block.title_height + (
                    block.header_height + (row - 1) * block.row_height if row else 0
                )
                height = block.row_height if row else block.header_height
                cursor = 0
                for width in block.widths:
                    regions.append(
                        QRectF(
                            x + cursor * block.scale,
                            y + top * block.scale,
                            width * block.scale,
                            height * block.scale,
                        )
                    )
                    cursor += width
        rects = [rect.toAlignedRect() for rect in regions]
        return image, [[rect.x(), rect.y(), rect.width(), rect.height()] for rect in rects]
    finally:
        renderer.close()


def update_references(destination):
    destination.mkdir(parents=True, exist_ok=True)
    records = {}
    for case in cases():
        image, regions = render_case(case)
        name = case[0]
        if not image.save(str(destination / f"{name}.png")):
            raise OSError(f"No se pudo guardar la referencia {name}.")
        records[name] = {"file": f"{name}.png", "regions": regions}
    (destination / "manifest.json").write_text(
        json.dumps({"environment": fingerprint(), "cases": records}, indent=2) + "\n",
        encoding="utf-8",
    )
