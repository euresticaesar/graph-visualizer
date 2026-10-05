import math
from dataclasses import dataclass
from pathlib import Path

import networkx as nx
from PySide6.QtCore import QSignalBlocker, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from dijkstra_visualizer.core.dijkstra import dijkstra_steps, reconstruct_path
from dijkstra_visualizer.core.graph import validate_graph
from dijkstra_visualizer.core.models import DijkstraState
from dijkstra_visualizer.export.image_exporter import ExportKind, export_graph
from dijkstra_visualizer.io.graph_io import load_graph, save_graph_data
from dijkstra_visualizer.io.layout_io import PositionMap, load_layout, save_layout
from dijkstra_visualizer.paths import DATA_DIR, OUTPUT_DIR
from dijkstra_visualizer.ui.graph_editor import GraphEditor
from dijkstra_visualizer.ui.graph_view import GraphView
from dijkstra_visualizer.ui.node_combo_box import NodeComboBox
from dijkstra_visualizer.ui.node_item import format_distance


class ControlTabs(QTabWidget):
    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.tabBar().setFixedWidth(self.contentsRect().width())


@dataclass
class EditSnapshot:
    graph: nx.Graph
    positions: PositionMap
    start: int
    target: int
    description: str


class MainWindow(QMainWindow):
    def __init__(self, data_dir: Path = DATA_DIR, output_dir: Path = OUTPUT_DIR):
        super().__init__()
        self.data_dir, self.output_dir = data_dir, output_dir
        self.graph = load_graph(data_dir / "nodes.csv", data_dir / "edges.csv")
        positions = load_layout(data_dir / "layout.json", self.graph)
        self.states: list[DijkstraState] = []
        self.state_index = 0
        self.history: list[EditSnapshot] = []
        self.history_index = 0
        self.last_export_path: Path | None = None
        self.setWindowTitle("Visualizador de Dijkstra · Fundamentos de IA")
        self.resize(1380, 940)
        self.setMinimumSize(1040, 740)
        self.graph_view = GraphView(self.graph, positions)
        self.graph_view.layout_changed.connect(self._save_layout)
        self._build_ui()
        self._apply_style()
        self.history.append(self._snapshot("Estado inicial"))
        self.reset()
        QTimer.singleShot(0, self.graph_view.fit_graph)

    @property
    def start(self) -> int:
        return self.start_combo.currentData()

    @property
    def target(self) -> int:
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
        layout.setContentsMargins(12, 8, 12, 12)
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
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(340)
        controls = QVBoxLayout(sidebar)
        controls.setContentsMargins(20, 20, 20, 16)
        controls.setSpacing(12)
        title = QLabel("Dijkstra")
        title.setObjectName("title")
        controls.addWidget(title)
        self.mode_label = QLabel()
        self.mode_label.setObjectName("mode")
        controls.addWidget(self.mode_label)
        self.tabs = ControlTabs()
        self.tabs.tabBar().setExpanding(True)
        self.tabs.addTab(self._scroll_page(self._algorithm_controls()), "Recorrido")
        self.editor = GraphEditor(self.graph)
        self.tabs.addTab(self._scroll_page(self.editor), "Editar grafo")
        self.editor.add_node_requested.connect(self.add_node)
        self.editor.rename_node_requested.connect(self.rename_node)
        self.editor.delete_node_requested.connect(self.delete_node)
        self.editor.save_edge_requested.connect(self.set_edge)
        self.editor.delete_edge_requested.connect(self.delete_edge)
        self.graph_view.node_selected.connect(self.editor.select_node)
        controls.addWidget(self.tabs, 1)

        self.legend_grid = QGridLayout()
        self.legend_grid.setHorizontalSpacing(16)
        self.legend_grid.setVerticalSpacing(8)
        for index, (symbol, color, text) in enumerate(
            [
                ("●", "#64748b", "Sin alcanzar"),
                ("●", "#b48412", "Tentativo"),
                ("●", "#329758", "Visitado"),
                ("●", "#18794e", "Actual"),
                ("○", "#dc3545", "Destino"),
                ("━", "#087e8b", "Ruta final"),
            ]
        ):
            label = QLabel(f'<span style="color:{color}">{symbol}</span> {text}')
            self.legend_grid.addWidget(label, index // 2, index % 2)
        self.legend_grid.setColumnStretch(0, 1)
        self.legend_grid.setColumnStretch(1, 1)
        controls.addLayout(self.legend_grid)
        notation = QLabel("[distancia, predecesor]\nNegritas: mejora en el paso actual")
        notation.setObjectName("hint")
        controls.addWidget(notation)
        export_row = QHBoxLayout()
        export_row.addWidget(QLabel("Exportar:"))
        self.export_actions: list[QAction] = []
        self.export_buttons: list[QToolButton] = []
        for _index, (label, kind) in enumerate(
            [
                ("Paso actual", "current"),
                ("Pasos separados", "all"),
                ("Imagen conjunta", "combined"),
                ("Ruta final", "final"),
            ]
        ):
            action = self._action(label, lambda checked=False, kind=kind: self.export(kind))
            action.setToolTip("Inicia Dijkstra para exportar las imágenes a output/")
            self.export_actions.append(action)
            button = self._action_button(action)
            self.export_buttons.append(button)
            export_row.addWidget(button, 1)
        footer = QHBoxLayout()
        self.output_button = QPushButton("Abrir carpeta")
        self.output_button.setToolTip("Abrir la carpeta de exportaciones")
        self.output_button.clicked.connect(self.open_output_folder)
        self.exit_button = QPushButton("Salir")
        self.exit_button.setShortcut("Ctrl+Q")
        self.exit_button.clicked.connect(self.close)
        footer.addWidget(self.output_button, 2)
        footer.addWidget(self.exit_button, 1)
        controls.addLayout(footer)

        graph_panel = QWidget()
        graph_column = QVBoxLayout(graph_panel)
        graph_column.setContentsMargins(14, 12, 14, 12)
        toolbar = QHBoxLayout()
        self.graph_info = QLabel()
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
        graph_column.addLayout(toolbar)
        self.view_hint = QLabel()
        self.view_hint.setObjectName("hint")
        graph_column.addWidget(self.view_hint)
        self.export_notice = QFrame()
        self.export_notice.setObjectName("exportNotice")
        notice_row = QHBoxLayout(self.export_notice)
        notice_text = QVBoxLayout()
        self.export_notice_title = QLabel("✓ Exportación completada")
        self.export_notice_title.setObjectName("section")
        notice_text.addWidget(self.export_notice_title)
        self.export_notice_path = QLabel()
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
        graph_column.addWidget(self.graph_view, 1)
        graph_column.addLayout(export_row)
        row.addWidget(sidebar)
        row.addWidget(graph_panel, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage("Grafo cargado. Los cambios se guardan automáticamente.")

    def _algorithm_controls(self) -> QWidget:
        page = QWidget()
        controls = QVBoxLayout(page)
        controls.setContentsMargins(0, 12, 4, 8)
        controls.setSpacing(10)
        self.start_combo, self.target_combo = NodeComboBox(), NodeComboBox()
        for node in sorted(self.graph):
            self.start_combo.addItem(f"Nodo {node}", node)
            self.target_combo.addItem(f"Nodo {node}", node)
        self.target_combo.setCurrentIndex(self.target_combo.count() - 1)
        for label, combo in (
            ("Nodo de inicio", self.start_combo),
            ("Nodo de destino", self.target_combo),
        ):
            controls.addWidget(QLabel(label))
            controls.addWidget(combo)
            combo.currentIndexChanged.connect(self._selection_changed)
        self.run_button = QPushButton("Iniciar Dijkstra")
        self.run_button.setObjectName("primary")
        self.run_button.clicked.connect(self.initialize)
        controls.addWidget(self.run_button)
        navigation = QHBoxLayout()
        self.previous_button, self.next_button = (
            QPushButton("← Anterior"),
            QPushButton("Siguiente →"),
        )
        self.previous_button.clicked.connect(lambda: self.show_state(self.state_index - 1))
        self.next_button.clicked.connect(lambda: self.show_state(self.state_index + 1))
        navigation.addWidget(self.previous_button)
        navigation.addWidget(self.next_button)
        controls.addLayout(navigation)
        self.reset_button = QPushButton("Volver a editar")
        self.reset_button.clicked.connect(self.reset)
        controls.addWidget(self.reset_button)
        self.step_label = QLabel()
        self.step_label.setObjectName("step")
        controls.addWidget(self.step_label)
        self.detail_label = QLabel()
        self.detail_label.setWordWrap(True)
        controls.addWidget(self.detail_label)
        controls.addStretch()
        return page

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #f8fafc; color: #172b4d; }
            QWidget { font-family: 'Sans Serif'; font-size: 13px; }
            QFrame#sidebar { background: #ffffff; border-right: 1px solid #dce3ed; }
            QFrame#sidebar QLabel { background: transparent; }
            QLabel#title { font-size: 30px; font-weight: 700; }
            QLabel#mode { color: #087e8b; font-weight: 600; }
            QLabel#section { font-weight: 600; padding-top: 4px; }
            QLabel#step { font-size: 17px; font-weight: 600; padding-top: 6px; }
            QLabel#hint { color: #64748b; font-size: 12px; }
            QLabel#error { color: #b42318; }
            QFrame#exportNotice {
                background: #e9f8ef; border: 1px solid #9fd7b5; border-radius: 6px;
            }
            QFrame#exportNotice QLabel { background: transparent; color: #14532d; }
            QPushButton, QToolButton, QComboBox, QLineEdit {
                background: #ffffff; border: 1px solid #cbd5e1;
                border-radius: 6px; padding: 8px 9px;
            }
            QToolButton#history { font-size: 20px; padding: 2px 8px; }
            QPushButton:hover, QToolButton:hover { background: #edf3f8; border-color: #94a3b8; }
            QPushButton#primary {
                background: #0f766e; color: white; border-color: #0f766e;
            }
            QPushButton#primary:hover { background: #115e59; }
            QPushButton:disabled, QPushButton#primary:disabled, QToolButton:disabled,
            QComboBox:disabled, QLineEdit:disabled {
                background: #f1f5f9; color: #94a3b8; border-color: #e2e8f0;
            }
            QComboBox QAbstractItemView { selection-background-color: #ccfbf1; }
            QStatusBar { border-top: 1px solid #dce3ed; color: #526179; }
            QScrollBar:vertical { background: #eef2f7; width: 10px; margin: 0; }
            QScrollBar::handle:vertical {
                background: #b6c3d3; min-height: 28px; border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: transparent;
            }
            QFrame#controlCard {
                background: #f1f5f9; border: 1px solid #e2e8f0; border-radius: 16px;
            }
            QScrollArea#controlScroll, QWidget#controlViewport, QWidget#controlPage {
                background: transparent; border: 0;
            }
            QWidget#controlPage QLabel { background: transparent; }
            QTabWidget::pane { border: 0; }
            QTabBar::tab {
                padding: 9px 18px; background: #f1f5f9; border: 1px solid #cbd5e1;
                min-width: 100px; margin-bottom: 8px;
            }
            QTabBar::tab:first {
                border-top-left-radius: 19px; border-bottom-left-radius: 19px;
                border-right: 0;
            }
            QTabBar::tab:last {
                border-top-right-radius: 19px; border-bottom-right-radius: 19px;
            }
            QTabBar::tab:selected { background: #d6eee8; color: #0f766e; }
            QTabBar::tab:disabled { color: #94a3b8; background: #f1f5f9; }
        """)

    def _snapshot(self, description: str) -> EditSnapshot:
        return EditSnapshot(
            self.graph.copy(), self.graph_view.positions(), self.start, self.target, description
        )

    def _restore(self, snapshot: EditSnapshot) -> None:
        topology_changed = not nx.utils.graphs_equal(self.graph, snapshot.graph)
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
            with QSignalBlocker(combo):
                if [combo.itemData(i) for i in range(combo.count())] != sorted(self.graph):
                    combo.clear()
                    for node in sorted(self.graph):
                        combo.addItem(f"Nodo {node}", node)
                combo.setCurrentIndex(combo.findData(selected))
        self.editor.set_graph(self.graph)
        self.graph_view.apply_state(None, self.start, self.target)
        self.graph_info.setText(
            f"{len(self.graph)} nodos · {self.graph.number_of_edges()} conexiones"
        )

    def _persist_and_restore(self, snapshot: EditSnapshot) -> bool:
        current = self.history[self.history_index]
        try:
            validate_graph(snapshot.graph)
            if not nx.utils.graphs_equal(current.graph, snapshot.graph):
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
        if self.states:
            return False
        current = self.history[self.history_index]
        if (
            nx.utils.graphs_equal(current.graph, snapshot.graph)
            and current.positions == snapshot.positions
            and (current.start, current.target) == (snapshot.start, snapshot.target)
        ):
            return False
        if not self._persist_and_restore(snapshot):
            return False
        del self.history[self.history_index + 1 :]
        self.history.append(snapshot)
        # Conserva hasta 100 acciones sin acumular copias indefinidamente.
        if len(self.history) > 101:
            self.history.pop(0)
        self.history_index = len(self.history) - 1
        self._sync_history()
        saved = current.positions != snapshot.positions or not nx.utils.graphs_equal(
            current.graph, snapshot.graph
        )
        message = snapshot.description + (" · Guardado" if saved else "")
        self.statusBar().showMessage(message, 5000)
        return True

    def _sync_history(self) -> None:
        editable = not self.states
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
        if self.states or self.history_index == 0:
            return
        description = self.history[self.history_index].description
        if self._persist_and_restore(self.history[self.history_index - 1]):
            self.history_index -= 1
            self._sync_history()
            self.statusBar().showMessage(f"Deshecho: {description}", 5000)

    def redo(self) -> None:
        if self.states or self.history_index >= len(self.history) - 1:
            return
        snapshot = self.history[self.history_index + 1]
        if self._persist_and_restore(snapshot):
            self.history_index += 1
            self._sync_history()
            self.statusBar().showMessage(f"Rehecho: {snapshot.description}", 5000)

    def _selection_changed(self) -> None:
        if not self.states and self.history:
            self._commit_edit(self._snapshot("Cambiar inicio o destino"))

    def _save_layout(self) -> None:
        self._commit_edit(self._snapshot("Mover nodos"))

    def add_node(self, node: int) -> bool:
        if self.states:
            return False
        if type(node) is not int or node < 0 or node in self.graph:
            self.editor.error_label.setText("Usa un ID entero desde 0 que todavía no exista.")
            return False
        snapshot = self._snapshot(f"Agregar nodo {node}")
        snapshot.graph.add_node(node)
        center = self.graph_view.mapToScene(self.graph_view.viewport().rect().center())
        x, y = center.x(), center.y()
        while any(math.hypot(x - px, y - py) < 100 for px, py in snapshot.positions.values()):
            x += 110
        snapshot.positions[node] = (x, y)
        if self._commit_edit(snapshot):
            self.editor.select_node(node)
            self.graph_view.ensureVisible(self.graph_view.nodes[node])
            return True
        return False

    def rename_node(self, node: int, new_id: int) -> bool:
        if self.states:
            return False
        if node not in self.graph or type(new_id) is not int or new_id < 0 or new_id in self.graph:
            self.editor.error_label.setText(
                "Elige un nodo existente y un ID entero desde 0 disponible."
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

    def delete_node(self, node: int) -> bool:
        if self.states:
            return False
        if node not in self.graph or len(self.graph) == 1:
            self.editor.error_label.setText("El grafo debe conservar al menos un nodo.")
            return False
        snapshot = self._snapshot(f"Eliminar nodo {node}")
        snapshot.graph.remove_node(node)
        del snapshot.positions[node]
        if snapshot.start == node:
            snapshot.start = min(snapshot.graph)
        if snapshot.target == node:
            snapshot.target = max(snapshot.graph)
        return self._commit_edit(snapshot)

    def set_edge(self, source: int, target: int, weight: float) -> bool:
        if self.states:
            return False
        if (
            source not in self.graph
            or target not in self.graph
            or source == target
            or isinstance(weight, bool)
            or not isinstance(weight, (int, float))
            or not math.isfinite(weight)
            or weight <= 0
        ):
            self.editor.error_label.setText(
                "Conecta dos nodos distintos con un peso positivo y finito."
            )
            return False
        snapshot = self._snapshot(f"Guardar conexión {source}–{target}")
        snapshot.graph.add_edge(source, target, weight=weight)
        return self._commit_edit(snapshot)

    def delete_edge(self, source: int, target: int) -> bool:
        if self.states or not self.graph.has_edge(source, target):
            return False
        snapshot = self._snapshot(f"Eliminar conexión {source}–{target}")
        snapshot.graph.remove_edge(source, target)
        return self._commit_edit(snapshot)

    def initialize(self) -> None:
        try:
            self.states = dijkstra_steps(self.graph, self.start, self.target)
        except ValueError as error:
            QMessageBox.warning(self, "No se pudo iniciar Dijkstra", str(error))
            return
        self.graph_view.set_editable(False)
        self.start_combo.setEnabled(False)
        self.target_combo.setEnabled(False)
        self.run_button.setEnabled(False)
        self.reset_button.setEnabled(True)
        self.tabs.setCurrentIndex(0)
        self.tabs.setTabEnabled(1, False)
        self.editor.setEnabled(False)
        self.mode_label.setText("MODO ALGORITMO")
        self.view_hint.setText(
            "Arrastra el fondo para mover la vista · Usa la rueda para acercar o alejar"
        )
        for action in self.export_actions:
            action.setEnabled(True)
        self._sync_history()
        self.show_state(0)

    def show_state(self, index: int) -> None:
        if not self.states or not 0 <= index < len(self.states):
            return
        self.state_index = index
        state = self.states[index]
        final = index == len(self.states) - 1
        self.graph_view.apply_state(state, self.start, self.target, final)
        self.previous_button.setEnabled(index > 0)
        self.next_button.setEnabled(not final)
        self.step_label.setText(f"Paso {index} / {len(self.states) - 1}")
        if final:
            path = reconstruct_path(state, self.start, self.target)
            self.detail_label.setText(
                f"Destino visitado · distancia {format_distance(state.distances[self.target])}\n"
                + " → ".join(map(str, path))
                if path
                else f"No hay ruta del nodo {self.start} al nodo {self.target}.\n"
                "Ya no quedan nodos alcanzables sin visitar."
            )
        elif state.current_node is None:
            self.detail_label.setText(
                "Nodo actual: —\nLa distancia inicial es 0; las demás son ∞.\n"
                "Siguiente elige la menor distancia tentativa."
            )
        else:
            updated = ", ".join(map(str, sorted(state.updated_nodes))) or "ninguna"
            self.detail_label.setText(
                f"Nodo actual: {state.current_node}\n"
                f"Nodos visitados: {len(state.visited)}\nEtiquetas mejoradas: {updated}"
            )

    def reset(self) -> None:
        for action in self.export_actions:
            action.setEnabled(False)
        self.states = []
        self.state_index = 0
        self.graph_view.set_editable(True)
        self.graph_view.apply_state(None, self.start, self.target)
        self.start_combo.setEnabled(True)
        self.target_combo.setEnabled(True)
        self.run_button.setEnabled(True)
        self.previous_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.reset_button.setEnabled(False)
        self.tabs.setTabEnabled(1, True)
        self.editor.setEnabled(True)
        self.mode_label.setText("MODO EDICIÓN")
        self.step_label.setText("Todo listo para empezar")
        self.detail_label.setText(
            "Acomoda los nodos, elige el inicio y el destino e inicia el recorrido.\n"
            "En Editar grafo puedes cambiar nodos, conexiones y pesos."
        )
        self.view_hint.setText(
            "Arrastra los nodos para acomodarlos · Fondo: mover vista · Rueda: acercar"
        )
        self.graph_info.setText(
            f"{len(self.graph)} nodos · {self.graph.number_of_edges()} conexiones"
        )
        self._sync_history()

    def export(self, kind: ExportKind) -> None:
        self.statusBar().showMessage("Generando imágenes…")
        self.statusBar().repaint()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            destination = export_graph(
                self.graph,
                self.graph_view.positions(),
                self.states,
                self.start,
                self.target,
                self.state_index,
                kind,
                self.output_dir,
            )
        except (OSError, ValueError) as error:
            QApplication.restoreOverrideCursor()
            self.statusBar().showMessage("No se pudo exportar", 8000)
            QMessageBox.warning(self, "No se pudo exportar", str(error))
            return
        else:
            QApplication.restoreOverrideCursor()
        self.last_export_path = destination
        count = len(self.states) if kind == "all" else 1
        self.export_notice_title.setText(
            f"✓ Exportación completada · {count} {'imágenes' if count != 1 else 'imagen'}"
        )
        self.export_notice_path.setText(str(destination))
        self.export_notice.show()
        self.statusBar().showMessage(f"Exportación completada · {destination}", 15000)
        QApplication.alert(self, 3000)

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
