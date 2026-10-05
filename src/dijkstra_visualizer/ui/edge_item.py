from PySide6.QtCore import QLineF, Qt
from PySide6.QtGui import QColor, QFont, QPen
from PySide6.QtWidgets import QGraphicsLineItem, QGraphicsSimpleTextItem

from dijkstra_visualizer.ui.node_item import PATH, NodeItem, format_distance


class WeightLabel(QGraphicsSimpleTextItem):
    def paint(self, painter, option, widget=None) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#f8fafc"))
        painter.drawRoundedRect(self.boundingRect(), 3, 3)
        super().paint(painter, option, widget)

    def boundingRect(self):
        return super().boundingRect().adjusted(-4, -2, 4, 2)


class EdgeItem(QGraphicsLineItem):
    def __init__(self, source: NodeItem, target: NodeItem, weight: float):
        super().__init__()
        self.source, self.target = source, target
        self.setZValue(-1)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.label = WeightLabel(format_distance(weight), self)
        self.label.setFont(QFont("Sans Serif", 11, QFont.Weight.DemiBold))
        self.label.setBrush(QColor("#475569"))
        self.label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.source.position_changed.connect(self.update_position)
        self.target.position_changed.connect(self.update_position)
        self.set_highlighted(False)
        self.update_position()

    def update_position(self) -> None:
        line = QLineF(self.source.pos(), self.target.pos())
        self.setLine(line)
        center = line.center()
        bounds = self.label.boundingRect()
        self.label.setPos(center.x() - bounds.width() / 2, center.y() - bounds.height() / 2)

    def set_highlighted(self, highlighted: bool) -> None:
        self.setPen(QPen(QColor(PATH if highlighted else "#94a3b8"), 5 if highlighted else 2))
        self.label.setBrush(QColor(PATH if highlighted else "#475569"))
