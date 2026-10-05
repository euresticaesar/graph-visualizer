import os
import subprocess
import sys


def test_localized_entry_point_starts_from_another_directory(tmp_path):
    script = """
from PySide6.QtCore import QLocale, QTimer
from PySide6.QtWidgets import QApplication
from dijkstra_visualizer import main
original_exec = QApplication.exec

def short_event_loop(self):
    assert QLocale().name() == "es_MX"
    assert self.translate("QPlatformTheme", "Cancel") == "Cancelar"
    QTimer.singleShot(10, self.quit)
    return original_exec()

QApplication.exec = short_event_loop
assert main() == 0
print("startup-ok")
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "startup-ok" in result.stdout
