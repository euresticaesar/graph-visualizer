import os
import shutil

import pytest

os.environ["QT_QPA_PLATFORM"] = "offscreen"


@pytest.fixture(scope="session")
def qapp():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    return app


@pytest.fixture
def window(qapp, tmp_path):
    from dijkstra_visualizer.paths import DATA_DIR
    from dijkstra_visualizer.ui.main_window import MainWindow

    data_dir = tmp_path / "data"
    shutil.copytree(DATA_DIR, data_dir)
    window = MainWindow(data_dir, tmp_path / "output")
    window.show()
    qapp.processEvents()
    yield window
    window.close()
    window.deleteLater()
    qapp.processEvents()
