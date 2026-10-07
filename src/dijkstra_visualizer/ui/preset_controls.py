from pathlib import Path

import networkx as nx
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QWidget,
)

from dijkstra_visualizer.io.presets import Preset, new_preset_path, read_preset, write_preset


class PresetControls:
    def build_presets(self):
        self.preset_path = None
        self.preset_baseline = None
        self.personal_presets = self.data_dir / "presets"
        page = QWidget()
        layout = QGridLayout(page)
        layout.addWidget(QLabel("Presets locales · el trabajo se guarda aparte"), 0, 0, 1, 2)
        self.preset_combo = QComboBox()
        layout.addWidget(self.preset_combo, 1, 0, 1, 2)
        for i, (text, callback) in enumerate(
            [
                ("Cargar", self.load_selected_preset),
                ("Guardar como nuevo", self.save_new_preset),
                ("Actualizar preset", self.update_preset),
                ("Renombrar", self.rename_preset),
                ("Duplicar", self.duplicate_preset),
                ("Eliminar", self.delete_preset),
                ("Importar JSON", self.import_preset),
                ("Exportar JSON", self.export_preset),
            ]
        ):
            button = QPushButton(text)
            button.clicked.connect(lambda checked=False, cb=callback: self.preset_action(cb))
            layout.addWidget(button, 2 + i // 2, i % 2)
        self.refresh_presets()
        return page

    def preset_action(self, callback):
        try:
            callback()
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "No se pudo completar el preset", str(error))

    def current_preset(self, name="Trabajo actual"):
        settings = {"start": self.start, "target": self.target}
        if hasattr(self, "algorithm_combo"):
            settings.update(
                algorithm=self.algorithm_combo.currentText(),
                detail=self.detail_checkbox.isChecked(),
            )
        return Preset(name, self.graph.copy(), self.graph_view.positions(), settings)

    def preset_fingerprint(self):
        document = self.current_preset().document()
        document.pop("name")
        return document

    def refresh_presets(self):
        selected = self.preset_combo.currentData()
        self.preset_combo.clear()
        examples = Path(__file__).resolve().parents[1] / "examples"
        for directory, prefix in [(examples, "Ejemplo"), (self.personal_presets, "Personal")]:
            for path in sorted(directory.glob("*.json")):
                try:
                    preset = read_preset(path)
                    self.preset_combo.addItem(f"{prefix}: {preset.name}", path)
                except (ValueError, OSError):
                    self.preset_combo.addItem(f"Archivo no válido: {path.name}", path)
        index = self.preset_combo.findData(selected)
        if index >= 0:
            self.preset_combo.setCurrentIndex(index)

    def save_new_preset(self):
        name, ok = QInputDialog.getText(self, "Guardar preset", "Nombre:")
        if not ok or not name.strip():
            return False
        path = new_preset_path(self.personal_presets)
        write_preset(path, self.current_preset(name))
        self.preset_path = path
        self.preset_baseline = self.preset_fingerprint()
        self.refresh_presets()
        self.preset_combo.setCurrentIndex(self.preset_combo.findData(path))
        return True

    def update_preset(self):
        if self.preset_path is None or self.preset_path.parent != self.personal_presets:
            return self.save_new_preset()
        name = read_preset(self.preset_path).name
        write_preset(self.preset_path, self.current_preset(name))
        self.preset_baseline = self.preset_fingerprint()
        return True

    def load_selected_preset(self):
        path = self.preset_combo.currentData()
        if path is not None:
            self.load_preset_path(path)

    def load_preset_path(self, path):
        # Validate before prompting or altering the current graph.
        preset = read_preset(path)
        if self.preset_fingerprint() != self.preset_baseline:
            dialog = QMessageBox(self)
            dialog.setWindowTitle("Cambios del trabajo actual")
            dialog.setText("Hay cambios sin guardar en preset. El autoguardado es independiente.")
            save = dialog.addButton("Guardar y continuar", QMessageBox.ButtonRole.AcceptRole)
            skip = dialog.addButton(
                "Continuar sin guardar en preset", QMessageBox.ButtonRole.DestructiveRole
            )
            dialog.addButton("Cancelar", QMessageBox.ButtonRole.RejectRole)
            dialog.exec()
            if dialog.clickedButton() == save:
                if not self.update_preset():
                    return False
            elif dialog.clickedButton() != skip:
                return False
        self.reset()
        snapshot = self._snapshot(f"Cargar preset {preset.name}")
        snapshot.graph, snapshot.positions = preset.graph.copy(), dict(preset.positions)
        snapshot.start = preset.settings.get("start", min(preset.graph))
        snapshot.target = preset.settings.get("target", max(preset.graph))
        if snapshot.start not in preset.graph:
            snapshot.start = min(preset.graph)
        if snapshot.target not in preset.graph:
            snapshot.target = max(preset.graph)
        if not self._commit_edit(snapshot):
            # Identical graph is a successful load; a failed write is not.
            if (
                not nx.utils.graphs_equal(self.graph, preset.graph)
                or self.graph_view.positions() != preset.positions
            ):
                return False
        if hasattr(self, "algorithm_combo"):
            self.algorithm_combo.setCurrentText(preset.settings.get("algorithm", "Dijkstra"))
            self.detail_checkbox.setChecked(preset.settings.get("detail", True) is True)
        self.preset_path = path
        self.preset_baseline = self.preset_fingerprint()
        self.graph_view.fit_graph()
        return True

    def rename_preset(self):
        path = self.preset_combo.currentData()
        if path is None:
            return
        if path.parent != self.personal_presets:
            raise ValueError("Duplica el ejemplo para crear una copia personal.")
        preset = read_preset(path)
        name, ok = QInputDialog.getText(self, "Renombrar preset", "Nombre:", text=preset.name)
        if ok and name.strip():
            preset.name = name.strip()
            write_preset(path, preset)
            self.refresh_presets()

    def duplicate_preset(self):
        path = self.preset_combo.currentData()
        if path:
            preset = read_preset(path)
            preset.name += " (copia)"
            write_preset(new_preset_path(self.personal_presets), preset)
            self.refresh_presets()

    def delete_preset(self):
        path = self.preset_combo.currentData()
        if path is None:
            return
        if path.parent != self.personal_presets:
            raise ValueError("Los ejemplos incluidos son de solo lectura.")
        if (
            QMessageBox.question(self, "Eliminar preset", f"¿Eliminar {read_preset(path).name}?")
            == QMessageBox.StandardButton.Yes
        ):
            path.unlink()
            if self.preset_path == path:
                self.preset_path = None
            self.refresh_presets()

    def import_preset(self):
        name, _ = QFileDialog.getOpenFileName(self, "Importar preset", "", "JSON (*.json)")
        if name:
            preset = read_preset(Path(name))
            write_preset(new_preset_path(self.personal_presets), preset)
            self.refresh_presets()

    def export_preset(self):
        name, _ = QFileDialog.getSaveFileName(
            self, "Exportar trabajo como preset", "grafo.json", "JSON (*.json)"
        )
        if name:
            write_preset(Path(name), self.current_preset())
