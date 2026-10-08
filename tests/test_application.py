import os
import subprocess
import sys


def test_localized_entry_point_starts_from_another_directory(tmp_path):
    script = """
from PySide6.QtCore import QLocale, QTimer
from PySide6.QtWidgets import QApplication
from graph_visualizer import main
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
        env={
            **os.environ,
            "QT_QPA_PLATFORM": "offscreen",
            "GRAPH_VISUALIZER_DATA_DIR": str(tmp_path / "data"),
            "GRAPH_VISUALIZER_OUTPUT_DIR": str(tmp_path / "output"),
        },
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    assert "startup-ok" in result.stdout


def test_new_console_command_help_and_packaged_examples(tmp_path):
    import shutil
    from importlib.metadata import distribution

    command = shutil.which("graph-visualizer")
    assert command is not None
    result = subprocess.run(
        [command, "--help"], cwd=tmp_path, capture_output=True, text=True, check=True
    )
    assert "--data-dir" in result.stdout and "Bellman-Ford" in result.stdout
    assert distribution("graph-visualizer").version == "0.3.0"
