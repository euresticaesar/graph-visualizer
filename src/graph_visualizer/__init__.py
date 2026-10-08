def main() -> int:
    import argparse
    import os
    import sys
    from pathlib import Path

    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
    from PySide6.QtWidgets import QApplication, QMessageBox

    from graph_visualizer.io.graph_io import initialize_graph_data
    from graph_visualizer.paths import DATA_DIR, OUTPUT_DIR
    from graph_visualizer.ui.main_window import MainWindow

    parser = argparse.ArgumentParser(
        description="Visualizador de Dijkstra, A*, Bellman-Ford y Floyd-Warshall"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR,
        help="Directorio del trabajo y presets personales",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=OUTPUT_DIR,
        help="Directorio de exportaciones PNG/PDF/SVG",
    )
    parser.add_argument("--export-preset", type=Path, help="Exporta un preset sin abrir la ventana")
    parser.add_argument("--format", choices=("png", "pdf", "svg"), default="png")
    parser.add_argument("--kind", choices=("all", "combined", "final"), default="final")
    parser.add_argument(
        "--theme",
        choices=("light", "dark", "paper", "contrast", "print", "colorblind"),
        default="light",
    )
    parser.add_argument("--resolution", type=int, choices=(1920, 2560, 3840), default=1920)
    parser.add_argument("--layout", choices=("balanced", "graph", "tables"), default="balanced")
    parser.add_argument("--font-scale", type=float, default=1.0, help="Escala de texto: 0.8 a 1.5")
    parser.add_argument("--composition", choices=("auto", "side", "top"), default="auto")
    parser.add_argument(
        "--graph-fraction", type=float, default=0.48, help="Espacio del grafo: 0.2 a 0.65"
    )
    parser.add_argument(
        "--dim-unrelated", action="store_true", help="Atenúa conexiones fuera de la ruta"
    )
    parser.add_argument(
        "--focus", action="store_true", help="Amplía la comparación activa dentro de la diapositiva"
    )
    parser.add_argument("--detail", choices=("preset", "summary", "detailed"), default="preset")
    parser.add_argument("--simple", action="store_true", help="Exporta solo el grafo")
    args = parser.parse_args()
    if args.export_preset:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    QLocale.setDefault(QLocale("es_MX"))
    app = QApplication([sys.argv[0]])
    translator = QTranslator(app)
    translations = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load("qtbase_es", translations):
        app.installTranslator(translator)
    app.setApplicationName("Graph Visualizer · Caminos mínimos")
    app.setStyle("Fusion")
    if args.export_preset:
        from graph_visualizer.export.batch import export_preset

        try:
            print(export_preset(args))
            return 0
        except (OSError, ValueError) as error:
            print(f"No se pudo exportar: {error}", file=sys.stderr)
            return 1
    try:
        initialize_graph_data(args.data_dir)
        window = MainWindow(args.data_dir, args.output_dir)
    except (OSError, ValueError) as error:
        QMessageBox.critical(None, "No se pudieron cargar los datos del grafo", str(error))
        return 1
    window.show()
    return app.exec()
