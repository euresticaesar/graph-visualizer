"""Export options and cooperative previews of the number of output images."""

from PySide6.QtCore import QElapsedTimer, Qt
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from graph_visualizer.export.image_exporter import ExportKind
from graph_visualizer.ui.section_card import SectionCard


class ExportControls:
    def _export_controls(self) -> QWidget:
        page = QWidget()
        controls = QVBoxLayout(page)
        controls.setContentsMargins(0, 4, 0, 4)
        controls.setSpacing(12)
        options = SectionCard("Exportación", "Diapositivas horizontales de 1920 × 1080.")
        self.export_format = QComboBox()
        self.export_format.addItem("Imágenes PNG", "png")
        self.export_format.addItem("Documento PDF", "pdf")
        self.export_style = QComboBox()
        self.export_style.addItems(["Didáctico", "Simple (solo grafo)"])
        self.export_detail = QComboBox()
        self.export_detail.addItems(["Detalle visible", "Resumen", "Subpasos"])
        form = QFormLayout()
        form.addRow("Formato", self.export_format)
        form.addRow("Estilo", self.export_style)
        form.addRow("Pasos", self.export_detail)
        options.content.addLayout(form)
        self.export_description = QLabel()
        self.export_description.setObjectName("hint")
        self.export_description.setWordWrap(True)
        options.content.addWidget(self.export_description)
        controls.addWidget(options)
        images = SectionCard("Qué exportar")
        buttons = QGridLayout()
        self.export_actions: list[QAction] = []
        self.export_buttons: list[QToolButton] = []
        self.export_count_labels: dict[ExportKind, QLabel] = {}
        for index, (label, kind) in enumerate(
            [
                ("Paso actual", "current"),
                ("Pasos separados", "all"),
                ("Conjuntas", "combined"),
                ("Resultado final", "final"),
            ]
        ):
            action = self._action(label, lambda checked=False, kind=kind: self.export(kind))
            action.setToolTip("Inicia un algoritmo para exportar imágenes")
            self.export_actions.append(action)
            button = self._action_button(action)
            self.export_buttons.append(button)
            choice = QWidget()
            column = QVBoxLayout(choice)
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(4)
            column.addWidget(button)
            count_label = QLabel("—")
            count_label.setObjectName("hint")
            count_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.export_count_labels[kind] = count_label
            column.addWidget(count_label)
            buttons.addWidget(choice, index // 2, index % 2)
        images.content.addLayout(buttons)
        self.export_summary = QLabel()
        self.export_summary.setObjectName("hint")
        self.export_summary.setWordWrap(True)
        images.content.addWidget(self.export_summary)
        self.preview_before_export = QCheckBox("Mostrar vista previa antes de exportar")
        self.preview_before_export.setChecked(True)
        self.preview_before_export.setToolTip(
            "Revisa hasta dos imágenes o páginas y confirma antes de crear los archivos."
        )
        images.content.addWidget(self.preview_before_export)
        controls.addWidget(images)
        destination = SectionCard("Archivos generados", "Cada exportación crea su propia carpeta.")
        self.output_button = QPushButton("Abrir carpeta de exportaciones")
        self.output_button.clicked.connect(self.open_output_folder)
        destination.content.addWidget(self.output_button)
        controls.addWidget(destination)
        controls.addStretch()
        self.export_format.currentIndexChanged.connect(self.refresh_export_preview)
        self.export_style.currentIndexChanged.connect(self.refresh_export_preview)
        self.export_detail.currentIndexChanged.connect(self.refresh_export_preview)
        return page

    def _export_states(self):
        from graph_visualizer.core.models import StateView

        mode = self.export_detail.currentIndex()
        if self.states and mode and self.algorithm_combo.currentText() != "Bellman-Ford":
            return StateView(self.states.events, mode == 2)
        return self.states

    def _export_preview_key(self, states):
        return (
            id(states.events),
            len(states),
            self.start,
            self.target,
            self.export_style.currentIndex(),
            self.graph_view.show_state_labels,
            self.graph_view.show_edge_ids,
        )

    def _image_count_text(self, count: int) -> str:
        if self.export_format.currentData() == "pdf":
            return f"{count} página" if count == 1 else f"{count} páginas"
        return f"{count} imagen" if count == 1 else f"{count} imágenes"

    def cancel_export_preview(self) -> None:
        self.export_preview_timer.stop()
        if self.export_preview_job is not None:
            self.export_preview_job.close()
            self.export_preview_job = None

    def refresh_export_preview(self) -> None:
        self.cancel_export_preview()
        self.export_description.setText(
            "Solo el grafo, con pesos y resaltados."
            if self.export_style.currentIndex() == 1
            else "Grafo, explicación y leyenda; incluye las tablas del algoritmo."
        )
        if not self.states:
            for label in self.export_count_labels.values():
                label.setText("—")
                label.setToolTip("")
            self.export_summary.setText("Inicia un algoritmo para conocer la cantidad de imágenes.")
            return
        states = self._export_states()
        for kind, count in (("current", 1), ("final", 1), ("all", len(states))):
            self.export_count_labels[kind].setText(self._image_count_text(count))
        detailed = self.export_detail.currentIndex() == 2 or (
            self.export_detail.currentIndex() == 0 and self.detail_checkbox.isChecked()
        )
        detail = (
            "un paso por arco"
            if self.algorithm_combo.currentText() == "Bellman-Ford"
            else "por comparación"
            if detailed
            else "resumen"
        )
        self.export_summary.setText(
            f"{len(states)} pasos · {detail}. Las conjuntas agrupan hasta 4 pasos por diapositiva."
        )
        key = self._export_preview_key(states)
        combined_label = self.export_count_labels["combined"]
        if key in self.export_preview_cache:
            combined_label.setText(self._image_count_text(self.export_preview_cache[key]))
            combined_label.setToolTip("Cantidad calculada según el tamaño de los pasos.")
            return
        combined_label.setText("Calculando…")
        if self.tabs.currentIndex() != 3 or self.busy:
            return
        from graph_visualizer.export.image_exporter import combined_image_count_job

        self.export_preview_job = combined_image_count_job(
            self.graph,
            self.graph_view.positions(),
            states,
            self.start,
            self.target,
            simple=self.export_style.currentIndex() == 1,
            show_state_labels=self.graph_view.show_state_labels,
            show_edge_ids=self.graph_view.show_edge_ids,
        )
        self.export_preview_key = key
        self.export_preview_total = len(states)
        self.export_preview_timer.start(0)

    def advance_export_preview(self) -> None:
        if self.export_preview_job is None:
            return
        budget = QElapsedTimer()
        budget.start()
        try:
            while budget.elapsed() < 12:
                progress, _pages = next(self.export_preview_job)
                self.export_count_labels["combined"].setToolTip(
                    f"Midiendo paso {progress} de {self.export_preview_total}."
                )
        except StopIteration as result:
            self.cancel_export_preview()
            if len(self.export_preview_cache) >= 32:
                self.export_preview_cache.clear()
            self.export_preview_cache[self.export_preview_key] = result.value
            self.export_count_labels["combined"].setText(self._image_count_text(result.value))
            self.export_count_labels["combined"].setToolTip(
                "Cantidad calculada según el tamaño de los pasos."
            )
        except (ValueError, OverflowError) as error:
            self.cancel_export_preview()
            self.export_count_labels["combined"].setText("No disponible")
            self.export_count_labels["combined"].setToolTip(str(error))

    def show_export_sample(self, kind="current"):
        if not self.states or self.busy:
            return
        from itertools import islice

        from graph_visualizer.export.image_exporter import export_frames

        self.stop_playback()
        states = self._export_states()
        index = states.equivalent(self.states[self.state_index].step)
        frames = export_frames(
            self.graph,
            self.graph_view.positions(),
            states,
            self.start,
            self.target,
            index,
            kind,
            simple=self.export_style.currentIndex() == 1,
            show_state_labels=self.graph_view.show_state_labels,
            show_edge_ids=self.graph_view.show_edge_ids,
        )
        try:
            samples = list(islice((image for image, *_ in frames if image is not None), 2))
        except (ValueError, OSError, OverflowError) as error:
            QMessageBox.warning(self, "No se pudo generar la vista previa", str(error))
            return
        finally:
            frames.close()
        dialog = QDialog(self)
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        is_pdf = self.export_format.currentData() == "pdf"
        dialog.setWindowTitle("Vista previa del PDF" if is_pdf else "Vista previa de exportación")
        dialog.setWindowModality(Qt.WindowModality.WindowModal)
        dialog.resize(1000, 700)
        layout = QVBoxLayout(dialog)
        hint = QLabel(
            "Muestra de hasta 2 páginas del PDF con la configuración actual. "
            "Cada imagen ocupará una página horizontal completa, sin márgenes."
            if is_pdf
            else "Muestra de hasta 2 imágenes con la configuración actual. "
            "La exportación usa estas mismas imágenes a 1920 × 1080."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        column = QVBoxLayout(content)
        for page, image in enumerate(samples, start=1):
            caption = QLabel(f"{'Página' if is_pdf else 'Imagen'} {page} de la muestra")
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            column.addWidget(caption)
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setPixmap(
                QPixmap.fromImage(image).scaledToWidth(
                    900, Qt.TransformationMode.SmoothTransformation
                )
            )
            column.addWidget(label)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(dialog.reject)
        buttons.addWidget(cancel)
        confirm = QPushButton("Exportar PDF" if is_pdf else "Exportar imágenes")
        confirm.setObjectName("confirmExport")
        confirm.setDefault(True)
        confirm.clicked.connect(dialog.accept)
        buttons.addWidget(confirm)
        layout.addLayout(buttons)
        dialog.accepted.connect(lambda: self.export(kind, preview_confirmed=True))
        dialog.open()
