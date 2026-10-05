import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject, QGraphicsSimpleTextItem, QStyle

UNREACHED = "#e2e8f0"
TENTATIVE = "#fef3c7"
VISITED = "#a7e3bd"
CURRENT = "#18794e"
TARGET = "#dc3545"
PATH = "#087e8b"


def format_distance(value: float) -> str:
    return "∞" if math.isinf(value) else f"{value:.8g}"


class AnnotationLabel(QGraphicsSimpleTextItem):
    def paint(self, painter, option, widget=None) -> None:
        painter.fillRect(self.boundingRect(), QColor("#f8fafc"))
        super().paint(painter, option, widget)


class NodeItem(QGraphicsObject):
    position_changed = Signal()
    movement_finished = Signal()

    def __init__(self, node_id: int):
        super().__init__()
        self.node_id = node_id
        self.fill = QColor(UNREACHED)
        self.is_target = False
        self.is_current = False
        self.drag_origin = QPointF()
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(1)
        self.label = AnnotationLabel(self)
        self.label.setFont(QFont("Sans Serif", 11))
        self.label.setBrush(QColor("#172b4d"))
        self.label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.caption = AnnotationLabel(self)
        self.caption.setFont(QFont("Sans Serif", 9))
        self.caption.setBrush(QColor("#526179"))
        self.caption.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.set_state(math.inf, None, False, False, False, False, False)

    def boundingRect(self) -> QRectF:
        return QRectF(-34, -34, 68, 68)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.is_current or option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(QPen(QColor(CURRENT), 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QRectF(-32, -32, 64, 64))
        painter.setPen(
            QPen(QColor(TARGET if self.is_target else "#64748b"), 3 if self.is_target else 1.5)
        )
        painter.setBrush(self.fill)
        painter.drawEllipse(QRectF(-26, -26, 52, 52))
        painter.setPen(QColor("white" if self.is_current else "#172b4d"))
        painter.setFont(QFont("Sans Serif", 13, QFont.Weight.Bold))
        painter.drawText(QRectF(-26, -26, 52, 52), Qt.AlignmentFlag.AlignCenter, str(self.node_id))

    def set_state(self, distance, predecessor, visited, current, start, target, updated) -> None:
        self.is_target, self.is_current = target, current
        color = (
            CURRENT
            if current
            else VISITED
            if visited
            else (TENTATIVE if math.isfinite(distance) else UNREACHED)
        )
        self.fill = QColor(color)
        self.label.setText(
            f"[{format_distance(distance)}, {predecessor if predecessor is not None else 'null'}]"
        )
        font = self.label.font()
        font.setBold(updated)
        self.label.setFont(font)
        self.label.setPos(-self.label.boundingRect().width() / 2, 35)
        state = (
            "current"
            if current
            else "visited"
            if visited
            else ("tentative" if math.isfinite(distance) else "unreached")
        )
        roles = (["START"] if start else []) + (["TARGET"] if target else [])
        self.caption.setText(" · ".join([*roles, state]))
        self.caption.setPos(-self.caption.boundingRect().width() / 2, -53)
        self.setToolTip(f"Node {self.node_id} — {self.caption.text()}\n{self.label.text()}")
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.position_changed.emit()
        return super().itemChange(change, value)

    def mousePressEvent(self, event) -> None:
        self.drag_origin = self.pos()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if self.pos() != self.drag_origin:
            self.movement_finished.emit()
