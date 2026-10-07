import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainterPath, QPainterPathStroker, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsSimpleTextItem

from dijkstra_visualizer.ui.node_item import PATH, NodeItem, format_distance


class WeightLabel(QGraphicsSimpleTextItem):
    def paint(self, painter, option, widget=None) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#f8fafc"))
        painter.drawRoundedRect(self.boundingRect(), 3, 3)
        super().paint(painter, option, widget)

    def boundingRect(self):
        return super().boundingRect().adjusted(-4, -2, 4, 2)


class EdgeItem(QGraphicsPathItem):
    def __init__(
        self, source: NodeItem, target: NodeItem, weight: float, key=0, offset=0.0, directed=False
    ):
        super().__init__()
        self.source, self.target = source, target
        self.key, self.offset = key, offset
        self.directed = directed
        self.setZValue(-1)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setToolTip(f"Conexión {key} · Haz clic para cambiar el peso")
        self.label = WeightLabel(f"{format_distance(weight)} · #{key}", self)
        self.label.setFont(QFont("Sans Serif", 11, QFont.Weight.DemiBold))
        self.label.setBrush(QColor("#475569"))
        self.label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.source.position_changed.connect(self.update_position)
        self.target.position_changed.connect(self.update_position)
        self.set_highlighted(False)
        self.update_position()

    def update_position(self) -> None:
        start, end = self.source.pos(), self.target.pos()
        delta = end - start
        length = math.hypot(delta.x(), delta.y()) or 1
        control = (start + end) / 2 + QPointF(-delta.y(), delta.x()) * (2 * self.offset / length)
        path = QPainterPath(start)
        path.quadTo(control, end)
        self.setPath(path)
        self.label.setPos(path.pointAtPercent(0.5) - self.label.boundingRect().center())

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.directed:
            path = self.path()
            t = 0.98
            while t > 0.1 and self.target.boundingRect().contains(
                path.pointAtPercent(t) - self.target.pos()
            ):
                t -= 0.01
            tip = path.pointAtPercent(t)
            delta = tip - path.pointAtPercent(max(0, t - 0.02))
            length = math.hypot(delta.x(), delta.y()) or 1
            unit = delta / length
            normal = QPointF(-unit.y(), unit.x())
            painter.setBrush(self.pen().color())
            painter.drawPolygon(
                QPolygonF([tip, tip - unit * 15 + normal * 7, tip - unit * 15 - normal * 7])
            )

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(12)
        return stroker.createStroke(self.path())

    def boundingRect(self):
        return self.path().boundingRect().adjusted(-6, -6, 6, 6)

    def set_highlighted(self, highlighted: bool) -> None:
        self.setPen(QPen(QColor(PATH if highlighted else "#94a3b8"), 5 if highlighted else 2))
        self.label.setBrush(QColor(PATH if highlighted else "#475569"))
