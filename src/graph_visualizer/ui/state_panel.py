from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import (
    QHeaderView,
    QLabel,
    QSplitter,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from graph_visualizer.core.graph import ordered_arcs
from graph_visualizer.core.models import format_number
from graph_visualizer.ui.section_card import SectionCard
from graph_visualizer.ui.themes import matrix_colors, palette_for, row_color


class StatePanel(QWidget):
    def __init__(self):
        super().__init__()
        self.palette = palette_for()
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        self.hint = QLabel()
        self.hint.setObjectName("hint")
        self.hint.setWordWrap(True)
        column.addWidget(self.hint)
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.table = QTableWidget()
        self.arcs = QTableWidget()
        for title, table in (
            ("Distancias · V / d / π", self.table),
            ("Arcos ordenados", self.arcs),
        ):
            card = SectionCard(title)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setAlternatingRowColors(True)
            table.verticalHeader().setDefaultSectionSize(26)
            table.setMinimumHeight(100)
            card.content.addWidget(table)
            self.splitter.addWidget(card)
        column.addWidget(self.splitter, 1)

    def show_state(self, graph, state):
        self.setVisible(state.algorithm in {"Bellman-Ford", "A*"})
        self.splitter.widget(1).setVisible(state.algorithm != "A*")
        self.splitter.widget(0).findChild(QLabel, "section").setText(
            "Prioridades · g / h / f" if state.algorithm == "A*" else "Distancias · V / d / π"
        )
        if state.algorithm == "A*":
            from graph_visualizer.export.image_exporter import table_data

            self.hint.setText(
                "g: costo acumulado · h: estimación admisible · f = g + h. "
                "Se expande el nodo con menor f."
            )
            _, headers, rows = table_data(graph, state)[0]
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setRowCount(len(rows))
            for row, values in enumerate(rows):
                for col, value in enumerate(values):
                    item = QTableWidgetItem(value)
                    item.setBackground(QColor(row_color(state, "astar", values, self.palette)))
                    item.setForeground(QColor(self.palette.text))
                    self.table.setItem(row, col, item)
            self.table.resizeColumnsToContents()
            return
        if state.algorithm != "Bellman-Ford":
            return
        self.hint.setText(
            "Naranja: arco actual · Amarillo: mejora. "
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
                item.setBackground(QColor(row_color(state, "distances", [node], self.palette)))
                item.setForeground(QColor(self.palette.text))
                self.table.setItem(row, col, item)
        arcs = ordered_arcs(graph)
        self.arcs.setColumnCount(4)
        self.arcs.setHorizontalHeaderLabels(["Origen", "Destino", "ID", "Peso"])
        self.arcs.setRowCount(len(arcs))
        for row, (u, v, key, weight) in enumerate(arcs):
            for col, value in enumerate([u, v, str(key), format_number(weight)]):
                item = QTableWidgetItem(value)
                item.setBackground(QColor(row_color(state, "arcs", [u, v, str(key)], self.palette)))
                item.setForeground(QColor(self.palette.text))
                self.arcs.setItem(row, col, item)
            if state.current_edge == (u, v, key):
                self.arcs.scrollToItem(self.arcs.item(row, 0))
        self.table.resizeColumnsToContents()
        self.arcs.resizeColumnsToContents()


class MatrixDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.palette = palette_for()

    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        if index.data(Qt.ItemDataRole.UserRole):
            painter.save()
            painter.setPen(QPen(QColor(self.palette.k_border), 2))
            painter.drawRect(option.rect.adjusted(1, 1, -2, -2))
            painter.restore()
        if index.data(Qt.ItemDataRole.UserRole + 1):
            painter.save()
            painter.setPen(QPen(QColor(self.palette.active), 3))
            painter.drawRect(option.rect.adjusted(4, 4, -5, -5))
            painter.restore()


def matrix_style(state, row, col, palette=None):
    return matrix_colors(state, row, col, palette)


class MatrixPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.palette = palette_for()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        hint = QLabel("Fila / columna k · Mejora · Comparación · Rojo: sin mínimo finito")
        hint.setObjectName("hint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.tables = []
        for title in ["Distancias D", "Recorridos · intermedios"]:
            card = SectionCard(title)
            if title.startswith("Recorridos"):
                card.setToolTip(
                    "Destino en rutas directas; k al mejorar por un intermedio; "
                    "nodo propio en diagonal; — sin recorrido."
                )
            table = QTableWidget()
            table.setMinimumHeight(100)
            table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            table.setItemDelegate(MatrixDelegate(table))
            table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
            table.setHorizontalHeader(MatrixHeader(Qt.Orientation.Horizontal, table))
            table.setVerticalHeader(MatrixHeader(Qt.Orientation.Vertical, table))
            table.verticalHeader().setDefaultSectionSize(26)
            card.content.addWidget(table)
            self.splitter.addWidget(card)
            self.tables.append(table)
        layout.addWidget(self.splitter, 1)

    def show_state(self, state):
        self.setVisible(state.algorithm == "Floyd-Warshall")
        if state.algorithm != "Floyd-Warshall":
            return
        for table, matrix in zip(self.tables, [state.matrix, state.intermediates], strict=True):
            table.itemDelegate().palette = self.palette
            table.horizontalHeader().palette = self.palette
            table.verticalHeader().palette = self.palette
            table.setRowCount(len(state.nodes))
            table.setColumnCount(len(state.nodes))
            table.setHorizontalHeaderLabels(state.nodes)
            table.setVerticalHeaderLabels(state.nodes)
            for index in range(len(state.nodes)):
                color = QColor(self.palette.k_fill if index == state.k else self.palette.header)
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
                    background, green, active = matrix_style(state, i, j, self.palette)
                    item.setBackground(QColor(background))
                    item.setForeground(QColor(self.palette.text))
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
        painter.fillRect(rect, color if color is not None else QColor(self.palette.header))
        painter.setPen(QColor(self.palette.border))
        painter.drawRect(rect.adjusted(0, 0, -1, -1))
        painter.setPen(QColor(self.palette.text))
        text = self.model().headerData(
            logical_index, self.orientation(), Qt.ItemDataRole.DisplayRole
        )
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(text))
        painter.restore()

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.palette = palette_for()
