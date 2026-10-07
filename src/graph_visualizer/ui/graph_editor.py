import math

import networkx as nx
from PySide6.QtCore import QSignalBlocker, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from graph_visualizer.ui.node_combo_box import NodeComboBox
from graph_visualizer.ui.section_card import SectionCard


class GraphEditor(QWidget):
    graph_type_requested = Signal(bool)
    add_node_requested = Signal(object)
    rename_node_requested = Signal(object, object)
    delete_node_requested = Signal(object)
    save_edge_requested = Signal(object, object, float, object)
    delete_edge_requested = Signal(object, object, object)

    def __init__(self, graph: nx.Graph, parent=None):
        super().__init__(parent)
        self.graph = graph
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 4, 0, 4)
        column.setSpacing(12)
        graph_card = SectionCard("Tipo de grafo")
        self.graph_type = QComboBox()
        self.graph_type.addItems(["No dirigido", "Dirigido"])
        self.graph_type.setToolTip(
            "No dirigido → dirigido: dos arcos por conexión.\n"
            "Dirigido → no dirigido: conserva todos los arcos como conexiones paralelas "
            "y reasigna claves en conflicto. Rechaza pesos negativos."
        )
        graph_card.content.addWidget(self.graph_type)
        self.graph_type_hint = QLabel()
        self.graph_type_hint.setObjectName("hint")
        self.graph_type_hint.setWordWrap(True)
        graph_card.content.addWidget(self.graph_type_hint)
        column.addWidget(graph_card)
        self.graph_type.currentIndexChanged.connect(
            lambda index: self.graph_type_requested.emit(index == 1)
        )

        nodes = SectionCard("Nodos")
        self.node_combo = NodeComboBox()
        self.node_id = QLineEdit()
        self.node_id.setPlaceholderText("Nombre, letra o número")
        form = QFormLayout()
        form.addRow("Seleccionado", self.node_combo)
        form.addRow("ID nuevo", self.node_id)
        nodes.content.addLayout(form)
        self.add_button = QPushButton("Agregar nodo")
        self.rename_button = QPushButton("Cambiar ID")
        buttons = QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.rename_button)
        nodes.content.addLayout(buttons)
        self.delete_button = QPushButton("Eliminar nodo seleccionado")
        self.delete_button.setToolTip(
            "Elimina también sus conexiones. Puedes deshacer esta acción."
        )
        self.delete_button.setObjectName("destructive")
        nodes.content.addWidget(self.delete_button)
        column.addWidget(nodes)
        self.add_button.clicked.connect(lambda: self._node_action(False))
        self.rename_button.clicked.connect(lambda: self._node_action(True))
        self.node_id.returnPressed.connect(self.rename_button.click)
        self.delete_button.clicked.connect(
            lambda: self.delete_node_requested.emit(self.node_combo.currentData())
        )

        connections = SectionCard("Conexiones y pesos")
        self.source_combo, self.target_combo = NodeComboBox(), NodeComboBox()
        self.weight_input = QLineEdit("1")
        self.weight_input.setPlaceholderText("Ej. 4.5")
        edge_form = QFormLayout()
        edge_form.addRow("Desde", self.source_combo)
        edge_form.addRow("Hasta", self.target_combo)
        self.edge_combo = NodeComboBox()
        edge_form.addRow("Conexión", self.edge_combo)
        edge_form.addRow("Peso", self.weight_input)
        connections.content.addLayout(edge_form)
        self.edge_info = QLabel()
        self.edge_info.setObjectName("hint")
        self.edge_info.setWordWrap(True)
        connections.content.addWidget(self.edge_info)
        self.save_edge_button = QPushButton("Guardar peso")
        self.save_edge_button.setObjectName("primary")
        self.delete_edge_button = QPushButton("Eliminar")
        self.delete_edge_button.setObjectName("destructive")
        self.add_edge_button = QPushButton("Agregar paralela")
        self.add_edge_button.setToolTip("Crea una conexión paralela con su propio ID y peso.")
        save_row = QHBoxLayout()
        self.delete_edge_button.setToolTip("Elimina la conexión seleccionada.")
        save_row.addWidget(self.save_edge_button)
        save_row.addWidget(self.delete_edge_button)
        connections.content.addLayout(save_row)
        connections.content.addWidget(self.add_edge_button)
        column.addWidget(connections)
        self.save_edge_button.clicked.connect(lambda: self._save_edge())
        self.add_edge_button.clicked.connect(lambda: self._save_edge(new=True))
        self.edge_combo.currentIndexChanged.connect(self._weight_changed)
        self.weight_input.returnPressed.connect(self.save_edge_button.click)
        self.delete_edge_button.clicked.connect(
            lambda: self.delete_edge_requested.emit(
                self.source_combo.currentData(),
                self.target_combo.currentData(),
                self.edge_combo.currentData(),
            )
        )
        self.error_label = QLabel()
        self.error_label.setObjectName("error")
        self.error_label.setWordWrap(True)
        column.addWidget(self.error_label)
        hint = QLabel("Autoguardado activo · Deshacer / rehacer: ↶ / ↷")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        column.addWidget(hint)
        column.addStretch()
        self.set_graph(graph)
        self.source_combo.currentIndexChanged.connect(self._edge_selection_changed)
        self.target_combo.currentIndexChanged.connect(self._edge_selection_changed)

    def set_graph(self, graph: nx.Graph) -> None:
        self.graph = graph
        self.graph_type_hint.setText(
            "Con flechas · Admite pesos negativos"
            if graph.is_directed()
            else "Ambos sentidos · Pesos no negativos"
        )
        with QSignalBlocker(self.graph_type):
            self.graph_type.setCurrentIndex(int(graph.is_directed()))
        for combo in (self.node_combo, self.source_combo, self.target_combo):
            combo.set_nodes(graph)
        if self.source_combo.currentData() == self.target_combo.currentData() and len(graph) > 1:
            self.target_combo.setCurrentIndex(1 if self.source_combo.currentIndex() == 0 else 0)
        self.node_id.setText(next(str(i) for i in range(len(graph) + 1) if str(i) not in graph))
        self.delete_button.setEnabled(len(graph) > 1)
        self.error_label.clear()
        self._edge_selection_changed()

    def select_node(self, node: str) -> None:
        self.node_combo.setCurrentIndex(self.node_combo.findData(node))
        self.source_combo.setCurrentIndex(self.source_combo.findData(node))

    def _node_action(self, rename: bool) -> None:
        try:
            node = self.node_id.text().strip()
            if not node:
                raise ValueError
        except ValueError:
            self.error_label.setText("El ID debe ser un texto no vacío.")
            return
        self.error_label.clear()
        if rename:
            self.rename_node_requested.emit(self.node_combo.currentData(), node)
        else:
            self.add_node_requested.emit(node)

    def select_edge(self, source: str, target: str, key: int) -> None:
        self.source_combo.setCurrentIndex(self.source_combo.findData(source))
        self.target_combo.setCurrentIndex(self.target_combo.findData(target))
        self.edge_combo.setCurrentIndex(self.edge_combo.findData(key))

    def _edge_selection_changed(self) -> None:
        source, target = self.source_combo.currentData(), self.target_combo.currentData()
        selected = self.edge_combo.currentData()
        with QSignalBlocker(self.edge_combo):
            self.edge_combo.clear()
            for key in sorted(self.graph.get_edge_data(source, target, default={})):
                self.edge_combo.addItem(f"Conexión {key}", key)
            index = self.edge_combo.findData(selected)
            self.edge_combo.setCurrentIndex(index if index >= 0 else 0)
        exists = self.edge_combo.count() > 0
        self.save_edge_button.setText("Guardar peso" if exists else "Crear conexión")
        self.add_edge_button.setVisible(exists)
        self.edge_info.setText(
            "Edita la seleccionada o agrega una conexión paralela."
            if exists
            else "Guarda el peso para crear una conexión dirigida."
            if self.graph.is_directed()
            else "Guarda el peso para conectar estos nodos."
        )
        self.save_edge_button.setEnabled(source != target)
        self.add_edge_button.setEnabled(source != target)
        self.delete_edge_button.setEnabled(exists)
        self._weight_changed()

    def _weight_changed(self) -> None:
        source, target, key = (
            self.source_combo.currentData(),
            self.target_combo.currentData(),
            self.edge_combo.currentData(),
        )
        self.weight_input.setText(
            str(self.graph[source][target][key]["weight"]) if key is not None else "1"
        )

    def _save_edge(self, new: bool = False) -> None:
        try:
            weight = float(self.weight_input.text())
            if not math.isfinite(weight) or (weight < 0 and not self.graph.is_directed()):
                raise ValueError
        except ValueError:
            self.error_label.setText(
                "El peso debe ser finito; negativo solo en grafos dirigidos. Usa punto decimal."
            )
            return
        self.error_label.clear()
        self.save_edge_requested.emit(
            self.source_combo.currentData(),
            self.target_combo.currentData(),
            weight,
            None if new else self.edge_combo.currentData(),
        )
