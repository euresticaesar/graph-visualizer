import math
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
from PySide6.QtCore import QSignalBlocker, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from graph_visualizer.core.dijkstra import dijkstra_steps
from graph_visualizer.core.graph import graphs_equal, validate_graph
from graph_visualizer.core.models import DijkstraState
from graph_visualizer.export.image_exporter import ExportKind, export_job
from graph_visualizer.io.graph_io import load_graph, save_graph_data
from graph_visualizer.io.layout_io import PositionMap, load_layout, save_layout
from graph_visualizer.io.preferences import load_preferences
from graph_visualizer.paths import DATA_DIR, OUTPUT_DIR
from graph_visualizer.ui.appearance_controls import AppearanceControls
from graph_visualizer.ui.export_controls import ExportControls
from graph_visualizer.ui.graph_editor import GraphEditor
from graph_visualizer.ui.graph_view import GraphView
from graph_visualizer.ui.node_combo_box import NodeComboBox, sorted_node_ids
from graph_visualizer.ui.preset_controls import PresetControls
from graph_visualizer.ui.section_card import SectionCard
from graph_visualizer.ui.state_panel import MatrixPanel, StatePanel


class ControlTabs(QTabWidget):
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.tabBar().setFixedWidth(self.contentsRect().width())


@dataclass
class EditSnapshot:
    graph: nx.Graph
    positions: PositionMap
    start: str
    target: str
    description: str
    preset_path: Path | None = None
    preset_baseline: dict | None = None
    algorithm: str = "Dijkstra"
    detail: bool = True
    early_stop: bool = False


