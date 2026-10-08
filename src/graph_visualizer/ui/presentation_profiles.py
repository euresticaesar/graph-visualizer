"""Named, portable profiles for UI and exported slides."""

from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from graph_visualizer.io.presentation_profiles import (
    profile_document,
    read_profile,
    write_profile,
)
from graph_visualizer.ui.accessibility import MessageLabel


class PresentationProfilesDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.directory = owner.data_dir / "presentation_profiles"
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle("Perfiles de presentación")
        self.resize(520, 360)
        column = QVBoxLayout(self)
        hint = QLabel(
            "Guarda y comparte colores, distribución, tipografía y opciones de exportación. "
            "Cada perfil conserva tu grafo y el paso actual."
        )
        hint.setWordWrap(True)
        column.addWidget(hint)
        self.profiles = QComboBox()
        self.profiles.setObjectName("presentationProfiles")
        self.profiles.setAccessibleName("Perfil de presentación guardado")
        self.name = QLineEdit()
        self.name.setMaxLength(80)
        self.name.setAccessibleName("Nombre del perfil")
        form = QFormLayout()
        form.addRow("Perfil", self.profiles)
        form.addRow("Nombre", self.name)
        column.addLayout(form)
        actions = QGridLayout()
        for index, (label, callback) in enumerate(
            (
                ("Aplicar perfil", self.apply_profile),
                ("Guardar configuración actual", self.save_profile),
                ("Renombrar", self.rename_profile),
                ("Eliminar", self.delete_profile),
                ("Importar JSON", self.import_profile),
                ("Exportar JSON", self.export_profile),
            )
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, cb=callback: self.perform(cb))
            actions.addWidget(button, index // 2, index % 2)
        column.addLayout(actions)
        self.message = MessageLabel()
        self.message.setWordWrap(True)
        self.message.setTextFormat(Qt.TextFormat.PlainText)
        self.message.setAccessibleName("Resultado de la operación del perfil")
        column.addWidget(self.message)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        column.addWidget(buttons)
        self.profiles.currentIndexChanged.connect(self.select_profile)
        self.refresh()

    def perform(self, callback):
        if self.owner.busy:
            return
        try:
            callback()
        except (OSError, ValueError) as error:
            self.message.setText(str(error))

    def refresh(self, selected=None):
        selected = selected or self.profiles.currentData()
        self.profiles.clear()
        for path in sorted(self.directory.glob("*.json")):
            try:
                document = read_profile(path)
            except (OSError, ValueError):
                continue
            self.profiles.addItem(document["name"], path)
        index = self.profiles.findData(selected)
        if index >= 0:
            self.profiles.setCurrentIndex(index)
        self.select_profile()

    def select_profile(self):
        if self.profiles.currentData():
            self.name.setText(self.profiles.currentText())

    def selected(self):
        path = self.profiles.currentData()
        if path is None:
            raise ValueError("Guarda o importa un perfil primero.")
        return path

    def save_profile(self):
        self.owner.persist_preferences()
        document = profile_document(self.name.text(), self.owner.preferences)
        path = self.directory / f"{uuid4().hex}.json"
        write_profile(path, document)
        self.refresh(path)
        self.message.setText("Configuración guardada como perfil.")

    def apply_profile(self):
        document = read_profile(self.selected())
        self.owner.apply_presentation_profile(document)
        self.message.setText(f"Perfil aplicado: {document['name']}.")

    def rename_profile(self):
        path = self.selected()
        document = read_profile(path)
        document["name"] = self.name.text()
        write_profile(path, document)
        self.refresh(path)
        self.message.setText("Perfil renombrado.")

    def delete_profile(self):
        path = self.selected()
        if (
            QMessageBox.question(
                self, "Eliminar perfil", f"¿Eliminar {self.profiles.currentText()}?"
            )
            == QMessageBox.StandardButton.Yes
        ):
            path.unlink()
            self.refresh()
            self.message.setText("Perfil eliminado.")

    def import_profile(self):
        filename, _ = QFileDialog.getOpenFileName(
            self, "Importar perfil de presentación", "", "JSON (*.json)"
        )
        if filename:
            document = read_profile(Path(filename))
            path = self.directory / f"{uuid4().hex}.json"
            write_profile(path, document)
            self.refresh(path)
            self.message.setText("Perfil importado; pulsa Aplicar perfil para usarlo.")

    def export_profile(self):
        document = read_profile(self.selected())
        filename, _ = QFileDialog.getSaveFileName(
            self, "Exportar perfil de presentación", "perfil-presentacion.json", "JSON (*.json)"
        )
        if filename:
            write_profile(Path(filename), document)
            self.message.setText("Perfil exportado.")
