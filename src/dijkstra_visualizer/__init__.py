def main() -> int:
    import sys

    from PySide6.QtWidgets import QApplication, QMessageBox

    from dijkstra_visualizer.ui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName("Dijkstra Visualizer")
    app.setStyle("Fusion")
    try:
        window = MainWindow()
    except (OSError, ValueError) as error:
        QMessageBox.critical(None, "Unable to load graph data", str(error))
        return 1
    window.show()
    return app.exec()