class MainWindow(AppearanceControls, PresetControls, ExportControls, QMainWindow):
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "graph_view"):
            QTimer.singleShot(0, self.refit_workspace)

    def refit_workspace(self):
        if self.graph_view.auto_fit and not self.busy:
            self.graph_view.fit_graph()

    def __init__(self, data_dir: Path = DATA_DIR, output_dir: Path = OUTPUT_DIR):
        super().__init__()
        self.data_dir, self.output_dir = data_dir, output_dir
        self.preferences = load_preferences(data_dir / "preferences.json")
        self.previous_layout = (
            self.preferences["ui_layout"] if self.preferences["ui_layout"] != "focus" else "classic"
        )
        self.revision = 0
        self.export_generator = None
        self.graph = load_graph(data_dir / "nodes.csv", data_dir / "edges.csv")
        positions = load_layout(data_dir / "layout.json", self.graph)
        self.states: list[DijkstraState] = []
        self.state_index = 0
        self.bookmarks = set()
        self.history: list[EditSnapshot] = []
        self.history_index = 0
        self.last_export_path: Path | None = None
        self.play_timer = QTimer(self)
        self.play_timer.timeout.connect(lambda: self.show_state(self.state_index + 1))
        self.export_preview_timer = QTimer(self)
        self.export_preview_timer.timeout.connect(self.advance_export_preview)
        self.export_preview_job = None
        self.export_preview_cache = {}
        self.busy = False
        self.worker = None
        self.setWindowTitle("Visualizador de grafos · Caminos mínimos")
        self.resize(*self.preferences["window_size"])
        self.setMinimumSize(940, 680)
        self.graph_view = GraphView(self.graph, positions)
        self.graph_view.layout_changed.connect(self._save_layout)
        self._build_ui()
        self._apply_style()
        self.history.append(self._snapshot("Estado inicial"))
        self.reset()
        self.apply_appearance()
        if self.preferences["ui_layout"] != "focus":
            self.workspace_splitter.setSizes(self.preferences["workspace_sizes"])
        if self.preferences["results_sizes"]:
            self.visual_splitter.setSizes(self.preferences["results_sizes"])
        self.preset_baseline = self.preset_fingerprint()
        self.remember_preset()
        QTimer.singleShot(0, self.graph_view.fit_graph)

    @property
    def start(self) -> str:
        return self.start_combo.currentData()

    @property
    def target(self) -> str:
        return self.target_combo.currentData()

    def _action(self, text: str, callback, shortcuts=()) -> QAction:
        action = QAction(text, self)
        action.triggered.connect(callback)
        action.setShortcuts(list(shortcuts))
        self.addAction(action)
        return action

    def _action_button(self, action: QAction) -> QToolButton:
        button = QToolButton()
        button.setDefaultAction(action)
        button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        return button

    @staticmethod
    def _scroll_page(widget: QWidget) -> QFrame:
        card = QFrame()
        card.setObjectName("controlCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 6, 8, 6)
        scroll = QScrollArea()
        scroll.setObjectName("controlScroll")
        scroll.viewport().setObjectName("controlViewport")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        widget.setObjectName("controlPage")
        scroll.setWidget(widget)
        widget.setAutoFillBackground(False)
        scroll.viewport().setAutoFillBackground(False)
        layout.addWidget(scroll)
        return card

    def _build_ui(self) -> None:
        central = QWidget()
        row = QHBoxLayout(central)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        sidebar = self.sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(310)
        sidebar.setMaximumWidth(520)
        controls = QVBoxLayout(sidebar)
        controls.setContentsMargins(16, 18, 16, 14)
        controls.setSpacing(10)
        title = QLabel("Caminos mínimos")
        title.setObjectName("title")
        controls.addWidget(title)
        self.mode_label = QLabel()
        self.mode_label.setObjectName("mode")
        controls.addWidget(self.mode_label)
        self.tabs = ControlTabs()
        self.tabs.tabBar().setExpanding(True)
        self.tabs.addTab(self._scroll_page(self._algorithm_controls()), "Recorrido")
        self.editor = GraphEditor(self.graph)
        self.tabs.addTab(self._scroll_page(self.editor), "Editar")
        self.editor.graph_type_requested.connect(self.change_graph_type)
        self.editor.add_node_requested.connect(self.add_node)
        self.editor.rename_node_requested.connect(self.rename_node)
        self.editor.delete_node_requested.connect(self.delete_node)
        self.editor.save_edge_requested.connect(self.set_edge)
        self.editor.delete_edge_requested.connect(self.delete_edge)
        self.graph_view.node_selected.connect(self.editor.select_node)
        self.graph_view.node_creation_requested.connect(self._create_node_at)
        self.graph_view.edge_edit_requested.connect(self._edit_edge_at)
        self.graph_view.connection_requested.connect(self._connect_nodes)
        self.tabs.addTab(self._scroll_page(self.build_presets()), "Presets")
        self.tabs.addTab(self._scroll_page(self._export_controls()), "Exportar")
        self.tabs.currentChanged.connect(self._tab_changed)
        controls.addWidget(self.tabs, 1)
        self._build_legend(controls)
        self.exit_button = QPushButton("Salir")
        self.exit_button.setShortcut("Ctrl+Q")
        self.exit_button.clicked.connect(self.close)
        controls.addWidget(self.exit_button)

        graph_panel = self.graph_panel = QWidget()
        graph_column = QVBoxLayout(graph_panel)
        graph_column.setContentsMargins(14, 12, 14, 12)
        graph_column.setSpacing(10)
        toolbar = QHBoxLayout()
        self.graph_info = QLabel()
        self.graph_info.setWordWrap(True)
        toolbar.addWidget(self.graph_info, 1)
        self.undo_action = self._action("↶", self.undo, ["Ctrl+Z"])
        self.redo_action = self._action("↷", self.redo, ["Ctrl+Y", "Ctrl+Shift+Z"])
        self.undo_button = self._action_button(self.undo_action)
        self.redo_button = self._action_button(self.redo_action)
        for button, name in ((self.undo_button, "Deshacer"), (self.redo_button, "Rehacer")):
            button.setObjectName("history")
            button.setAccessibleName(name)
            button.setFixedWidth(42)
            toolbar.addWidget(button)
        self.fit_button = QPushButton("Ajustar vista")
        self.fit_button.setShortcut("Ctrl+0")
        self.fit_button.clicked.connect(self.graph_view.fit_graph)
        toolbar.addWidget(self.fit_button)
        self.data_button = QPushButton("Datos del grafo")
        self.data_button.clicked.connect(self.open_graph_data)
        toolbar.addWidget(self.data_button)
        graph_column.addLayout(toolbar)
        workspace_tools = QHBoxLayout()
        self.appearance_button = QPushButton("Personalizar")
        self.appearance_button.clicked.connect(self.open_appearance)
        self.focus_button = QPushButton("Ampliar lienzo")
        self.focus_button.clicked.connect(self.toggle_focus_layout)
        self.copy_image_button = QPushButton("Copiar imagen")
        self.copy_image_button.setToolTip(
            "Copia la primera página del paso visible con las opciones de Exportar."
        )
        self.copy_image_button.clicked.connect(self.copy_current_image)
        self.bookmark_button = QPushButton("Marcar paso")
        self.bookmark_button.setCheckable(True)
        self.bookmark_button.clicked.connect(self.toggle_bookmark)
        for button in (
            self.appearance_button,
            self.focus_button,
            self.copy_image_button,
            self.bookmark_button,
        ):
            workspace_tools.addWidget(button)
        workspace_tools.addStretch()
        graph_column.addLayout(workspace_tools)

        display_row = QHBoxLayout()
        self.state_labels_checkbox = QCheckBox("Etiquetas de estado")
        self.state_labels_checkbox.setChecked(self.preferences["state_labels"])
        self.graph_view.set_state_labels_visible(self.preferences["state_labels"])
        self.state_labels_checkbox.setToolTip(
            "Muestra los estados de los nodos; INICIO, DESTINO y distancias permanecen visibles."
        )
        self.state_labels_checkbox.toggled.connect(self.graph_view.set_state_labels_visible)
        self.state_labels_checkbox.toggled.connect(self.refresh_export_preview)
        display_row.addWidget(self.state_labels_checkbox)
        self.edge_ids_checkbox = QCheckBox("IDs de conexiones")
        self.edge_ids_checkbox.setChecked(self.preferences["edge_ids"])
        self.graph_view.set_edge_ids_visible(self.preferences["edge_ids"])
        self.edge_ids_checkbox.setToolTip(
            "Muestra #ID junto al peso para distinguir conexiones paralelas. "
            "También se aplica a las exportaciones PNG."
        )
        self.edge_ids_checkbox.toggled.connect(self.graph_view.set_edge_ids_visible)
        self.edge_ids_checkbox.toggled.connect(self.refresh_export_preview)
        display_row.addWidget(self.edge_ids_checkbox)
        display_row.addStretch()
        self.help_button = QToolButton()
        self.help_button.setText("Gestos y ayuda")
        self.help_button.setCheckable(True)
        display_row.addWidget(self.help_button)
        graph_column.addLayout(display_row)
        self.view_hint = QLabel()
        self.view_hint.setObjectName("hint")
        self.view_hint.setWordWrap(True)
        self.view_hint.hide()
        self.help_button.toggled.connect(self.view_hint.setVisible)
        graph_column.addWidget(self.view_hint)

        self.execution_card = QFrame()
        self.execution_card.setObjectName("executionCard")
        execution_text = QVBoxLayout(self.execution_card)
        execution_text.setContentsMargins(14, 10, 14, 12)
        execution_text.setSpacing(6)
        execution_text.addWidget(self.step_label)
        execution_text.addWidget(self.detail_label)
        graph_column.addWidget(self.execution_card)
        self.export_notice = QFrame()
        self.export_notice.setObjectName("exportNotice")
        notice_row = QHBoxLayout(self.export_notice)
        notice_text = QVBoxLayout()
        self.export_notice_title = QLabel("✓ Exportación completada")
        self.export_notice_title.setObjectName("section")
        notice_text.addWidget(self.export_notice_title)
        self.export_notice_path = QLabel()
        self.export_notice_path.setTextFormat(Qt.TextFormat.PlainText)
        self.export_notice_path.setWordWrap(True)
        self.export_notice_path.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        notice_text.addWidget(self.export_notice_path)
        notice_row.addLayout(notice_text, 1)
        self.notice_open_button = QPushButton("Abrir carpeta")
        self.notice_open_button.clicked.connect(self.open_last_export_folder)
        notice_row.addWidget(self.notice_open_button)
        dismiss = QPushButton("×")
        dismiss.setAccessibleName("Cerrar aviso de exportación")
        dismiss.setFixedWidth(32)
        dismiss.clicked.connect(self.export_notice.hide)
        notice_row.addWidget(dismiss)
        self.export_notice.hide()
        graph_column.addWidget(self.export_notice)

        self.visual_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.visual_splitter.setChildrenCollapsible(False)
        self.graph_view.setMinimumWidth(280)
        self.visual_splitter.addWidget(self.graph_view)
        self.results_panel = QFrame()
        self.results_panel.setObjectName("resultsPanel")
        self.results_panel.setMinimumWidth(280)
        results_column = QVBoxLayout(self.results_panel)
        results_column.setContentsMargins(12, 12, 12, 12)
        results_column.setSpacing(8)
        self.results_title = QLabel()
        self.results_title.setObjectName("section")
        results_column.addWidget(self.results_title)
        self.state_panel = StatePanel()
        self.state_panel.hide()
        results_column.addWidget(self.state_panel, 1)
        self.matrix_panel = MatrixPanel()
        self.matrix_panel.hide()
        results_column.addWidget(self.matrix_panel, 1)
        self.results_panel.hide()
        self.visual_splitter.addWidget(self.results_panel)
        self.visual_splitter.setStretchFactor(0, 1)
        self.visual_splitter.setStretchFactor(1, 0)
        graph_column.addWidget(self.visual_splitter, 1)
        self.workspace_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.workspace_splitter.setChildrenCollapsible(False)
        self.workspace_splitter.addWidget(sidebar)
        self.workspace_splitter.addWidget(graph_panel)
        self.workspace_splitter.setStretchFactor(0, 0)
        self.workspace_splitter.setStretchFactor(1, 1)
        self.workspace_splitter.setSizes([365, 1015])
        self.workspace_splitter.splitterMoved.connect(self.refit_workspace)
        self.visual_splitter.splitterMoved.connect(self.refit_workspace)
        row.addWidget(self.workspace_splitter)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Grafo cargado. Los cambios se guardan automáticamente.")
        self.cancel_button = QPushButton("Cancelar operación")
        self.cancel_button.clicked.connect(self.cancel_operation)
        self.cancel_button.hide()
        self.statusBar().addPermanentWidget(self.cancel_button)
        self._action("Personalizar interfaz", self.open_appearance, ["Ctrl+,"])
        self._action("Datos del grafo", self.open_graph_data, ["Ctrl+D"])
        self._action("Copiar imagen del paso", self.copy_current_image, ["Ctrl+Shift+C"])
        self._action("Ampliar lienzo", self.toggle_focus_layout, ["Ctrl+Shift+F"])
        self._action("Paso anterior", lambda: self.navigate_step(-1), ["Alt+Left"])
        self._action("Paso siguiente", lambda: self.navigate_step(1), ["Alt+Right"])
        self.graph_view.navigation_requested.connect(self.navigate_step)
        self.graph_view.playback_requested.connect(self.toggle_playback)

    def _build_legend(self, controls: QVBoxLayout) -> None:
        self.legend_button = QToolButton()
        self.legend_button.setText("Colores y notación")
        self.legend_button.setCheckable(True)
        self.legend_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.legend_button.setArrowType(Qt.ArrowType.RightArrow)
        self.legend_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        controls.addWidget(self.legend_button)
        legend = QFrame()
        legend.setObjectName("sectionCard")
        column = QVBoxLayout(legend)
        self.legend_grid = QGridLayout()
        self.legend_grid.setHorizontalSpacing(12)
        self.legend_grid.setVerticalSpacing(8)
        for index, (symbol, _color, text) in enumerate(
            [
                ("●", "#64748b", "Sin alcanzar"),
                ("●", "#b48412", "Tentativo"),
                ("●", "#329758", "Fijado (Dijkstra / A*)"),
                ("●", "#18794e", "Nodo actual / k"),
                ("━", "#a66300", "Comparación"),
                ("━", "#087e8b", "Ruta consultada"),
            ]
        ):
            label = QLabel(f"{symbol} {text}")
            self.legend_grid.addWidget(label, index // 2, index % 2)
        column.addLayout(self.legend_grid)
        self.notation = QLabel("[distancia, predecesor] · Negritas: mejora")
        self.notation.setObjectName("hint")
        self.notation.setWordWrap(True)
        column.addWidget(self.notation)
        legend.hide()
        self.legend_button.toggled.connect(legend.setVisible)
        self.legend_button.toggled.connect(
            lambda checked: self.legend_button.setArrowType(
                Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
            )
        )
        controls.addWidget(legend)

    def _algorithm_controls(self) -> QWidget:
        page = QWidget()
        controls = QVBoxLayout(page)
        controls.setContentsMargins(0, 4, 0, 4)
        controls.setSpacing(12)
        setup = SectionCard("1. Configurar recorrido")
        self.algorithm_combo = QComboBox()
        self.algorithm_combo.addItems(["Dijkstra", "Bellman-Ford", "Floyd-Warshall", "A*"])
        self.algorithm_combo.currentTextChanged.connect(self.algorithm_changed)
        setup.content.addWidget(self.algorithm_combo)
        self.algorithm_hint = QLabel("Ruta mínima entre el origen y el destino.")
        self.algorithm_hint.setObjectName("hint")
        self.algorithm_hint.setWordWrap(True)
        setup.content.addWidget(self.algorithm_hint)
        self.start_combo, self.target_combo = NodeComboBox(), NodeComboBox()
        self.algorithm_combo.setAccessibleName("Algoritmo")
        self.start_combo.setAccessibleName("Origen")
        self.target_combo.setAccessibleName("Destino")
        self.start_combo.set_nodes(self.graph)
        self.target_combo.set_nodes(self.graph)
        self.target_combo.setCurrentIndex(self.target_combo.count() - 1)
        selection = QGridLayout()
        self.start_label, self.target_label = QLabel("Origen"), QLabel("Destino")
        self.start_label.setBuddy(self.start_combo)
        self.target_label.setBuddy(self.target_combo)
        for index, (label, combo) in enumerate(
            [(self.start_label, self.start_combo), (self.target_label, self.target_combo)]
        ):
            selection.addWidget(label, index, 0)
            selection.addWidget(combo, index, 1)
            combo.currentIndexChanged.connect(self._selection_changed)
        self.swap_button = QToolButton()
        self.swap_button.setText("⇄")
        self.swap_button.setFixedWidth(34)
        self.swap_button.setAccessibleName("Intercambiar origen y destino")
        self.swap_button.setToolTip("Intercambiar origen y destino")
        self.swap_button.clicked.connect(self.swap_endpoints)
        selection.addWidget(self.swap_button, 0, 2, 2, 1)
        selection.setColumnStretch(1, 1)
        setup.content.addLayout(selection)
        self.early_stop = QCheckBox("Terminar si una pasada no mejora")
        self.early_stop.setToolTip("Detiene Bellman-Ford tras una pasada completa sin cambios.")
        self.early_stop.setVisible(False)
        setup.content.addWidget(self.early_stop)
        self.detail_checkbox = QCheckBox("Por comparación")
        self.detail_checkbox.setChecked(True)
        self.detail_checkbox.toggled.connect(self.change_detail)
        setup.content.addWidget(self.detail_checkbox)
        self.run_button = QPushButton("Iniciar Dijkstra")
        self.run_button.setObjectName("primary")
        self.run_button.clicked.connect(self.initialize)
        setup.content.addWidget(self.run_button)
        controls.addWidget(setup)

        navigation = SectionCard("2. Explorar pasos")
        buttons = QGridLayout()
        self.previous_button, self.next_button = (
            QPushButton("← Anterior"),
            QPushButton("Siguiente →"),
        )
        self.previous_button.clicked.connect(lambda: self.show_state(self.state_index - 1))
        self.next_button.clicked.connect(lambda: self.show_state(self.state_index + 1))
        self.first_button, self.last_button = QPushButton("⇤"), QPushButton("⇥")
        for button, text in ((self.first_button, "Primer paso"), (self.last_button, "Último paso")):
            button.setAccessibleName(text)
            button.setToolTip(text)
            button.setFixedWidth(34)
        self.first_button.clicked.connect(lambda: self.show_state(0))
        self.last_button.clicked.connect(lambda: self.show_state(len(self.states) - 1))
        self.previous_button.setText("Anterior")
        self.next_button.setText("Siguiente")
        buttons.addWidget(self.first_button, 0, 0)
        buttons.addWidget(self.previous_button, 0, 1)
        buttons.addWidget(self.next_button, 0, 2)
        buttons.addWidget(self.last_button, 0, 3)
        navigation.content.addLayout(buttons)
        jumps = QFormLayout()
        self.jump_step = QSpinBox()
        self.jump_step.setKeyboardTracking(False)
        self.jump_step.valueChanged.connect(self.show_state)
        jumps.addRow("Paso", self.jump_step)
        self.jump_phase = QComboBox()
        self.jump_phase.activated.connect(
            lambda index: self.show_state(self.jump_phase.itemData(index))
        )
        jumps.addRow("Fase", self.jump_phase)
        navigation.content.addLayout(jumps)
        controls.addWidget(navigation)

        playback = SectionCard("3. Reproducción automática")
        self.play_button = QPushButton("▶ Reproducir")
        self.play_button.clicked.connect(self.toggle_playback)
        playback.content.addWidget(self.play_button)
        self.speed = QSpinBox()
        self.speed.setRange(50, 10000)
        self.speed.setValue(800)
        self.speed.setSuffix(" ms / paso")
        self.speed.valueChanged.connect(lambda value: self.play_timer.setInterval(value))
        speed_form = QFormLayout()
        speed_form.addRow("Intervalo", self.speed)
        playback.content.addLayout(speed_form)
        controls.addWidget(playback)
        self.reset_button = QPushButton("Volver a editar")
        self.reset_button.clicked.connect(self.reset)
        controls.addWidget(self.reset_button)
        self.step_label = QLabel()
        self.step_label.setObjectName("step")
        self.step_label.setWordWrap(True)
        self.detail_label = QLabel()
        self.detail_label.setTextFormat(Qt.TextFormat.PlainText)
        self.detail_label.setWordWrap(True)
        self.detail_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        controls.addStretch()
        return page

    def _tab_changed(self, index: int) -> None:
        if index:
            self.stop_playback()
        if index == 3:
            self.refresh_export_preview()
        else:
            self.cancel_export_preview()

    def _apply_style(self) -> None:
        from graph_visualizer.ui.appearance_controls import style_sheet
        from graph_visualizer.ui.themes import palette_for

        self.setStyleSheet(
            style_sheet(
                palette_for(self.preferences["theme"], self.preferences["accent"]),
                self.preferences["ui_font_size"],
            )
        )

    def _snapshot(self, description: str) -> EditSnapshot:
        return EditSnapshot(
            self.graph.copy(),
            self.graph_view.positions(),
            self.start,
            self.target,
            description,
            self.preset_path,
            self.preset_baseline,
            self.algorithm_combo.currentText(),
            self.detail_checkbox.isChecked(),
            self.early_stop.isChecked(),
        )

    def _restore(self, snapshot: EditSnapshot) -> None:
        self.preset_path, self.preset_baseline = snapshot.preset_path, snapshot.preset_baseline
        topology_changed = not graphs_equal(self.graph, snapshot.graph)
        self.graph = snapshot.graph.copy()
        if topology_changed:
            self.graph_view.set_graph(self.graph, snapshot.positions)
        else:
            self.graph_view.graph = self.graph
            for node, position in snapshot.positions.items():
                self.graph_view.nodes[node].setPos(*position)
        for combo, selected in (
            (self.start_combo, snapshot.start),
            (self.target_combo, snapshot.target),
        ):
            combo.set_nodes(self.graph, selected)
        self.editor.set_graph(self.graph)
        if self.algorithm_combo.currentText() != snapshot.algorithm:
            self.algorithm_combo.setCurrentText(snapshot.algorithm)
        self.detail_checkbox.setChecked(snapshot.detail)
        self.early_stop.setChecked(snapshot.early_stop)
        self.graph_view.apply_state(None, self.start, self.target)
        self.graph_info.setText(
            f"{len(self.graph)} nodos · {self.graph.number_of_edges()} conexiones · "
            f"{'Dirigido' if self.graph.is_directed() else 'No dirigido'}"
        )
        self._refresh_swap_button()

    def _persist_and_restore(self, snapshot: EditSnapshot) -> bool:
        current = self.history[self.history_index]
        try:
            validate_graph(snapshot.graph)
            if not graphs_equal(current.graph, snapshot.graph):
                save_graph_data(self.data_dir, snapshot.graph, snapshot.positions)
            elif current.positions != snapshot.positions:
                save_layout(self.data_dir / "layout.json", snapshot.positions)
        except (OSError, ValueError) as error:
            self._restore(current)
            QMessageBox.warning(
                self, "No se pudo guardar", f"No se pudo guardar el cambio.\n{error}"
            )
            return False
        self._restore(snapshot)
        return True

    def _commit_edit(self, snapshot: EditSnapshot) -> bool:
        if self.states or self.busy:
            return False
        self.remember_preset()
        current = self.history[self.history_index]
        if self._same_edit(current, snapshot):
            return False
        if not self._persist_and_restore(snapshot):
            return False
        del self.history[self.history_index + 1 :]
        self.history.append(snapshot)
        # Conserva hasta 100 acciones sin acumular copias indefinidamente.
        if len(self.history) > 101:
            self.history.pop(0)
        self.history_index = len(self.history) - 1
        self.revision += 1
        self._sync_history()
        saved = current.positions != snapshot.positions or not graphs_equal(
            current.graph, snapshot.graph
        )
        message = snapshot.description + (" · Guardado" if saved else "")
        self.statusBar().showMessage(message, 5000)
        return True

    @staticmethod
    def _same_edit(current, snapshot):
        return (
            graphs_equal(current.graph, snapshot.graph)
            and current.positions == snapshot.positions
            and (current.start, current.target) == (snapshot.start, snapshot.target)
            and (current.algorithm, current.detail, current.early_stop, current.preset_path)
            == (snapshot.algorithm, snapshot.detail, snapshot.early_stop, snapshot.preset_path)
        )

    def _sync_history(self) -> None:
        editable = not self.states and not self.busy
        self.undo_action.setEnabled(editable and self.history_index > 0)
        self.redo_action.setEnabled(editable and self.history_index < len(self.history) - 1)
        undo_text = self.history[self.history_index].description if self.history_index else ""
        redo_text = (
            self.history[self.history_index + 1].description
            if self.history_index < len(self.history) - 1
            else ""
        )
        self.undo_action.setToolTip(
            f"Deshacer: {undo_text} (Ctrl+Z)" if undo_text else "Deshacer (Ctrl+Z)"
        )
        self.redo_action.setToolTip(
            f"Rehacer: {redo_text} (Ctrl+Y)" if redo_text else "Rehacer (Ctrl+Y)"
        )

    def undo(self) -> None:
        if self.states or self.busy or self.history_index == 0:
            return
        description = self.history[self.history_index].description
        if self._persist_and_restore(self.history[self.history_index - 1]):
            self.history_index -= 1
            self.revision += 1
            self._sync_history()
            self.statusBar().showMessage(f"Deshecho: {description}", 5000)

    def redo(self) -> None:
        if self.states or self.busy or self.history_index >= len(self.history) - 1:
            return
        snapshot = self.history[self.history_index + 1]
        if self._persist_and_restore(snapshot):
            self.history_index += 1
            self.revision += 1
            self._sync_history()
            self.statusBar().showMessage(f"Rehecho: {snapshot.description}", 5000)

    def _selection_changed(self) -> None:
        self._refresh_swap_button()
        if self.states:
            self.show_state(self.state_index)
            self.refresh_export_preview()
            return
        if not self.states and self.history:
            self._commit_edit(self._snapshot("Cambiar inicio o destino"))

    def _refresh_swap_button(self) -> None:
        self.swap_button.setEnabled(
            self.start_combo.isEnabled()
            and self.target_combo.isEnabled()
            and self.start != self.target
        )

    def swap_endpoints(self) -> None:
        if not self.swap_button.isEnabled():
            return
        start, target = self.start, self.target
        with QSignalBlocker(self.start_combo), QSignalBlocker(self.target_combo):
            self.start_combo.setCurrentIndex(self.start_combo.findData(target))
            self.target_combo.setCurrentIndex(self.target_combo.findData(start))
        self.start_combo.setToolTip(self.start_combo.currentText())
        self.target_combo.setToolTip(self.target_combo.currentText())
        self._selection_changed()

    def _save_layout(self) -> None:
        self._commit_edit(self._snapshot("Mover nodos"))

    def add_node(self, node: str, position: tuple[float, float] | None = None) -> bool:
        if self.states:
            return False
        if not isinstance(node, str) or not node or node.strip() != node or node in self.graph:
            self.editor.error_label.setText("Usa un ID texto único que todavía no exista.")
            return False
        snapshot = self._snapshot(f"Agregar nodo {node}")
        snapshot.graph.add_node(node)
        if position is None:
            center = self.graph_view.mapToScene(self.graph_view.viewport().rect().center())
            x, y = center.x(), center.y()
            while any(math.hypot(x - px, y - py) < 100 for px, py in snapshot.positions.values()):
                x += 110
            position = (x, y)
        snapshot.positions[node] = position
        if self._commit_edit(snapshot):
            self.editor.select_node(node)
            self.graph_view.ensureVisible(self.graph_view.nodes[node])
            return True
        return False

    def _create_node_at(self, position) -> None:
        if self.states:
            return
        value = next(str(i) for i in range(len(self.graph) + 1) if str(i) not in self.graph)
        while True:
            value, accepted = QInputDialog.getText(
                self, "Agregar nodo", "ID del nodo (texto único):", text=value
            )
            if not accepted:
                return
            try:
                node = value.strip()
                if not node or node in self.graph:
                    raise ValueError
            except ValueError:
                QMessageBox.warning(self, "ID no válido", "Usa un texto único que no exista.")
                continue
            self.add_node(node, (position.x(), position.y()))
            return

    def _request_weight(self, source: str, target: str, weight: float) -> float | None:
        value = str(weight)
        while True:
            value, accepted = QInputDialog.getText(
                self,
                f"Conexión {source}–{target}",
                "Peso finito (usa punto decimal):",
                text=value,
            )
            if not accepted:
                return None
            try:
                weight = float(value)
                if not math.isfinite(weight) or (weight < 0 and not self.graph.is_directed()):
                    raise ValueError
                return weight
            except ValueError:
                QMessageBox.warning(
                    self,
                    "Peso no válido",
                    "Usa un número finito; negativo solo en grafos dirigidos.",
                )

    def _edit_edge_at(self, source: str, target: str, key: int) -> None:
        if self.states or not self.graph.has_edge(source, target, key):
            return
        self.editor.select_edge(source, target, key)
        weight = self._request_weight(source, target, self.graph[source][target][key]["weight"])
        if weight is not None:
            self.set_edge(source, target, weight, key)

    def _connect_nodes(self, source: str, target: str) -> None:
        if self.states:
            return
        weight = self._request_weight(source, target, 1)
        if weight is not None:
            self.set_edge(source, target, weight)

    def rename_node(self, node: str, new_id: str) -> bool:
        if self.states:
            return False
        if (
            node not in self.graph
            or not isinstance(new_id, str)
            or not new_id
            or new_id.strip() != new_id
            or new_id in self.graph
        ):
            self.editor.error_label.setText(
                "Elige un nodo existente y un ID texto único disponible."
            )
            return False
        snapshot = self._snapshot(f"Cambiar ID de {node} a {new_id}")
        snapshot.graph = nx.relabel_nodes(snapshot.graph, {node: new_id}, copy=True)
        snapshot.positions[new_id] = snapshot.positions.pop(node)
        if snapshot.start == node:
            snapshot.start = new_id
        if snapshot.target == node:
            snapshot.target = new_id
        if self._commit_edit(snapshot):
            self.editor.select_node(new_id)
            return True
        return False

    def delete_node(self, node: str) -> bool:
        if self.states:
            return False
        if node not in self.graph or len(self.graph) == 1:
            self.editor.error_label.setText("El grafo debe conservar al menos un nodo.")
            return False
        snapshot = self._snapshot(f"Eliminar nodo {node}")
        snapshot.graph.remove_node(node)
        del snapshot.positions[node]
        ordered = sorted_node_ids(snapshot.graph)
        if snapshot.start == node:
            snapshot.start = ordered[0]
        if snapshot.target == node:
            snapshot.target = ordered[-1]
        return self._commit_edit(snapshot)

    def set_edge(self, source: str, target: str, weight: float, key: int | None = None) -> bool:
        if self.states:
            return False
        if (
            source not in self.graph
            or target not in self.graph
            or source == target
            or isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(weight)
            or (weight < 0 and not self.graph.is_directed())
        ):
            self.editor.error_label.setText(
                "Conecta dos nodos distintos con un peso finito; negativo solo en grafos dirigidos."
            )
            return False
        snapshot = self._snapshot(f"Guardar conexión {source}–{target}")
        if key is not None and not self.graph.has_edge(source, target, key):
            return False
        key = snapshot.graph.add_edge(source, target, key=key, weight=weight)
        if self._commit_edit(snapshot):
            self.editor.select_edge(source, target, key)
            return True
        return False

    def delete_edge(self, source: str, target: str, key: int = 0) -> bool:
        if self.states or not self.graph.has_edge(source, target, key):
            return False
        snapshot = self._snapshot(f"Eliminar conexión {source}–{target}")
        snapshot.graph.remove_edge(source, target, key)
        return self._commit_edit(snapshot)

    def initialize(self) -> None:
        if self.busy:
            return
        self.stop_playback()
        algorithm = self.algorithm_combo.currentText()
        estimated = (
            len(self.graph) ** 3
            if algorithm == "Floyd-Warshall"
            else len(self.graph) * self.graph.number_of_edges() * 2
        )
        if estimated > 5000:
            from graph_visualizer.ui.worker import AlgorithmWorker

            self.busy = True
            self._sync_history()
            self.cancel_button.setEnabled(True)
            self.cancel_button.show()
            self.centralWidget().setEnabled(False)
            self.statusBar().showMessage("Calculando estados en segundo plano…")
            self.worker = AlgorithmWorker(
                self.graph.copy(),
                algorithm,
                self.start,
                self.target,
                self.detail_checkbox.isChecked(),
                self.early_stop.isChecked(),
                self,
            )
            revision = self.revision
            self.worker.ready.connect(lambda states: self.execution_ready(states, revision))
            self.worker.failed.connect(self.execution_failed)
            self.worker.cancelled.connect(self.execution_cancelled)
            self.worker.finished.connect(self.worker.deleteLater)
            self.worker.start()
            return
        try:
            if self.algorithm_combo.currentText() == "Floyd-Warshall":
                from graph_visualizer.core.floyd_warshall import floyd_warshall_steps

                self.states = floyd_warshall_steps(
                    self.graph, detailed=self.detail_checkbox.isChecked()
                )
            elif self.algorithm_combo.currentText() == "Bellman-Ford":
                from graph_visualizer.core.bellman_ford import bellman_ford_steps

                self.states = bellman_ford_steps(
                    self.graph, self.start, early_stop=self.early_stop.isChecked()
                )
            elif self.algorithm_combo.currentText() == "A*":
                from graph_visualizer.core.astar import astar_steps

                self.states = astar_steps(
                    self.graph, self.start, self.target, detailed=self.detail_checkbox.isChecked()
                )
            else:
                self.states = dijkstra_steps(
                    self.graph, self.start, self.target, detailed=self.detail_checkbox.isChecked()
                )
        except ValueError as error:
            QMessageBox.warning(self, "No se pudo iniciar el algoritmo", str(error))
            return
        self.execution_ready(self.states)

    def execution_failed(self, message):
        self.busy = False
        self.worker = None
        self.cancel_button.hide()
        self.centralWidget().setEnabled(True)
        self._sync_history()
        self.statusBar().showMessage("No se pudo calcular. Revisa el grafo y vuelve a iniciar.")
        QMessageBox.warning(self, "No se pudo calcular", message)

    def execution_ready(self, states, revision=None):
        self.busy = False
        self.worker = None
        self.cancel_button.hide()
        self.centralWidget().setEnabled(True)
        if revision is not None and revision != self.revision:
            self._sync_history()
            self.statusBar().showMessage("El grafo cambió durante el cálculo. Inicia de nuevo.")
            return
        self.states = states
        self.early_stop.setEnabled(False)
        self.statusBar().showMessage(f"Ejecución preparada · {len(states)} pasos disponibles")
        self.refresh_navigation()
        self.graph_view.set_editable(False)
        self.start_combo.setEnabled(self.algorithm_combo.currentText() == "Floyd-Warshall")
        self.target_combo.setEnabled(self.algorithm_combo.currentText() not in {"Dijkstra", "A*"})
        self._refresh_swap_button()
        self.run_button.setEnabled(False)
        self.copy_image_button.setEnabled(True)
        self.bookmark_button.setEnabled(True)
        self.reset_button.setEnabled(True)
        self.tabs.setCurrentIndex(0)
        self.tabs.setTabEnabled(1, False)
        self.editor.setEnabled(False)
        self.mode_label.setText("MODO ALGORITMO")
        self.execution_card.show()
        algorithm = self.algorithm_combo.currentText()
        self.results_title.setText(
            "Matrices · Floyd-Warshall"
            if algorithm == "Floyd-Warshall"
            else "Tablas · " + algorithm
        )
        self.results_panel.setVisible(algorithm != "Dijkstra")
        self.view_hint.setText(
            "Arrastra el fondo para mover la vista · Usa la rueda para acercar o alejar"
        )
        for action in self.export_actions:
            action.setEnabled(True)
            action.setToolTip("Exportar estados de " + algorithm)
        self._sync_history()
        self.show_state(0)
        self.centralWidget().layout().activate()
        if (
            algorithm != "Dijkstra"
            and self.visual_splitter.orientation() == Qt.Orientation.Horizontal
        ):
            tables = (
                self.matrix_panel.tables
                if algorithm == "Floyd-Warshall"
                else [self.state_panel.table, self.state_panel.arcs]
            )
            preferred_width = max(
                table.horizontalHeader().length() + table.verticalHeader().sizeHint().width() + 64
                for table in tables
            )
            results_width = max(280, min(preferred_width, int(self.visual_splitter.width() * 0.45)))
            self.visual_splitter.setSizes(
                [self.visual_splitter.width() - results_width, results_width]
            )
        self.graph_view.fit_graph()
        self.refresh_export_preview()

    def change_graph_type(self, directed):
        if self.states or self.busy:
            return
        from graph_visualizer.core.graph import convert_graph

        snapshot = self._snapshot("Cambiar tipo de grafo")
        try:
            snapshot.graph = convert_graph(self.graph, directed)
            self._commit_edit(snapshot)
        except ValueError as error:
            self.editor.set_graph(self.graph)
            self.editor.error_label.setText(str(error))

    def stop_playback(self):
        self.play_timer.stop()
        if hasattr(self, "play_button"):
            self._refresh_play_button()

    def _refresh_play_button(self) -> None:
        self.play_button.setText(
            "Ⅱ Pausar"
            if self.play_timer.isActive()
            else "↻ Repetir recorrido"
            if self.states and self.state_index == len(self.states) - 1
            else "▶ Reproducir"
        )

    def toggle_playback(self):
        if self.busy:
            return
        if self.play_timer.isActive():
            self.stop_playback()
        elif self.states:
            if self.state_index == len(self.states) - 1:
                self.show_state(0)
            self.play_timer.start(self.speed.value())
            self._refresh_play_button()

    def refresh_navigation(self):
        with QSignalBlocker(self.jump_step):
            self.jump_step.setRange(0, max(0, len(self.states) - 1))
        self.jump_phase.clear()
        seen = set()
        for index, state in enumerate(self.states):
            key = (state.iteration, state.phase)
            if key not in seen:
                self.jump_phase.addItem(f"{state.iteration} · {state.phase}", index)
                seen.add(key)
        for control in (
            self.first_button,
            self.last_button,
            self.jump_step,
            self.jump_phase,
            self.play_button,
        ):
            control.setEnabled(bool(self.states))

    def closeEvent(self, event):
        self.stop_playback()
        if self.busy:
            self.statusBar().showMessage("Espera a que termine la operación antes de cerrar.")
            event.ignore()
            return
        self.cancel_export_preview()
        self.persist_preferences()
        super().closeEvent(event)

    def navigate_step(self, offset):
        if self.states and not self.busy:
            self.stop_playback()
            self.show_state(self.state_index + offset)

    def execution_cancelled(self):
        self.worker = None
        self.busy = False
        self.cancel_button.hide()
        self.centralWidget().setEnabled(True)
        self._sync_history()
        self.statusBar().showMessage(
            "Cálculo cancelado. Puedes editar el grafo o iniciar de nuevo."
        )

    def cancel_operation(self):
        if not self.busy:
            return
        if self.worker is not None:
            self.worker.requestInterruption()
            self.cancel_button.setEnabled(False)
            self.statusBar().showMessage("Cancelando cálculo…")
        elif self.export_generator is not None:
            self.export_generator.close()
            self.export_generator = None
            self.busy = False
            self.centralWidget().setEnabled(True)
            self.cancel_button.hide()
            self._sync_history()
            self.refresh_export_preview()
            self.statusBar().showMessage(
                "Exportación cancelada. No se publicaron archivos incompletos."
            )

    def copy_current_image(self):
        if not self.states or self.busy:
            return
        from PySide6.QtWidgets import QApplication

        from graph_visualizer.export.image_exporter import render_state

        try:
            image = render_state(
                self.graph,
                self.graph_view.positions(),
                self.states[self.state_index],
                self.start,
                self.target,
                self.state_index,
                len(self.states),
                **self.export_options(),
            )
            QApplication.clipboard().setImage(image)
            self.statusBar().showMessage("Imagen del paso visible copiada al portapapeles.", 5000)
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "No se pudo copiar la imagen", str(error))

    def open_graph_data(self):
        if self.busy:
            return
        from graph_visualizer.ui.graph_data_dialog import GraphDataDialog

        self.stop_playback()
        GraphDataDialog(self).open()

    def toggle_bookmark(self):
        if not self.states or self.busy:
            return
        step = self.states[self.state_index].step
        if step in self.bookmarks:
            self.bookmarks.remove(step)
        else:
            self.bookmarks.add(step)
        self.bookmark_button.setText("Quitar marca" if step in self.bookmarks else "Marcar paso")
        self.bookmark_button.setChecked(step in self.bookmarks)
        self.refresh_export_preview()

    def algorithm_changed(self):
        self.reset()
        bellman = self.algorithm_combo.currentText() == "Bellman-Ford"
        self.early_stop.setVisible(bellman)
        self.detail_checkbox.setVisible(not bellman)
        self.detail_checkbox.setChecked(self.algorithm_combo.currentText() != "Floyd-Warshall")
        self.run_button.setText("Iniciar " + self.algorithm_combo.currentText())
        algorithm = self.algorithm_combo.currentText()
        self.detail_checkbox.setText("Por comparación")
        self.algorithm_hint.setText(
            {
                "A*": "Prioridad f = g + h. h = saltos mínimos al destino × menor peso. "
                "Heurística admisible; con peso mínimo cero equivale a Dijkstra.",
                "Dijkstra": "Ruta mínima entre el origen y el destino.",
                "Bellman-Ford": "Desde el origen a todos los nodos. Admite pesos negativos.",
                "Floyd-Warshall": "Todos los pares. Origen y destino solo consultan una ruta.",
            }[algorithm]
        )
        self.start_label.setText("Consultar desde" if algorithm == "Floyd-Warshall" else "Origen")
        self.target_label.setText(
            "Consultar hasta" if algorithm not in {"Dijkstra", "A*"} else "Destino"
        )
        self.start_combo.setAccessibleName(self.start_label.text())
        self.target_combo.setAccessibleName(self.target_label.text())
        self.export_detail.setEnabled(algorithm != "Bellman-Ford")
        self.export_detail.setToolTip(
            "Bellman-Ford exporta un paso por arco."
            if algorithm == "Bellman-Ford"
            else "Elige el detalle de las imágenes sin cambiar el paso visible."
        )
        self.detail_checkbox.setToolTip(
            "Desmarcado: una iteración completa de k"
            if algorithm == "Floyd-Warshall"
            else "Desmarcado: resumen por nodo"
        )
        self.legend_grid.itemAtPosition(1, 0).widget().setVisible(algorithm in {"Dijkstra", "A*"})
        self.notation.setText(
            "Distancias desde el origen consultado · k: intermedio"
            if algorithm == "Floyd-Warshall"
            else "[distancia, predecesor] · Negritas: mejora"
        )

    def change_detail(self):
        self.stop_playback()
        if self.states:
            from graph_visualizer.core.models import StateView

            step = self.states[self.state_index].step
            self.states = StateView(self.states.events, self.detail_checkbox.isChecked())
            self.refresh_navigation()
            self.show_state(self.states.equivalent(step))
        self.refresh_export_preview()

    def show_state(self, index: int) -> None:
        if not self.states or not 0 <= index < len(self.states):
            return
        self.state_index = index
        marked = self.states[index].step in self.bookmarks
        self.bookmark_button.setChecked(marked)
        self.bookmark_button.setText("Quitar marca" if marked else "Marcar paso")
        phase_index = max(
            (i for i in range(self.jump_phase.count()) if self.jump_phase.itemData(i) <= index),
            default=0,
        )
        self.jump_phase.setCurrentIndex(phase_index)
        with QSignalBlocker(self.jump_step):
            self.jump_step.setValue(index)
        state = self.states[index]
        self.state_panel.show_state(self.graph, state)
        self.matrix_panel.show_state(state)
        final = index == len(self.states) - 1
        if final:
            self.stop_playback()
        self._refresh_play_button()
        self.graph_view.apply_state(state, self.start, self.target, final)
        self.previous_button.setEnabled(index > 0)
        self.next_button.setEnabled(not final)
        from graph_visualizer.core.dijkstra import route_description

        self.detail_label.setText(
            state.explanation + "\n" + route_description(state, self.start, self.target)
        )
        self.graph_view.setAccessibleDescription(self.detail_label.text())
        self.step_label.setText(
            f"{state.algorithm} · {state.phase} · "
            f"Iteración {state.iteration} · Paso {index} / {len(self.states) - 1}"
        )

    def reset(self) -> None:
        if self.busy:
            return
        self.stop_playback()
        for action in self.export_actions:
            action.setEnabled(False)
        self.states = []
        self.bookmarks.clear()
        self.cancel_export_preview()
        self.export_preview_cache.clear()
        self._refresh_play_button()
        self.state_panel.hide()
        self.matrix_panel.hide()
        self.results_panel.hide()
        self.execution_card.hide()
        self.state_index = 0
        self.refresh_navigation()
        self.graph_view.set_editable(True)
        self.graph_view.apply_state(None, self.start, self.target)
        self.start_combo.setEnabled(True)
        self.target_combo.setEnabled(True)
        self._refresh_swap_button()
        self.run_button.setEnabled(True)
        self.copy_image_button.setEnabled(False)
        self.bookmark_button.setEnabled(False)
        self.bookmark_button.setChecked(False)
        self.bookmark_button.setText("Marcar paso")
        self.early_stop.setEnabled(True)
        self.previous_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.reset_button.setEnabled(False)
        self.tabs.setTabEnabled(1, True)
        self.editor.setEnabled(True)
        self.mode_label.setText("MODO EDICIÓN")
        self.step_label.setText("Todo listo para empezar")
        self.detail_label.setText(
            "Acomoda los nodos, elige el inicio y el destino e inicia el recorrido.\n"
            "En Editar puedes cambiar nodos, conexiones y pesos."
        )
        self.view_hint.setText(
            "Doble clic en el fondo: agregar nodo · Arrastra el centro: mover nodo"
            " · Borde a nodo: conectar\nClic en una arista o su peso: editar"
            " · Arrastra el fondo: mover vista · Rueda: acercar"
        )
        self.graph_info.setText(
            f"{len(self.graph)} nodos · {self.graph.number_of_edges()} conexiones · "
            f"{'Dirigido' if self.graph.is_directed() else 'No dirigido'}"
        )
        self._sync_history()
        self.refresh_export_preview()

    def export(self, kind: ExportKind, *, preview_confirmed=False) -> None:
        if not self.states or self.busy:
            return
        self.stop_playback()
        self.cancel_export_preview()
        if self.preview_before_export.isChecked() and not preview_confirmed:
            self.show_export_sample(kind)
            return
        states = self._export_states(kind)
        if not states:
            return
        index = (
            self.state_index
            if kind == "current"
            else max(0, states.equivalent(self.states[self.state_index].step))
        )
        self.export_generator = export_job(
            self.graph.copy(),
            self.graph_view.positions(),
            states,
            self.start,
            self.target,
            index,
            kind,
            self.output_dir,
            output_format=self.export_format.currentData(),
            execution_settings=self.current_preset().settings,
            **self.export_options(),
        )
        self.export_kind = kind
        self.busy = True
        self._sync_history()
        self.export_notice.hide()
        self.cancel_button.setEnabled(True)
        self.cancel_button.show()
        self.persist_preferences()
        self.centralWidget().setEnabled(False)
        self.statusBar().showMessage("Generando páginas…")
        QTimer.singleShot(0, self.advance_export)

    def advance_export(self):
        if not self.busy or self.export_generator is None:
            return
        try:
            completed, total = next(self.export_generator)
            self.statusBar().showMessage(f"Exportando {completed}/{total}…")
            QTimer.singleShot(0, self.advance_export)
        except StopIteration as result:
            self.busy = False
            self.export_generator = None
            self.cancel_button.hide()
            self.centralWidget().setEnabled(True)
            self._sync_history()
            self.last_export_path = result.value
            if self.export_kind == "combined" and self.last_export_path.is_dir():
                self.export_preview_cache[self._export_preview_key(self._export_states())] = sum(
                    1 for _path in self.last_export_path.glob("*.png")
                )
            self.refresh_export_preview()
            self.export_notice_title.setText("✓ Exportación completada")
            self.export_notice_path.setText(str(result.value))
            self.export_notice.show()
            self.statusBar().showMessage(f"Exportación completada · {result.value}")
        except (OSError, ValueError) as error:
            self.busy = False
            self.export_generator = None
            self.cancel_button.hide()
            self.centralWidget().setEnabled(True)
            self._sync_history()
            self.statusBar().showMessage("No se pudo exportar")
            self.refresh_export_preview()
            QMessageBox.warning(self, "No se pudo exportar", str(error))

    def _open_folder(self, folder: Path) -> None:
        try:
            folder.mkdir(parents=True, exist_ok=True)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder.resolve()))):
                raise OSError(f"No se pudo abrir el explorador de archivos. Carpeta: {folder}")
        except OSError as error:
            QMessageBox.warning(self, "No se pudo abrir la carpeta", str(error))

    def open_output_folder(self) -> None:
        self._open_folder(self.output_dir)

    def open_last_export_folder(self) -> None:
        if self.last_export_path:
            path = self.last_export_path
            self._open_folder(path if path.is_dir() else path.parent)
