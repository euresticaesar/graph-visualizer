"""Export customization, selection and a zoomable, paged preview."""

from dataclasses import replace

from PySide6.QtCore import QEvent, QSignalBlocker, Qt, QTimer
from PySide6.QtGui import QAction, QPalette, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from graph_visualizer.core.models import StateView
from graph_visualizer.export.image_exporter import ExportKind, combined_capacity
from graph_visualizer.export.slide_renderer import SlideOptions, SlideRenderer, page_count
from graph_visualizer.ui.section_card import SectionCard
from graph_visualizer.ui.themes import THEME_NAMES


class ExportPreview(QDialog):
    def __init__(self, owner, graph, positions, states, start, target, index, kind, options):
        super().__init__(owner)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.is_pdf = owner.export_format.currentData() == "pdf"
        self.setWindowTitle(
            "Vista previa del PDF" if self.is_pdf else "Vista previa de exportación"
        )
        self.resize(1030, 780)
        self.renderer = SlideRenderer(graph, positions, SlideOptions(**options))
        self.states, self.start, self.target = states, start, target
        self.source_indices = (
            range(len(states))
            if kind in {"all", "combined"}
            else [len(states) - 1 if kind == "final" else index]
        )
        self.parts = len(self.renderer.plan(states[0].algorithm))
        total = len(self.source_indices) * self.parts
        self.capacity = (
            combined_capacity(
                self.renderer.options.resolution,
                self.renderer.options.resolution * 9 // 16,
                total,
                self.renderer.options.group_size,
            )
            if kind == "combined"
            else 1
        )
        self.total_pages = (total + self.capacity - 1) // self.capacity
        self.images = []
        self.fit_timer = QTimer(self)
        self.fit_timer.setSingleShot(True)
        self.fit_timer.timeout.connect(self.refresh_zoom)
        column = QVBoxLayout(self)
        hint = QLabel(
            "Revisa cualquier página y amplía al 100 % para comprobar textos y detalles. "
            "La vista previa y los archivos comparten la misma composición."
        )
        hint.setWordWrap(True)
        column.addWidget(hint)
        self.diagnosis = QLabel()
        self.diagnosis.setObjectName("hint")
        self.diagnosis.setWordWrap(True)
        self.diagnosis.setAccessibleName("Diagnóstico de legibilidad de la exportación")
        column.addWidget(self.diagnosis)
        fixes = QHBoxLayout()
        self.use_4k = QPushButton("Usar 4K")
        self.use_4k.clicked.connect(self.set_4k)
        adjust = QPushButton("Ajustar composición")
        adjust.clicked.connect(self.adjust_composition)
        fixes.addWidget(self.use_4k)
        fixes.addWidget(adjust)
        fixes.addStretch()
        column.addLayout(fixes)
        toolbar = QHBoxLayout()
        previous, next_page, last = (
            QPushButton("Anterior"),
            QPushButton("Siguiente"),
            QPushButton("Última página"),
        )
        self.page_input = QSpinBox()
        self.page_input.setObjectName("previewPage")
        self.page_input.setRange(1, self.total_pages)
        self.page_input.setKeyboardTracking(False)
        self.page_input.setSuffix(f" / {self.total_pages}")
        self.page_input.setAccessibleName("Página de vista previa")
        self.zoom = QComboBox()
        self.zoom.setObjectName("previewZoom")
        self.zoom.addItems(["Encajar", "50 %", "100 %"])
        self.zoom.setAccessibleName("Zoom de vista previa")
        previous.clicked.connect(lambda: self.page_input.setValue(self.page_input.value() - 1))
        next_page.clicked.connect(lambda: self.page_input.setValue(self.page_input.value() + 1))
        last.clicked.connect(lambda: self.page_input.setValue(self.total_pages))
        for widget in (previous, self.page_input, next_page, last, self.zoom):
            toolbar.addWidget(widget)
        column.addLayout(toolbar)
        scroll = self.scroll = QScrollArea()
        scroll.setObjectName("previewScroll")
        scroll.setWidgetResizable(True)
        # Reserve the scrollbar width so fitting cannot toggle it on and off.
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.viewport().setBackgroundRole(QPalette.ColorRole.Window)
        scroll.viewport().setAutoFillBackground(True)
        scroll.viewport().installEventFilter(self)
        content = QWidget()
        content.setObjectName("previewContent")
        samples = QVBoxLayout(content)
        samples.setSizeConstraint(QLayout.SizeConstraint.SetMinAndMaxSize)
        samples.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.labels, self.captions = [], []
        for _ in range(2):
            caption, label = QLabel(), QLabel()
            caption.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            samples.addWidget(caption)
            samples.addWidget(label, 0, Qt.AlignmentFlag.AlignHCenter)
            self.labels.append(label)
            self.captions.append(caption)
        scroll.setWidget(content)
        column.addWidget(scroll, 1)
        buttons = QHBoxLayout()
        buttons.addStretch()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        confirm = QPushButton("Exportar PDF" if self.is_pdf else "Exportar archivos")
        confirm.setObjectName("confirmExport")
        confirm.setDefault(True)
        confirm.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(confirm)
        column.addLayout(buttons)
        self.page_input.valueChanged.connect(self.show_page)
        self.zoom.currentIndexChanged.connect(self.refresh_zoom)
        self.finished.connect(lambda _: self.renderer.close())
        self.finished.connect(self.fit_timer.stop)
        try:
            self.show_page(1)
        except Exception:
            self.renderer.close()
            raise

    def show_page(self, value):
        self.images = []
        measurements = {}
        total = len(self.source_indices) * self.parts
        for slot, page in enumerate(range(value - 1, min(value + 1, self.total_pages))):
            refs = []
            for ordinal in range(page * self.capacity, min((page + 1) * self.capacity, total)):
                refs.append((self.source_indices[ordinal // self.parts], ordinal % self.parts))
            self.images.append(self.renderer.image(refs, self.states, self.start, self.target))
            for index, _ in refs:
                for category, size in self.renderer.legibility(
                    self.states[index], self.start, self.target
                ).items():
                    measurements[category] = min(measurements.get(category, float("inf")), size)
            self.labels[slot].setAccessibleName(f"Diapositiva de vista previa {page + 1}")
            self.labels[slot].setAccessibleDescription(
                "\n".join(
                    self.renderer.explanation(self.states[index], self.start, self.target)
                    for index, _ in refs
                )
            )
            self.captions[slot].setText(
                f"{'Página' if self.is_pdf else 'Imagen'} {page + 1} de la muestra"
            )
            self.captions[slot].setToolTip(
                f"Página {page + 1} de {self.total_pages} · Pasos "
                + ", ".join(str(i) for i, _ in refs)
            )
        self.measurements = measurements
        small = [category for category, size in measurements.items() if size < 12]
        self.diagnosis.setText(
            "Tamaño mínimo del texto en esta muestra: "
            + " · ".join(f"{category}: {size:.1f} px" for category, size in measurements.items())
            + (
                ". Texto pequeño en "
                + ", ".join(small)
                + ". Revisa al 100 %, usa 4K o ajusta la composición."
                if small
                else "."
            )
            + " Al proyectar, la legibilidad también depende del tamaño de la pantalla."
        )
        self.use_4k.setEnabled(self.renderer.options.resolution != 3840)
        self.refresh_zoom()

    def set_4k(self):
        self.renderer.options = replace(self.renderer.options, resolution=3840)
        self.parent().export_resolution.setCurrentIndex(
            self.parent().export_resolution.findData(3840)
        )
        self.show_page(self.page_input.value())

    def adjust_composition(self):
        self.parent().tabs.setCurrentIndex(3)
        self.parent().export_advanced_button.setChecked(True)
        self.reject()

    def refresh_zoom(self):
        for slot, label in enumerate(self.labels):
            visible = slot < len(self.images)
            label.setVisible(visible)
            self.captions[slot].setVisible(visible)
            if visible:
                image = self.images[slot]
                width = (
                    max(200, self.scroll.viewport().width() - 40)
                    if self.zoom.currentIndex() == 0
                    else image.width() // 2
                    if self.zoom.currentIndex() == 1
                    else image.width()
                )
                if self.zoom.currentIndex() == 0:
                    width = min(width, image.width())
                pixmap = QPixmap.fromImage(image).scaledToWidth(
                    width, Qt.TransformationMode.SmoothTransformation
                )
                label.setPixmap(pixmap)
                # A resizable scroll area may otherwise compress the label vertically.
                label.setFixedSize(pixmap.size())
        self.scroll.widget().layout().activate()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "zoom") and self.zoom.currentIndex() == 0:
            self.fit_timer.start(0)

    def eventFilter(self, watched, event):
        if (
            watched is self.scroll.viewport()
            and event.type() == QEvent.Type.Resize
            and self.zoom.currentIndex() == 0
        ):
            self.fit_timer.start(0)
        return super().eventFilter(watched, event)


class ExportControls:
    def _export_controls(self):
        page = QWidget()
        controls = QVBoxLayout(page)
        controls.setContentsMargins(0, 4, 0, 4)
        controls.setSpacing(12)
        options = SectionCard("Exportación", "Una diapositiva horizontal completa por paso.")
        self.export_format = QComboBox()
        for name, key in (
            ("Imágenes PNG", "png"),
            ("PDF vectorial", "pdf"),
            ("SVG vectorial", "svg"),
        ):
            self.export_format.addItem(name, key)
        self.export_style = QComboBox()
        self.export_style.addItems(["Didáctico", "Simple (solo grafo)"])
        self.export_detail = QComboBox()
        self.export_detail.addItems(["Detalle visible", "Resumen", "Subpasos"])
        self.export_theme = QComboBox()
        self.export_theme.addItem("Como la interfaz", "app")
        for key, name in THEME_NAMES.items():
            self.export_theme.addItem(name, key)
        self.export_resolution = QComboBox()
        for width in (1920, 2560, 3840):
            self.export_resolution.addItem(f"{width} × {width * 9 // 16}", width)
        self.export_layout = QComboBox()
        for name, key in (
            ("Grafo y tablas", "balanced"),
            ("Grafo destacado", "graph"),
            ("Tablas destacadas", "tables"),
        ):
            self.export_layout.addItem(name, key)
        self.export_composition = QComboBox()
        for name, key in (
            ("Adaptativa", "auto"),
            ("Grafo a la izquierda", "side"),
            ("Grafo arriba", "top"),
        ):
            self.export_composition.addItem(name, key)
        self.export_graph_fraction = QSpinBox()
        self.export_graph_fraction.setRange(20, 65)
        self.export_graph_fraction.setSingleStep(5)
        self.export_graph_fraction.setSuffix(" %")
        self.export_graph_fraction.setToolTip(
            "Porcentaje de ancho (lateral) o alto (superior) reservado al grafo."
        )
        self.export_dim_unrelated = QCheckBox("Atenuar conexiones fuera de la ruta")
        self.export_focus = QCheckBox("Ampliar comparación activa en la diapositiva")
        self.export_group = QComboBox()
        self.export_group.addItem("2 páginas", 2)
        self.export_group.addItem("4 páginas", 4)
        self.export_font_scale = QDoubleSpinBox()
        self.export_font_scale.setRange(0.8, 1.5)
        self.export_font_scale.setSingleStep(0.1)
        self.export_legend = QCheckBox("Incluir leyenda")
        self.export_explanation = QCheckBox("Incluir explicación")
        self.export_title = QLineEdit()
        self.export_title.setMaxLength(200)
        self.export_title.setPlaceholderText("Título opcional de las diapositivas")
        form = QFormLayout()
        for name, widget in (
            ("Formato", self.export_format),
            ("Estilo", self.export_style),
            ("Pasos", self.export_detail),
            ("Esquema", self.export_theme),
            ("Resolución", self.export_resolution),
        ):
            form.addRow(name, widget)
        options.content.addLayout(form)
        advanced_button = self.export_advanced_button = QToolButton()
        advanced_button.setText("Composición y tipografía")
        advanced_button.setCheckable(True)
        options.content.addWidget(advanced_button)
        advanced = QWidget()
        advanced_form = QFormLayout(advanced)
        for name, widget in (
            ("Distribución", self.export_layout),
            ("Composición", self.export_composition),
            ("Espacio del grafo", self.export_graph_fraction),
            ("Conjuntas", self.export_group),
            ("Escala de texto", self.export_font_scale),
            ("Título", self.export_title),
        ):
            advanced_form.addRow(name, widget)
        advanced_form.addRow(self.export_legend)
        advanced_form.addRow(self.export_explanation)
        advanced_form.addRow(self.export_dim_unrelated)
        advanced_form.addRow(self.export_focus)
        advanced.hide()
        advanced_button.toggled.connect(advanced.setVisible)
        options.content.addWidget(advanced)
        self.export_description = QLabel()
        self.export_description.setObjectName("hint")
        self.export_description.setWordWrap(True)
        options.content.addWidget(self.export_description)
        controls.addWidget(options)

        selection = SectionCard("Seleccionar pasos")
        self.export_selection = QComboBox()
        self.export_selection.addItems(["Todos", "Rango", "Solo mejoras", "Pasos marcados"])
        self.export_from, self.export_to = QSpinBox(), QSpinBox()
        for widget in (self.export_from, self.export_to):
            widget.setKeyboardTracking(False)
        selection_form = QFormLayout()
        selection_form.addRow("Selección", self.export_selection)
        selection_form.addRow("Desde", self.export_from)
        selection_form.addRow("Hasta", self.export_to)
        selection.content.addLayout(selection_form)
        controls.addWidget(selection)
        images = SectionCard("Qué exportar")
        buttons = QGridLayout()
        self.export_actions: list[QAction] = []
        self.export_buttons: list[QToolButton] = []
        self.export_count_labels: dict[ExportKind, QLabel] = {}
        for index, (label, kind) in enumerate(
            (
                ("Paso actual", "current"),
                ("Pasos separados", "all"),
                ("Conjuntas", "combined"),
                ("Resultado final", "final"),
            )
        ):
            action = self._action(label, lambda checked=False, kind=kind: self.export(kind))
            action.setToolTip("Inicia un algoritmo para exportar")
            self.export_actions.append(action)
            button = self._action_button(action)
            self.export_buttons.append(button)
            choice = QWidget()
            column = QVBoxLayout(choice)
            column.setContentsMargins(0, 0, 0, 0)
            column.addWidget(button)
            label = QLabel("—")
            label.setObjectName("hint")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.export_count_labels[kind] = label
            column.addWidget(label)
            buttons.addWidget(choice, index // 2, index % 2)
        images.content.addLayout(buttons)
        self.export_summary = QLabel()
        self.export_summary.setObjectName("hint")
        self.export_summary.setWordWrap(True)
        images.content.addWidget(self.export_summary)
        self.preview_before_export = QCheckBox("Mostrar vista previa antes de exportar")
        images.content.addWidget(self.preview_before_export)
        controls.addWidget(images)
        destination = SectionCard(
            "Archivos generados",
            "Cada carpeta incluye el grafo y un manifiesto para identificar "
            "y reproducir sus páginas.",
        )
        self.output_button = QPushButton("Abrir carpeta de exportaciones")
        self.output_button.clicked.connect(self.open_output_folder)
        destination.content.addWidget(self.output_button)
        controls.addWidget(destination)
        controls.addStretch()
        self.restore_export_preferences()
        for widget in (
            self.export_format,
            self.export_style,
            self.export_detail,
            self.export_theme,
            self.export_resolution,
            self.export_layout,
            self.export_composition,
            self.export_group,
            self.export_selection,
        ):
            widget.currentIndexChanged.connect(self.refresh_export_preview)
        for widget in (
            self.export_from,
            self.export_to,
            self.export_font_scale,
            self.export_graph_fraction,
        ):
            widget.valueChanged.connect(self.refresh_export_preview)
        self.export_title.editingFinished.connect(self.refresh_export_preview)
        self.export_legend.toggled.connect(self.refresh_export_preview)
        self.export_explanation.toggled.connect(self.refresh_export_preview)
        self.export_dim_unrelated.toggled.connect(self.refresh_export_preview)
        self.export_focus.toggled.connect(self.refresh_export_preview)
        return page

    def restore_export_preferences(self):
        for key, widget in (
            ("export_format", self.export_format),
            ("export_theme", self.export_theme),
            ("export_resolution", self.export_resolution),
            ("export_layout", self.export_layout),
            ("export_composition", self.export_composition),
            ("export_group", self.export_group),
        ):
            widget.setCurrentIndex(widget.findData(self.preferences[key]))
        self.export_style.setCurrentIndex(self.preferences["export_style"])
        self.export_detail.setCurrentIndex(self.preferences["export_detail"])
        self.export_font_scale.setValue(self.preferences["export_font_scale"])
        self.export_graph_fraction.setValue(round(100 * self.preferences["export_graph_fraction"]))
        self.export_dim_unrelated.setChecked(self.preferences["export_dim_unrelated"])
        self.export_focus.setChecked(self.preferences["export_focus"])
        self.export_title.setText(self.preferences["export_title"])
        self.export_legend.setChecked(self.preferences["export_legend"])
        self.export_explanation.setChecked(self.preferences["export_explanation"])
        self.preview_before_export.setChecked(self.preferences["preview_before_export"])

    def collect_export_preferences(self):
        for key in (
            "export_format",
            "export_theme",
            "export_resolution",
            "export_layout",
            "export_composition",
            "export_group",
        ):
            self.preferences[key] = getattr(self, key).currentData()
        self.preferences.update(
            export_style=self.export_style.currentIndex(),
            export_detail=self.export_detail.currentIndex(),
            export_font_scale=self.export_font_scale.value(),
            export_graph_fraction=self.export_graph_fraction.value() / 100,
            export_dim_unrelated=self.export_dim_unrelated.isChecked(),
            export_focus=self.export_focus.isChecked(),
            export_legend=self.export_legend.isChecked(),
            export_explanation=self.export_explanation.isChecked(),
            export_title=self.export_title.text(),
            preview_before_export=self.preview_before_export.isChecked(),
        )

    def export_options(self):
        theme = self.export_theme.currentData()
        return dict(
            simple=self.export_style.currentIndex() == 1,
            show_state_labels=self.graph_view.show_state_labels,
            show_edge_ids=self.graph_view.show_edge_ids,
            theme=self.preferences["theme"] if theme == "app" else theme,
            accent=self.preferences["accent"] if theme == "app" else "",
            resolution=self.export_resolution.currentData(),
            font_scale=self.export_font_scale.value(),
            graph_font_scale=self.preferences["graph_font_scale"],
            layout=self.export_layout.currentData(),
            composition=self.export_composition.currentData(),
            graph_fraction=self.export_graph_fraction.value() / 100,
            dim_unrelated=self.export_dim_unrelated.isChecked(),
            show_focus=self.export_focus.isChecked(),
            group_size=self.export_group.currentData(),
            show_legend=self.export_legend.isChecked(),
            show_explanation=self.export_explanation.isChecked(),
            title=self.export_title.text(),
        )

    def _export_states(self, kind=None):
        if kind in {"current", "final"}:
            return self.states
        mode = self.export_detail.currentIndex()
        states = (
            StateView(self.states.events, mode == 2)
            if self.states and mode and self.algorithm_combo.currentText() != "Bellman-Ford"
            else self.states
        )
        if not states or self.export_selection.currentIndex() == 0:
            return states
        selection = self.export_selection.currentIndex()
        selected = []
        for i, state in enumerate(states):
            keep = (
                self.export_from.value() <= i <= self.export_to.value()
                if selection == 1
                else (
                    i in {0, len(states) - 1}
                    or state.updated_nodes
                    or state.changed
                    or (state.comparison and state.comparison.improved)
                )
                if selection == 2
                else state.step in self.bookmarks
            )
            if keep:
                selected.append(states.indices[i])
        result = StateView(states.events)
        result.indices = tuple(selected)
        return result

    def _export_preview_key(self, states):
        return (
            id(states.events),
            len(states),
            self.start,
            self.target,
            tuple(self.export_options().items()),
        )

    def _image_count_text(self, count):
        if self.export_format.currentData() == "pdf":
            return f"{count} página" if count == 1 else f"{count} páginas"
        return f"{count} imagen" if count == 1 else f"{count} imágenes"

    def cancel_export_preview(self):
        self.export_preview_timer.stop()
        if self.export_preview_job is not None:
            self.export_preview_job.close()
            self.export_preview_job = None

    def refresh_export_preview(self):
        self.cancel_export_preview()
        simple = self.export_style.currentIndex() == 1
        self.export_description.setText(
            "Solo el grafo, con pesos y resaltados."
            if simple
            else "Grafo, tablas y explicación en una sola imagen 16:9. "
            "La composición ajusta columnas y escala para incluir todos los datos."
        )
        self.export_layout.setEnabled(not simple)
        self.export_composition.setEnabled(not simple)
        self.export_graph_fraction.setEnabled(
            not simple and self.export_composition.currentData() != "auto"
        )
        self.export_focus.setEnabled(not simple)
        self.export_legend.setEnabled(not simple)
        self.export_explanation.setEnabled(not simple)
        self.export_title.setEnabled(not simple)
        in_range = self.export_selection.currentIndex() == 1
        self.export_from.setEnabled(in_range)
        self.export_to.setEnabled(in_range)
        if not self.states:
            for label in self.export_count_labels.values():
                label.setText("—")
                label.setToolTip("")
            self.export_summary.setText("Inicia un algoritmo para conocer la cantidad de páginas.")
            return
        base = (
            StateView(self.states.events, self.export_detail.currentIndex() == 2)
            if self.export_detail.currentIndex()
            and self.algorithm_combo.currentText() != "Bellman-Ford"
            else self.states
        )
        old_max = self.export_to.maximum()
        with QSignalBlocker(self.export_from), QSignalBlocker(self.export_to):
            self.export_from.setRange(0, len(base) - 1)
            self.export_to.setRange(0, len(base) - 1)
            if self.export_to.value() == old_max:
                self.export_to.setValue(len(base) - 1)
        states = self._export_states()
        options = SlideOptions(**self.export_options())
        try:
            parts = page_count(self.graph, self.states[0].algorithm, options)
        except ValueError as error:
            for action in self.export_actions:
                action.setEnabled(False)
            self.export_summary.setText(str(error))
            return
        for action, kind in zip(
            self.export_actions, ("current", "all", "combined", "final"), strict=True
        ):
            action.setEnabled(not self.busy and (kind in {"current", "final"} or bool(states)))
        for kind, count in (("current", parts), ("final", parts), ("all", len(states) * parts)):
            self.export_count_labels[kind].setText(self._image_count_text(count))
        self.export_summary.setText(
            f"{len(states)} pasos seleccionados · Una diapositiva completa por paso. "
            f"Conjuntas: hasta {options.group_size} pasos, cada uno conserva su resolución."
        )
        if not states:
            self.export_count_labels["combined"].setText(self._image_count_text(0))
            self.export_summary.setText(
                "No hay pasos seleccionados. Ajusta el rango o marca pasos sobre el grafo."
            )
            return
        key = self._export_preview_key(states)
        label = self.export_count_labels["combined"]
        if key in self.export_preview_cache:
            label.setText(self._image_count_text(self.export_preview_cache[key]))
            return
        label.setText("Calculando…")
        if self.tabs.currentIndex() != 3 or self.busy:
            return
        from graph_visualizer.export.image_exporter import combined_image_count_job

        self.export_preview_job = combined_image_count_job(
            self.graph,
            self.graph_view.positions(),
            states,
            self.start,
            self.target,
            **self.export_options(),
        )
        self.export_preview_key = key
        self.export_preview_timer.start(0)

    def advance_export_preview(self):
        if self.export_preview_job is None:
            return
        try:
            next(self.export_preview_job)
        except StopIteration as result:
            self.cancel_export_preview()
            if len(self.export_preview_cache) >= 32:
                self.export_preview_cache.clear()
            self.export_preview_cache[self.export_preview_key] = result.value
            self.export_count_labels["combined"].setText(self._image_count_text(result.value))
        except (ValueError, OverflowError) as error:
            self.cancel_export_preview()
            self.export_count_labels["combined"].setText("No disponible")
            self.export_count_labels["combined"].setToolTip(str(error))

    def show_export_sample(self, kind="current"):
        if not self.states or self.busy:
            return
        self.stop_playback()
        states = self._export_states(kind)
        if not states:
            return
        index = (
            self.state_index
            if kind == "current"
            else max(0, states.equivalent(self.states[self.state_index].step))
        )
        try:
            dialog = ExportPreview(
                self,
                self.graph.copy(),
                self.graph_view.positions(),
                states,
                self.start,
                self.target,
                index,
                kind,
                self.export_options(),
            )
        except (ValueError, OSError, OverflowError) as error:
            QMessageBox.warning(self, "No se pudo generar la vista previa", str(error))
            return
        dialog.accepted.connect(lambda: self.export(kind, preview_confirmed=True))
        dialog.open()
