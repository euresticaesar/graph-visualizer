"""Native workspace customization, persisted independently of presets."""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from graph_visualizer.io.preferences import DEFAULTS, save_preferences
from graph_visualizer.ui.themes import THEME_NAMES, palette_for

UI_LAYOUTS = {
    "classic": "Controles a la izquierda",
    "right": "Controles a la derecha",
    "bottom": "Tablas debajo del grafo",
    "focus": "Lienzo amplio",
}


def style_sheet(p, size):
    return f"""
        QWidget {{ font-family: 'Sans Serif'; font-size: {size}px; color: {p.text}; }}
        QMainWindow, QDialog {{ background: {p.canvas}; }}
        QFrame#sidebar {{ background: {p.surface}; }}
        QFrame#sidebar QLabel, QFrame#sidebar QCheckBox {{ background: transparent; }}
        QLabel#title {{ font-size: {size + 14}px; font-weight: 700; }}
        QLabel#mode {{ color: {p.accent}; font-weight: 600; }}
        QLabel#section {{ font-weight: 600; font-size: {size + 1}px; }}
        QLabel#step {{ font-size: {size + 3}px; font-weight: 600; }}
        QLabel#hint {{ color: {p.muted}; font-size: {size}px; }}
        QLabel#error {{ color: {p.error}; }}
        QFrame#sectionCard, QFrame#resultsPanel {{
            background: {p.surface}; border: 1px solid {p.border}; border-radius: 10px;
        }}
        QFrame#sectionCard QLabel, QFrame#resultsPanel QLabel {{
            background: transparent;
            border: 0;
        }}
        QFrame#executionCard, QFrame#exportNotice {{
            background: {p.selection}; border: 1px solid {p.border}; border-radius: 10px;
        }}
        QFrame#executionCard QLabel, QFrame#exportNotice QLabel {{ background: transparent; }}
        QGraphicsView {{ border: 1px solid {p.border}; border-radius: 10px; }}
        QSplitter::handle {{ background: {p.border}; width: 6px; height: 6px; }}
        QPushButton, QToolButton, QComboBox, QLineEdit, QSpinBox, QDoubleSpinBox {{
            background: {p.surface}; color: {p.text}; border: 1px solid {p.border};
            border-radius: 6px; padding: 7px 9px;
        }}
        QPushButton:focus, QToolButton:focus, QComboBox:focus, QLineEdit:focus,
        QSpinBox:focus, QDoubleSpinBox:focus {{ border: 2px solid {p.accent}; }}
        QPushButton:hover, QToolButton:hover {{ background: {p.inset}; }}
        QPushButton#primary, QPushButton#confirmExport {{
            background: {p.accent}; color: {p.accent_text}; border-color: {p.accent};
        }}
        QPushButton#destructive {{ color: {p.error}; }}
        QPushButton:disabled, QToolButton:disabled, QComboBox:disabled,
        QLineEdit:disabled, QSpinBox:disabled {{ background: {p.inset}; color: {p.muted}; }}
        QToolButton#history {{ font-size: {size + 7}px; padding: 2px 8px; }}
        QCheckBox {{ spacing: 8px; background: transparent; }}
        QTableWidget {{
            background: {p.surface};
            alternate-background-color: {p.inset};
            gridline-color: {p.border};
        }}
        QHeaderView {{ background: {p.header}; color: {p.text}; }}
        QHeaderView::section {{
            background: {p.header}; color: {p.text}; padding: 4px;
            border: 1px solid {p.border};
        }}
        QTableCornerButton::section {{
            background: {p.header}; border: 1px solid {p.border};
        }}
        QAbstractScrollArea::corner {{ background: {p.inset}; }}
        QComboBox QAbstractItemView {{
            background: {p.surface};
            color: {p.text};
            selection-background-color: {p.selection};
            selection-color: {p.text};
        }}
        QFrame#controlCard {{
            background: {p.inset};
            border: 1px solid {p.border};
            border-radius: 12px;
        }}
        QScrollArea#controlScroll, QWidget#controlViewport, QWidget#controlPage {{
            background: transparent;
            border: 0;
        }}
        QTabWidget::pane {{ border: 0; background: {p.surface}; }}
        QTabBar::tab {{
            padding: 9px 5px;
            background: {p.inset};
            border: 1px solid {p.border};
            margin-bottom: 8px;
        }}
        QTabBar::tab:selected {{ background: {p.selection}; color: {p.text}; }}
        QTabBar::tab:disabled {{ color: {p.muted}; }}
        QStatusBar {{ background: {p.canvas}; color: {p.muted}; border-top: 1px solid {p.border}; }}
        QScrollBar:vertical {{ background: {p.inset}; width: 12px; margin: 0; }}
        QScrollBar:horizontal {{ background: {p.inset}; height: 12px; margin: 0; }}
        QScrollBar::handle {{
            background: {p.edge};
            min-width: 24px;
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
    """


