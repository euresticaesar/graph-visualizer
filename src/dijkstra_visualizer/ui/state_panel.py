from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QStyledItemDelegate,
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


class MatrixDelegate(QStyledItemDelegate):
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if index.data(Qt.ItemDataRole.UserRole):
            painter.save()
            painter.setPen(QPen(QColor("#15803d"), 2))
            painter.drawRect(option.rect.adjusted(1, 1, -2, -2))
            painter.restore()
        if index.data(Qt.ItemDataRole.UserRole + 1):
            painter.save()
            painter.setPen(QPen(QColor("#7c3aed"), 3))
            painter.drawRect(option.rect.adjusted(4, 4, -5, -5))
            painter.restore()


def matrix_style(state, row, col):
    green = state.k is not None and (row == state.k or col == state.k)
    yellow = (row, col) in state.changed
    return (
        "#fef08a" if yellow else "#bbf7d0" if green else "#ffffff",
        green,
        state.cell == (row, col),
    )


class MatrixPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        hint = QLabel(
            "Recorridos: destino en rutas directas; k al mejorar por un intermedio; "
            "nodo propio en diagonal; — sin recorrido. Verde: fila/columna k; "
            "amarillo: mejoras acumuladas; violeta: comparación actual."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        row = QHBoxLayout()
        self.tables = []
        for title in ["Distancias D", "Recorridos · intermedios"]:
            column = QVBoxLayout()
            column.addWidget(QLabel(title))
            table = QTableWidget()
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setItemDelegate(MatrixDelegate(table))
            table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
            table.setHorizontalHeader(MatrixHeader(Qt.Orientation.Horizontal, table))
            table.setVerticalHeader(MatrixHeader(Qt.Orientation.Vertical, table))
            column.addWidget(table)
            row.addLayout(column)
            self.tables.append(table)
        layout.addLayout(row)

    def show_state(self, state):
        self.setVisible(state.algorithm == "Floyd-Warshall")
        if state.algorithm != "Floyd-Warshall":
            return
        for table, matrix in zip(self.tables, [state.matrix, state.intermediates], strict=True):
            table.setRowCount(len(state.nodes))
            table.setColumnCount(len(state.nodes))
            table.setHorizontalHeaderLabels(state.nodes)
            table.setVerticalHeaderLabels(state.nodes)
            for index in range(len(state.nodes)):
                color = QColor("#bbf7d0" if index == state.k else "#e2e8f0")
                table.horizontalHeaderItem(index).setBackground(color)
                table.verticalHeaderItem(index).setBackground(color)
            for i, row in enumerate(matrix):
                for j, value in enumerate(row):
                    item = QTableWidgetItem(
                        format_number(value)
                        if isinstance(value, (int, float))
                        else value
                        if value is not None
                        else "—"
                    )
                    background, green, active = matrix_style(state, i, j)
                    item.setBackground(QColor(background))
                    item.setData(Qt.ItemDataRole.UserRole, green)
                    item.setData(Qt.ItemDataRole.UserRole + 1, active)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    table.setItem(i, j, item)
            table.resizeColumnsToContents()
            if state.cell:
                table.scrollToItem(table.item(*state.cell))


class MatrixHeader(QHeaderView):
    """Paint model header colors even when a desktop style ignores BackgroundRole."""

    def paintSection(self, painter, rect, logical_index):
        if not rect.isValid():
            return
        painter.save()
        color = self.model().headerData(
            logical_index, self.orientation(), Qt.ItemDataRole.BackgroundRole
        )
        painter.fillRect(rect, color if color is not None else QColor("#e2e8f0"))
        painter.setPen(QColor("#cbd5e1"))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        painter.setPen(QColor("#172b4d"))
        text = self.model().headerData(
            logical_index, self.orientation(), Qt.ItemDataRole.DisplayRole
        )
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(text))
        painter.restore()
