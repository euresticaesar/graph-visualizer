import math

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainterPath, QPainterPathStroker, QPen, QPolygonF
from PySide6.QtWidgets import QGraphicsPathItem, QGraphicsSimpleTextItem

from graph_visualizer.ui.node_item import NodeItem, format_distance


class WeightLabel(QGraphicsSimpleTextItem):
    def paint(self, painter, option, widget=None) -> None:
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(self.parentItem().palette.canvas))
        painter.drawRoundedRect(self.boundingRect(), 3, 3)
        super().paint(painter, option, widget)

    def boundingRect(self):
        return super().boundingRect().adjusted(-4, -2, 4, 2)


class EdgeItem(QGraphicsPathItem):
    def __init__(
        self,
        source: NodeItem,
        target: NodeItem,
        weight: float,
        key=0,
        offset=0.0,
        directed=False,
        show_id=False,
        label_offset=(0, 0),
    ):
        super().__init__()
        self.source, self.target = source, target
        self.palette = source.palette
        self.weight = weight
        self.key, self.offset = key, offset
        self.directed = directed
        self.label_offset = QPointF(*label_offset)
        self.setZValue(-1)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setToolTip(
            f"Conexión #{key} · {source.node_id} {'→' if directed else '↔'} {target.node_id}"
            f" · Peso {format_distance(weight)}\nClic izquierdo: cambiar el peso"
            "\nClic derecho: eliminar · Ctrl+Z: deshacer"
        )
        self.label = WeightLabel("", self)
        label_font = QFont("Sans Serif", 11, QFont.Weight.DemiBold)
        label_font.setPointSizeF(11 * source.font_scale)
        self.label.setFont(label_font)
        self.label.setBrush(QColor(self.palette.muted))
        self.label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.label.setToolTip(self.toolTip())
        self.source.position_changed.connect(self.update_position)
        self.target.position_changed.connect(self.update_position)
        self.set_highlighted(False)
        self.set_id_visible(show_id)

    def set_id_visible(self, visible: bool) -> None:
        text = format_distance(self.weight)
        self.label.setText(f"{text} · #{self.key}" if visible else text)
        self.update_position()

    def update_position(self) -> None:
        start, end = self.source.pos(), self.target.pos()
        delta = end - start
        length = math.hypot(delta.x(), delta.y()) or 1
        control = (start + end) / 2 + QPointF(-delta.y(), delta.x()) * (2 * self.offset / length)
        path = QPainterPath(start)
        path.quadTo(control, end)
        self.setPath(path)
        self.label.setPos(
            path.pointAtPercent(0.5) - self.label.boundingRect().center() + self.label_offset
        )

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self.directed:
            painter.setBrush(self.pen().color())
            painter.drawPolygon(self._arrow_head())

    def _arrow_head(self) -> QPolygonF:
        path = self.path()
        node_shapes = [node.mapToItem(self, node.shape()) for node in (self.source, self.target)]
        padding = self.pen().widthF() / 2 + 1
        label_rects = [
            label.mapRectToItem(self, label.boundingRect()).adjusted(
                -padding, -padding, padding, padding
            )
            for label in (
                self.source.label,
                self.source.caption,
                self.target.label,
                self.target.caption,
                self.label,
            )
            if label.isVisible()
        ]
        fallback = QPolygonF()
        for step in range(98, 9, -1):
            t = step / 100
            tip = path.pointAtPercent(t)
            delta = tip - path.pointAtPercent(max(0, t - 0.02))
            length = math.hypot(delta.x(), delta.y()) or 1
            unit = delta / length
            normal = QPointF(-unit.y(), unit.x())
            arrow = QPolygonF([tip, tip - unit * 15 + normal * 7, tip - unit * 15 - normal * 7])
            outline = QPainterPath()
            outline.addPolygon(arrow)
            outline.closeSubpath()
            # Nodes and labels are painted above the edge and can hide the whole arrow.
            if any(outline.intersects(shape) for shape in node_shapes):
                continue
            if fallback.isEmpty():
                fallback = arrow
            if not any(outline.intersects(rect) for rect in label_rects):
                return arrow
        return fallback

    def shape(self):
        stroker = QPainterPathStroker()
        stroker.setWidth(12)
        return stroker.createStroke(self.path())

    def boundingRect(self):
        return self.path().boundingRect().adjusted(-9, -9, 9, 9)

    def set_highlighted(self, highlighted: bool) -> None:
        self.setPen(
            QPen(
                QColor(self.palette.accent if highlighted else self.palette.edge),
                5 if highlighted else 2,
            )
        )
        self.label.setBrush(QColor(self.palette.accent if highlighted else self.palette.muted))
