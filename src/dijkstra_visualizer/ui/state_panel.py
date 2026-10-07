from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dijkstra_visualizer.core.graph import ordered_arcs
from dijkstra_visualizer.core.models import format_number


class StatePanel(QWidget):
    def __init__(self):
        super().__init__()
        column = QVBoxLayout(self)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        column.addWidget(self.hint)
        row = QHBoxLayout()
        self.table = QTableWidget()
        self.arcs = QTableWidget()
        for table in (self.table, self.arcs):
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setAlternatingRowColors(True)
            row.addWidget(table)
        column.addLayout(row)

    def show_state(self, graph, state):
        self.setVisible(state.algorithm == "Bellman-Ford")
        if state.algorithm != "Bellman-Ford":
            return
        self.hint.setText(
            "Bellman-Ford · V / d / π · naranja: arco actual · amarillo: mejora. "
            + (
                "Cada conexión no dirigida aparece en ambos sentidos."
                if not graph.is_directed()
                else "Los arcos respetan su dirección."
            )
        )
        nodes = sorted(graph)
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Nodo V", "Distancia d", "Predecesor π"])
        self.table.setRowCount(len(nodes))
        for row, node in enumerate(nodes):
            for col, value in enumerate(
                [node, format_number(state.distances[node]), state.predecessors[node] or "—"]
            ):
                item = QTableWidgetItem(value)
                if node in state.affected:
                    item.setBackground(QColor("#fecaca"))
                elif node in state.updated_nodes:
                    item.setBackground(QColor("#fef08a"))
                self.table.setItem(row, col, item)
        arcs = ordered_arcs(graph)
        self.arcs.setColumnCount(4)
        self.arcs.setHorizontalHeaderLabels(["Origen", "Destino", "ID", "Peso"])
        self.arcs.setRowCount(len(arcs))
        for row, (u, v, key, weight) in enumerate(arcs):
            for col, value in enumerate([u, v, str(key), format_number(weight)]):
                item = QTableWidgetItem(value)
                if state.current_edge == (u, v, key):
                    item.setBackground(QColor("#fed7aa"))
                self.arcs.setItem(row, col, item)
            if state.current_edge == (u, v, key):
                self.arcs.scrollToItem(self.arcs.item(row, 0))
        self.table.resizeColumnsToContents()
        self.arcs.resizeColumnsToContents()
