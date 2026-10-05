def main() -> int:
    import sys

    from PySide6.QtCore import QLibraryInfo, QLocale, QTranslator
    from PySide6.QtWidgets import QApplication, QMessageBox

    from dijkstra_visualizer.ui.main_window import MainWindow

    QLocale.setDefault(QLocale(QLocale.Language.Spanish, QLocale.Territory.Mexico))
    app = QApplication(sys.argv)
    translator = QTranslator(app)
    translations = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    if translator.load("qtbase_es", translations):
        app.installTranslator(translator)
    app.setApplicationName("Visualizador de Dijkstra")
    app.setStyle("Fusion")
    try:
        window = MainWindow()
    except (OSError, ValueError) as error:
        QMessageBox.critical(None, "No se pudieron cargar los datos del grafo", str(error))
        return 1
    window.show()
    return app.exec()
