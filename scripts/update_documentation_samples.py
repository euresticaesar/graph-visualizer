"""Reproduce the documented slides and desktop captures without touching user data."""

import os
import shutil
import tempfile
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QLocale  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

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
IMAGES = ROOT / "docs/images"


def save_capture(widget, path):
    QTest.qWait(30)
    if not widget.grab().save(str(path)):
        raise OSError(f"No se pudo guardar {path}.")


def main():
    QLocale.setDefault(QLocale("es_MX"))
    app = QApplication([])
    app.setStyle("Fusion")
    IMAGES.mkdir(parents=True, exist_ok=True)
    preset = read_preset(ROOT / "src/graph_visualizer/examples/repositorio_30.json")
    assert len(preset.graph) == 30 and preset.graph.number_of_edges() == 63
    assert len(ordered_arcs(preset.graph)) == 126
    with tempfile.TemporaryDirectory(prefix="gv-doc-samples-") as temporary:
        scratch = Path(temporary)
        for name, states in (
            ("floyd-30-matriz", floyd_warshall_steps(preset.graph)),
            ("bellman-30-tablas", bellman_ford_steps(preset.graph, "1")),
        ):
            assert reconstruct_path(states[-1], "1", "666") == ["1", "10", "27", "666"]
            assert route_description(states[-1], "1", "666").endswith("Costo 10")
            options = SlideOptions(resolution=3840, title="30 nodos · 63 conexiones · Ruta 1 → 666")
            renderer = SlideRenderer(preset.graph, preset.positions, options)
            try:
                image = renderer.image([(len(states) - 1, 0)], states, "1", "666")
                assert image.size().toTuple() == (3840, 2160)
                if not image.save(str(IMAGES / f"{name}.png")):
                    raise OSError(f"No se pudo guardar {name}.")
                print(name, renderer.legibility(states[-1], "1", "666"))
            finally:
                renderer.close()
            if name.startswith("floyd"):
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
                shutil.copy2(path, IMAGES / "floyd-30-diapositiva.pdf")
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
            save_capture(window, ROOT / "demo_screenshot.png")
            window.reset()
            window.algorithm_combo.setCurrentText("Bellman-Ford")
            window.initialize()
            window.preferences["ui_layout"] = "bottom"
            window.apply_appearance()
            for height in (680, 940, 680):
                window.resize(940, height)
                QTest.qWait(30)
            save_capture(window, IMAGES / "layout-inferior-compacto.png")
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
            save_capture(preview, IMAGES / "vista-previa-completa.png")
            preview.reject()
        finally:
            window.close()
            window.deleteLater()
            app.processEvents()


if __name__ == "__main__":
    main()
