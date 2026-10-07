from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QInputDialog,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from graph_visualizer.core.graph import graphs_equal
from graph_visualizer.io.presets import Preset, new_preset_path, read_preset, write_preset
from graph_visualizer.ui.node_combo_box import sorted_node_ids
from graph_visualizer.ui.section_card import SectionCard


class PresetControls:
    def build_presets(self):
        self.preset_path = None
        self.preset_baseline = None
        self.personal_presets = self.data_dir / "presets"
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(12)
        library = SectionCard("Biblioteca", "Carga un ejemplo o un preset personal.")
        self.preset_combo = QComboBox()
        self.preset_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        self.preset_combo.setMinimumContentsLength(12)
        self.preset_combo.currentTextChanged.connect(self.preset_combo.setToolTip)
        library.content.addWidget(self.preset_combo)
        load = QPushButton("Cargar preset")
        load.setObjectName("primary")
        load.clicked.connect(lambda: self.preset_action(self.load_selected_preset))
        library.content.addWidget(load)
        layout.addWidget(library)
        for title, description, actions in [
            (
                "Guardar trabajo",
                "El autoguardado del grafo es independiente del preset.",
                [
                    ("Guardar como nuevo", self.save_new_preset),
                    ("Actualizar preset", self.update_preset),
                ],
            ),
            (
                "Organizar biblioteca",
                "Duplica los ejemplos incluidos para personalizarlos.",
                [
                    ("Renombrar", self.rename_preset),
                    ("Duplicar", self.duplicate_preset),
                    ("Eliminar", self.delete_preset),
                ],
            ),
            (
                "Compartir JSON",
                "Importa un preset o exporta el trabajo actual.",
                [
                    ("Importar JSON", self.import_preset),
                    ("Exportar JSON", self.export_preset),
                ],
            ),
        ]:
            card = SectionCard(title, description)
            buttons = QGridLayout()
            for index, (text, callback) in enumerate(actions):
                button = QPushButton(text)
                if text == "Eliminar":
                    button.setObjectName("destructive")
                button.clicked.connect(lambda checked=False, cb=callback: self.preset_action(cb))
                if title == "Guardar trabajo":
                    buttons.addWidget(button, index, 0)
                else:
                    buttons.addWidget(button, index // 2, index % 2)
            card.content.addLayout(buttons)
            layout.addWidget(card)
        layout.addStretch()
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

    def remember_preset(self):
        snapshot = self.history[self.history_index]
        snapshot.preset_path = self.preset_path
        snapshot.preset_baseline = self.preset_baseline

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
        self.remember_preset()
        self.refresh_presets()
        self.preset_combo.setCurrentIndex(self.preset_combo.findData(path))
        return True

    def update_preset(self):
        if self.preset_path is None or self.preset_path.parent != self.personal_presets:
            return self.save_new_preset()
        name = read_preset(self.preset_path).name
        write_preset(self.preset_path, self.current_preset(name))
        self.preset_baseline = self.preset_fingerprint()
        self.remember_preset()
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
        ordered = sorted_node_ids(preset.graph)
        snapshot.start = preset.settings.get("start", ordered[0])
        snapshot.target = preset.settings.get("target", ordered[-1])
        if snapshot.start not in preset.graph:
            snapshot.start = ordered[0]
        if snapshot.target not in preset.graph:
            snapshot.target = ordered[-1]
        if not self._commit_edit(snapshot):
            # Identical graph is a successful load; a failed write is not.
            if (
                not graphs_equal(self.graph, preset.graph)
                or self.graph_view.positions() != preset.positions
            ):
                return False
        if hasattr(self, "algorithm_combo"):
            self.algorithm_combo.setCurrentText(preset.settings.get("algorithm", "Dijkstra"))
            self.detail_checkbox.setChecked(preset.settings.get("detail", True) is True)
        self.preset_path = path
        self.preset_baseline = self.preset_fingerprint()
        self.remember_preset()
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
                self.remember_preset()
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
