"""Export options and cooperative previews of the number of output images."""

from PySide6.QtCore import QElapsedTimer, Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QLabel,
    QPushButton,
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
        options = SectionCard("Formato PNG", "Exporta los estados del algoritmo iniciado.")
        self.export_style = QComboBox()
        self.export_style.addItems(["Didáctico", "Simple (solo grafo)"])
        self.export_detail = QComboBox()
        self.export_detail.addItems(["Detalle visible", "Resumen", "Subpasos"])
        form = QFormLayout()
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
        controls.addWidget(images)
        destination = SectionCard("Archivos generados", "Cada exportación crea su propia carpeta.")
        self.output_button = QPushButton("Abrir carpeta de exportaciones")
        self.output_button.clicked.connect(self.open_output_folder)
        destination.content.addWidget(self.output_button)
        controls.addWidget(destination)
        controls.addStretch()
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

    @staticmethod
    def _image_count_text(count: int) -> str:
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
            f"{len(states)} pasos · {detail}. Las conjuntas agrupan hasta 4 pasos por imagen."
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
