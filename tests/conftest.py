import os
import shutil
from pathlib import Path

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
    from graph_visualizer.ui.main_window import MainWindow

    data_dir = tmp_path / "data"
    shutil.copytree(Path(__file__).parent / "fixtures" / "sample", data_dir)
    window = MainWindow(data_dir, tmp_path / "output")
    window.show()
    qapp.processEvents()
    yield window
    wait_idle(window)
    window.close()
    window.deleteLater()
    qapp.processEvents()


def wait_idle(window):
    from PySide6.QtCore import QElapsedTimer
    from PySide6.QtTest import QTest

    timer = QElapsedTimer()
    timer.start()
    while window.busy and timer.elapsed() < 30000:
        QTest.qWait(10)
    assert not window.busy
