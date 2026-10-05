import math

import networkx as nx
from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import (
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from dijkstra_visualizer.ui.node_combo_box import NodeComboBox


class GraphEditor(QWidget):
    add_node_requested = Signal(object)
    rename_node_requested = Signal(object, object)
    delete_node_requested = Signal(object)
    save_edge_requested = Signal(object, object, float)
    delete_edge_requested = Signal(object, object)

    def __init__(self, graph: nx.Graph, parent=None):
        super().__init__(parent)
        self.graph = graph
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 12, 0, 0)
        column.setSpacing(10)
        self.node_combo = NodeComboBox()
        self.node_id = QLineEdit()
        self.node_id.setPlaceholderText("Número entero desde 0")
        form = QFormLayout()
        form.addRow("Nodo seleccionado", self.node_combo)
        form.addRow("ID nuevo", self.node_id)
        column.addLayout(form)
        self.add_button = QPushButton("Agregar nodo")
        self.rename_button = QPushButton("Cambiar ID")
        buttons = QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.rename_button)
        column.addLayout(buttons)
        self.delete_button = QPushButton("Eliminar nodo seleccionado")
        self.delete_button.setToolTip(
            "Elimina también sus conexiones. Puedes deshacer esta acción."
        )
        column.addWidget(self.delete_button)
        self.add_button.clicked.connect(lambda: self._node_action(False))
        self.rename_button.clicked.connect(lambda: self._node_action(True))
        self.node_id.returnPressed.connect(self.rename_button.click)
        self.delete_button.clicked.connect(
            lambda: self.delete_node_requested.emit(self.node_combo.currentData())
        )
        heading = QLabel("Conexiones y pesos")
        heading.setObjectName("section")
        column.addWidget(heading)
        self.source_combo, self.target_combo = NodeComboBox(), NodeComboBox()
        self.weight_input = QLineEdit("1")
        self.weight_input.setPlaceholderText("Ej. 4.5")
        edge_form = QFormLayout()
        edge_form.addRow("Desde", self.source_combo)
        edge_form.addRow("Hasta", self.target_combo)
        edge_form.addRow("Peso", self.weight_input)
        column.addLayout(edge_form)
        self.edge_info = QLabel()
        self.edge_info.setWordWrap(True)
        column.addWidget(self.edge_info)
        self.save_edge_button = QPushButton("Guardar conexión")
        self.delete_edge_button = QPushButton("Eliminar conexión")
        column.addWidget(self.save_edge_button)
        column.addWidget(self.delete_edge_button)
        self.save_edge_button.clicked.connect(self._save_edge)
        self.weight_input.returnPressed.connect(self.save_edge_button.click)
        self.delete_edge_button.clicked.connect(
            lambda: self.delete_edge_requested.emit(
                self.source_combo.currentData(), self.target_combo.currentData()
            )
        )
        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.setWordWrap(True)
        column.addWidget(self.error_label)
        hint = QLabel("Los cambios se guardan automáticamente.\nUsa ↶ / ↷ para deshacer o rehacer.")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        column.addWidget(hint)
        column.addStretch()
        self.set_graph(graph)
        self.source_combo.currentIndexChanged.connect(self._edge_selection_changed)
        self.target_combo.currentIndexChanged.connect(self._edge_selection_changed)

    def set_graph(self, graph: nx.Graph) -> None:
        self.graph = graph
        for combo in (self.node_combo, self.source_combo, self.target_combo):
            selected = combo.currentData()
            with QSignalBlocker(combo):
                combo.clear()
                for node in sorted(graph):
                    combo.addItem(f"Nodo {node}", node)
                index = combo.findData(selected)
                combo.setCurrentIndex(index if index >= 0 else 0)
        if self.source_combo.currentData() == self.target_combo.currentData() and len(graph) > 1:
            self.target_combo.setCurrentIndex(1 if self.source_combo.currentIndex() == 0 else 0)
        self.node_id.setText(str(max(graph) + 1))
        self.delete_button.setEnabled(len(graph) > 1)
        self.error_label.clear()
        self._edge_selection_changed()

    def select_node(self, node: int) -> None:
        self.node_combo.setCurrentIndex(self.node_combo.findData(node))
        self.source_combo.setCurrentIndex(self.source_combo.findData(node))

    def _node_action(self, rename: bool) -> None:
        try:
            node = int(self.node_id.text())
            if node < 0:
                raise ValueError
        except ValueError:
            self.error_label.setText("El ID debe ser un número entero mayor o igual a cero.")
            return
        self.error_label.clear()
        if rename:
            self.rename_node_requested.emit(self.node_combo.currentData(), node)
        else:
            self.add_node_requested.emit(node)

    def _edge_selection_changed(self) -> None:
        source, target = self.source_combo.currentData(), self.target_combo.currentData()
        exists = self.graph.has_edge(source, target)
        self.weight_input.setText(str(self.graph[source][target]["weight"]) if exists else "1")
        self.edge_info.setText(
            "Conexión existente: puedes cambiar su peso."
            if exists
            else "Nueva conexión sin dirección."
        )
        self.save_edge_button.setEnabled(source != target)
        self.delete_edge_button.setEnabled(exists)

    def _save_edge(self) -> None:
        try:
            weight = float(self.weight_input.text())
            if not math.isfinite(weight) or weight <= 0:
                raise ValueError
        except ValueError:
            self.error_label.setText(
                "El peso debe ser un número positivo y finito. Usa punto decimal."
            )
            return
        self.error_label.clear()
        self.save_edge_requested.emit(
            self.source_combo.currentData(), self.target_combo.currentData(), weight
        )
