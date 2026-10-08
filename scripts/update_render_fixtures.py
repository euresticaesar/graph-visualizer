"""Regenerate the controlled slide references after reviewing a renderer change."""

import os
import runpy
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
app.setStyle("Fusion")
root = Path(__file__).resolve().parents[1]
reference = runpy.run_path(str(root / "tests/render_reference.py"))
with reference["reference_font"]():
    reference["update_references"](root / "tests/fixtures/render")
print("Referencias actualizadas en tests/fixtures/render; revisa las imágenes antes de commit.")
