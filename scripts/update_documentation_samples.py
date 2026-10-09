"""Reproduce the documented slides and desktop captures without touching user data."""

import argparse
import os
import shutil
import tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QLocale  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from graph_visualizer.core.astar import astar_steps  # noqa: E402
from graph_visualizer.core.bellman_ford import bellman_ford_steps  # noqa: E402
from graph_visualizer.core.dijkstra import reconstruct_path, route_description  # noqa: E402
from graph_visualizer.core.floyd_warshall import floyd_warshall_steps  # noqa: E402
from graph_visualizer.core.graph import ordered_arcs  # noqa: E402
from graph_visualizer.export.image_exporter import export_graph  # noqa: E402
from graph_visualizer.export.slide_renderer import SlideOptions, SlideRenderer  # noqa: E402
from graph_visualizer.io.graph_io import save_graph_data  # noqa: E402
from graph_visualizer.io.presets import read_preset  # noqa: E402
from graph_visualizer.ui.export_controls import ExportPreview  # noqa: E402
from graph_visualizer.ui.main_window import MainWindow  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def save_capture(widget, path):
    QTest.qWait(30)
    if not widget.grab().save(str(path)):
        raise OSError(f"No se pudo guardar {path}.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT)
    output = parser.parse_args().output_dir
    images = output / "docs/images"
    QLocale.setDefault(QLocale("es_MX"))
    app = QApplication([])
    app.setStyle("Fusion")
    images.mkdir(parents=True, exist_ok=True)
    preset = read_preset(ROOT / "src/graph_visualizer/examples/repositorio_30.json")
    assert len(preset.graph) == 30 and preset.graph.number_of_edges() == 63
    assert len(ordered_arcs(preset.graph)) == 126
    comparison_preset = read_preset(ROOT / "src/graph_visualizer/examples/bellman_ford.json")
    comparison_states = bellman_ford_steps(
        comparison_preset.graph, comparison_preset.settings["start"]
    )
    comparison_index = next(
        i
        for i, state in enumerate(comparison_states)
        if state.comparison and state.comparison.improved
    )
    renderer = SlideRenderer(
        comparison_preset.graph, comparison_preset.positions, SlideOptions(show_focus=True)
    )
    try:
        image = renderer.image(
            [(comparison_index, 0)],
            comparison_states,
            comparison_preset.settings["start"],
            comparison_preset.settings["target"],
        )
        if not image.save(str(images / "comparacion-didactica.png")):
            raise OSError("No se pudo guardar la comparación didáctica.")
    finally:
        renderer.close()
    astar_states = astar_steps(preset.graph, "3", "12", detailed=True)
    renderer = SlideRenderer(preset.graph, preset.positions, SlideOptions(show_legend=False))
    try:
        image = renderer.image([(0, 0)], astar_states, "3", "12")
        if not image.save(str(images / "astar-30-adaptativa.png")):
            raise OSError("No se pudo guardar la composición adaptativa de A*.")
    finally:
        renderer.close()
    with tempfile.TemporaryDirectory(prefix="gv-doc-samples-") as temporary:
        scratch = Path(temporary)
        floyd_states = floyd_warshall_steps(preset.graph)
        for name, states, composition, fraction in (
            ("floyd-30-matriz", floyd_states, "auto", 0.48),
            ("floyd-30-inferior", floyd_states, "top", 0.65),
            ("bellman-30-tablas", bellman_ford_steps(preset.graph, "1"), "auto", 0.48),
        ):
            assert reconstruct_path(states[-1], "1", "666") == ["1", "10", "27", "666"]
            assert route_description(states[-1], "1", "666").endswith("Costo 10")
            options = SlideOptions(
                resolution=3840,
                title="30 nodos · 63 conexiones · Ruta 1 → 666",
                composition=composition,
                graph_fraction=fraction,
            )
            renderer = SlideRenderer(preset.graph, preset.positions, options)
            try:
                image = renderer.image([(len(states) - 1, 0)], states, "1", "666")
                assert image.size().toTuple() == (3840, 2160)
                if not image.save(str(images / f"{name}.png")):
                    raise OSError(f"No se pudo guardar {name}.")
                print(name, renderer.legibility(states[-1], "1", "666"))
            finally:
                renderer.close()
            if name == "floyd-30-matriz":
                path = export_graph(
                    preset.graph,
                    preset.positions,
                    states,
                    "1",
                    "666",
                    0,
                    "final",
                    scratch / "exports",
                    output_format="pdf",
                    resolution=options.resolution,
                    title=options.title,
                )
                shutil.copy2(path, images / "floyd-30-diapositiva.pdf")
        save_graph_data(scratch / "data", preset.graph, preset.positions)
        window = MainWindow(scratch / "data", scratch / "output")
        try:
            window.resize(1600, 1000)
            window.show()
            app.processEvents()
            window.start_combo.setCurrentIndex(window.start_combo.findData("1"))
            window.target_combo.setCurrentIndex(window.target_combo.findData("666"))
            window.initialize()
            window.show_state(len(window.states) - 1)
            save_capture(window, output / "demo_screenshot.png")
            window.reset()
            window.algorithm_combo.setCurrentText("Bellman-Ford")
            window.initialize()
            window.preferences["ui_layout"] = "bottom"
            window.apply_appearance()
            for height in (680, 940, 680):
                window.resize(940, height)
                QTest.qWait(30)
            save_capture(window, images / "layout-inferior-compacto.png")
            preview = ExportPreview(
                window,
                window.graph,
                window.graph_view.positions(),
                window.states,
                "1",
                "666",
                len(window.states) - 1,
                "final",
                window.export_options(),
            )
            preview.resize(1030, 900)
            preview.show()
            save_capture(preview, images / "vista-previa-completa.png")
            preview.reject()
        finally:
            window.close()
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    main()
