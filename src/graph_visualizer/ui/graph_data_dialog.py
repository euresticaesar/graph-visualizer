"""Keyboard-accessible graph data and explicit manual positioning commands."""

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
)

from graph_visualizer.core.graph import edges_with_keys
from graph_visualizer.core.models import format_number


def table(headers, rows, *, editable_columns=()):
    widget = QTableWidget(len(rows), len(headers))
    widget.setHorizontalHeaderLabels(headers)
    widget.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    widget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    widget.setAlternatingRowColors(True)
    for row, values in enumerate(rows):
        for col, value in enumerate(values):
            item = QTableWidgetItem(str(value))
            item.setToolTip(str(value))
            if col not in editable_columns:
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            widget.setItem(row, col, item)
    widget.resizeColumnsToContents()
    return widget


class GraphDataDialog(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Datos del grafo y posiciones")
        self.resize(850, 650)
        self.owner = owner
        self.editable = not owner.states and not owner.busy
        self.nodes = tuple(sorted(owner.graph))
        positions = owner.graph_view.positions()
        state = owner.states[owner.state_index] if owner.states else None
        rows = []
        for node in self.nodes:
            distance = (
                state.matrix[state.nodes.index(owner.start)][state.nodes.index(node)]
                if state and state.algorithm == "Floyd-Warshall"
                else state.distances[node]
                if state
                else math.inf
            )
            status = (
                "Sin mínimo finito"
                if distance == -math.inf
                else "Actual"
                if state and node == state.current_node
                else "Fijado"
                if state and node in state.visited
                else "Tentativo"
                if math.isfinite(distance)
                else "Sin alcanzar"
            )
            roles = (["Origen"] if node == owner.start else []) + (
                ["Destino"] if node == owner.target else []
            )
            rows.append(
                [
                    node,
                    *positions[node],
                    format_number(distance) if state else "—",
                    state.predecessors.get(node) or "—" if state else "—",
                    " · ".join([*roles, status] if state else roles),
                ]
            )
        column = QVBoxLayout(self)
        hint = QLabel(
            "Selecciona varias filas con Ctrl o Shift para alinear o distribuir sus nodos. "
            "También puedes escribir coordenadas X e Y. Aplica para guardar una acción deshacible."
            if self.editable
            else "Consulta los IDs completos, conexiones y estado del paso visible con el teclado. "
            "Vuelve a editar para cambiar posiciones."
        )
        hint.setWordWrap(True)
        column.addWidget(hint)
        tabs = QTabWidget()
        self.node_table = table(
            ["Nodo", "X", "Y", "Distancia", "Predecesor", "Estado / rol"],
            rows,
            editable_columns=(1, 2) if self.editable else (),
        )
        self.node_table.setAccessibleName("Nodos, coordenadas y estado del recorrido")
        connections = table(
            ["Origen", "Destino", "ID", "Peso"],
            [(u, v, k, format_number(d["weight"])) for u, v, k, d in edges_with_keys(owner.graph)],
        )
        connections.setAccessibleName("Conexiones del grafo con IDs y pesos")
        tabs.addTab(self.node_table, "Nodos y posiciones")
        tabs.addTab(connections, "Conexiones")
        column.addWidget(tabs, 1)
        if self.editable:
            commands = QHBoxLayout()
            for label, axis, distribute in (
                ("Alinear X", 0, False),
                ("Alinear Y", 1, False),
                ("Distribuir X", 0, True),
                ("Distribuir Y", 1, True),
            ):
                button = QPushButton(label)
                button.clicked.connect(
                    lambda checked=False, axis=axis, distribute=distribute: self.arrange(
                        axis, distribute
                    )
                )
                commands.addWidget(button)
            column.addLayout(commands)
        self.error = QLabel()
        self.error.setObjectName("error")
        self.error.setWordWrap(True)
        self.error.setTextFormat(Qt.TextFormat.PlainText)
        column.addWidget(self.error)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        if self.editable:
            buttons.addButton(QDialogButtonBox.StandardButton.Apply).clicked.connect(self.apply)
        buttons.rejected.connect(self.reject)
        column.addWidget(buttons)

    def positions(self):
        try:
            positions = {
                node: tuple(float(self.node_table.item(row, col).text()) for col in (1, 2))
                for row, node in enumerate(self.nodes)
            }
            if any(not math.isfinite(v) for point in positions.values() for v in point):
                raise ValueError
            return positions
        except ValueError as error:
            raise ValueError(
                "Las coordenadas deben ser números finitos. Usa punto decimal."
            ) from error

    def arrange(self, axis, distribute):
        selected = sorted(
            {index.row() for index in self.node_table.selectionModel().selectedRows()}
        )
        if len(selected) < (3 if distribute else 2):
            self.error.setText("Selecciona al menos tres nodos para distribuir o dos para alinear.")
            return
        try:
            positions = self.positions()
        except ValueError as error:
            self.error.setText(str(error))
            return
        selected.sort(key=lambda row: (positions[self.nodes[row]][axis], self.nodes[row]))
        low, high = (
            positions[self.nodes[selected[0]]][axis],
            positions[self.nodes[selected[-1]]][axis],
        )
        for number, row in enumerate(selected):
            value = (
                low * (1 - number / (len(selected) - 1)) + high * number / (len(selected) - 1)
                if distribute
                else sum(positions[self.nodes[r]][axis] / len(selected) for r in selected)
            )
            self.node_table.item(row, axis + 1).setText(repr(value))
        self.error.clear()

    def apply(self):
        if self.owner.states or self.owner.busy:
            return
        try:
            positions = self.positions()
        except ValueError as error:
            self.error.setText(str(error))
            return
        snapshot = self.owner._snapshot("Acomodar nodos")
        snapshot.positions = positions
        if self.owner._commit_edit(snapshot):
            self.owner.graph_view.fit_graph()
            self.error.clear()