class AppearanceControls:
    def apply_appearance(self):
        values = self.preferences
        p = palette_for(values["theme"], values["accent"])
        self.palette = p
        qt_palette = QPalette()
        for role, color in {
            QPalette.ColorRole.Window: p.canvas,
            QPalette.ColorRole.WindowText: p.text,
            QPalette.ColorRole.Base: p.surface,
            QPalette.ColorRole.AlternateBase: p.inset,
            QPalette.ColorRole.Text: p.text,
            QPalette.ColorRole.Button: p.surface,
            QPalette.ColorRole.ButtonText: p.text,
            QPalette.ColorRole.Highlight: p.accent,
            QPalette.ColorRole.HighlightedText: p.accent_text,
            QPalette.ColorRole.ToolTipBase: p.surface,
            QPalette.ColorRole.ToolTipText: p.text,
        }.items():
            qt_palette.setColor(role, QColor(color))
        self.setPalette(qt_palette)
        self.setStyleSheet(style_sheet(p, values["ui_font_size"]))
        self.graph_view.set_appearance(p, values["graph_font_scale"])
        self.state_panel.palette = self.matrix_panel.palette = p
        layout = values["ui_layout"]
        previous = getattr(self, "active_ui_layout", None)
        sizes = self.workspace_splitter.sizes()
        self.workspace_splitter.insertWidget(0 if layout != "right" else 1, self.sidebar)
        if previous is not None and previous != layout:
            if previous == "focus":
                sizes = self.preferences["workspace_sizes"]
            elif layout == "focus":
                self.preferences["workspace_sizes"] = sizes
            elif (previous == "right") != (layout == "right"):
                sizes.reverse()
            self.workspace_splitter.setSizes(sizes)
        self.workspace_splitter.setStretchFactor(0, 1 if layout == "right" else 0)
        self.workspace_splitter.setStretchFactor(1, 0 if layout == "right" else 1)
        self.sidebar.setVisible(layout != "focus")
        self.visual_splitter.setOrientation(
            Qt.Orientation.Vertical if layout == "bottom" else Qt.Orientation.Horizontal
        )
        for panel in (self.state_panel, self.matrix_panel):
            panel.splitter.setOrientation(
                Qt.Orientation.Horizontal if layout == "bottom" else Qt.Orientation.Vertical
            )
        if previous != layout:
            self.visual_splitter.setSizes([600, 320])
        self.active_ui_layout = layout
        self.focus_button.setText("Mostrar controles" if layout == "focus" else "Ampliar lienzo")
        self._refresh_legend_colors()
        if self.states:
            self.show_state(self.state_index)
        self.export_preview_cache.clear()
        self.refresh_export_preview()
        QTimer.singleShot(0, self.refit_workspace)

    def _refresh_legend_colors(self):
        p = self.palette
        colors = [p.edge, p.comparison, p.k_border, p.current, p.comparison, p.accent]
        for index in range(self.legend_grid.count()):
            label = self.legend_grid.itemAt(index).widget()
            label.setStyleSheet(f"color: {colors[index]};")

    def toggle_focus_layout(self):
        if self.busy:
            return
        current = self.preferences["ui_layout"]
        self.preferences["ui_layout"] = self.previous_layout if current == "focus" else "focus"
        if current != "focus":
            self.previous_layout = current
        self.apply_appearance()
        self.persist_preferences()

    def open_appearance(self):
        if self.busy:
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Personalizar interfaz")
        dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        dialog.resize(480, 390)
        column = QVBoxLayout(dialog)
        hint = QLabel(
            "Ajusta tu espacio de trabajo. Las imágenes tienen su propia configuración en Exportar."
        )
        hint.setWordWrap(True)
        column.addWidget(hint)
        form = QFormLayout()
        theme, layout = QComboBox(), QComboBox()
        theme.setObjectName("appearanceTheme")
        layout.setObjectName("appearanceLayout")
        for key, name in THEME_NAMES.items():
            theme.addItem(name, key)
        for key, name in UI_LAYOUTS.items():
            layout.addItem(name, key)
        theme.setCurrentIndex(theme.findData(self.preferences["theme"]))
        layout.setCurrentIndex(layout.findData(self.preferences["ui_layout"]))
        font_size = QSpinBox()
        font_size.setRange(11, 18)
        font_size.setValue(self.preferences["ui_font_size"])
        font_size.setSuffix(" px")
        graph_scale = QDoubleSpinBox()
        graph_scale.setRange(0.8, 1.5)
        graph_scale.setSingleStep(0.1)
        graph_scale.setValue(self.preferences["graph_font_scale"])
        accent = QPushButton("Elegir color…")
        accent_value = [self.preferences["accent"]]

        def choose_color():
            color = QColorDialog.getColor(
                QColor(accent_value[0] or self.palette.accent), dialog, "Color de acento"
            )
            if color.isValid():
                accent_value[0] = color.name()
                accent.setText(color.name())

        accent.clicked.connect(choose_color)
        reset_accent = QPushButton("Usar acento del esquema")
        reset_accent.clicked.connect(
            lambda: (accent_value.__setitem__(0, ""), accent.setText("Elegir color…"))
        )
        for label, widget in (
            ("Esquema de color", theme),
            ("Distribución", layout),
            ("Texto de interfaz", font_size),
            ("Texto del grafo", graph_scale),
            ("Acento personalizado", accent),
        ):
            form.addRow(label, widget)
        form.addRow("", reset_accent)
        column.addLayout(form)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Apply
            | QDialogButtonBox.StandardButton.Close
            | QDialogButtonBox.StandardButton.RestoreDefaults
        )

        def apply():
            if self.busy:
                return
            self.preferences.update(
                theme=theme.currentData(),
                ui_layout=layout.currentData(),
                ui_font_size=font_size.value(),
                graph_font_scale=graph_scale.value(),
                accent=accent_value[0],
            )
            if layout.currentData() != "focus":
                self.previous_layout = layout.currentData()
            self.apply_appearance()
            self.persist_preferences()

        def restore():
            theme.setCurrentIndex(theme.findData(DEFAULTS["theme"]))
            layout.setCurrentIndex(layout.findData(DEFAULTS["ui_layout"]))
            font_size.setValue(DEFAULTS["ui_font_size"])
            graph_scale.setValue(DEFAULTS["graph_font_scale"])
            accent_value[0] = ""
            accent.setText("Elegir color…")
            apply()

        buttons.button(QDialogButtonBox.StandardButton.Apply).clicked.connect(apply)
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(restore)
        buttons.rejected.connect(dialog.reject)
        column.addWidget(buttons)
        dialog.show()

    def persist_preferences(self):
        self.preferences.update(
            window_size=[self.width(), self.height()],
            results_sizes=self.visual_splitter.sizes(),
            state_labels=self.state_labels_checkbox.isChecked(),
            edge_ids=self.edge_ids_checkbox.isChecked(),
        )
        if self.preferences["ui_layout"] != "focus":
            self.preferences["workspace_sizes"] = self.workspace_splitter.sizes()
        self.collect_export_preferences()
        try:
            save_preferences(self.data_dir / "preferences.json", self.preferences)
        except OSError as error:
            self.statusBar().showMessage(f"No se pudieron guardar las preferencias: {error}", 8000)
