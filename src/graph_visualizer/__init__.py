def main() -> int:
    import argparse
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
        "--output-dir", type=Path, default=OUTPUT_DIR, help="Directorio de exportaciones PNG y PDF"
    )
    args = parser.parse_args()
    QLocale.setDefault(QLocale("es_MX"))
    app = QApplication(sys.argv)
    translator = QTranslator(app)
    translations = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load("qtbase_es", translations):
        app.installTranslator(translator)
    app.setApplicationName("Graph Visualizer · Caminos mínimos")
    app.setStyle("Fusion")
    try:
        initialize_graph_data(args.data_dir)
        window = MainWindow(args.data_dir, args.output_dir)
    except (OSError, ValueError) as error:
        QMessageBox.critical(None, "No se pudieron cargar los datos del grafo", str(error))
        return 1
    window.show()
    return app.exec()
