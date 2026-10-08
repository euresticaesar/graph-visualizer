import math
from collections import Counter

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsObject, QGraphicsSimpleTextItem, QStyle

from graph_visualizer.core.models import format_number as format_distance
from graph_visualizer.ui.themes import palette_for

UNREACHED = "#e2e8f0"
TENTATIVE = "#fef3c7"
VISITED = "#a7e3bd"
CURRENT = "#18794e"
TARGET = "#2563eb"
PATH = "#087e8b"


def node_aliases(nodes, font_scale=1.0):
    font = QFont("Sans Serif", 13, QFont.Weight.Bold)
    font.setPointSizeF(13 * font_scale)
    metrics = QFontMetricsF(font)
    width = 200 * font_scale
    aliases = {n: metrics.elidedText(n, Qt.TextElideMode.ElideMiddle, width) for n in nodes}
    used = set(aliases.values())
    ambiguous = {alias for alias, count in Counter(aliases.values()).items() if count > 1}
    for number, node in enumerate(sorted(nodes), 1):
        if aliases[node] not in ambiguous:
            continue
        suffix = f" [{number}]"
        alias = (
            metrics.elidedText(
                node, Qt.TextElideMode.ElideMiddle, width - metrics.horizontalAdvance(suffix)
            )
            + suffix
        )
        while alias in used:
            alias += "·"
        aliases[node] = alias
        used.add(alias)
    return aliases


class AnnotationLabel(QGraphicsSimpleTextItem):
    def paint(self, painter, option, widget=None) -> None:
        painter.fillRect(self.boundingRect(), QColor(self.parentItem().palette.canvas))
        super().paint(painter, option, widget)


class NodeItem(QGraphicsObject):
    position_changed = Signal()
    movement_finished = Signal()

    def __init__(self, node_id: str, palette=None, font_scale=1.0, display_id=None):
        super().__init__()
        self.node_id = node_id
        self.palette = palette or palette_for()
        self.font_scale = font_scale
        self.id_font = QFont("Sans Serif", 13, QFont.Weight.Bold)
        self.id_font.setPointSizeF(13 * font_scale)
        metrics = QFontMetricsF(self.id_font)
        self.display_id = display_id or metrics.elidedText(
            node_id, Qt.TextElideMode.ElideMiddle, 200 * font_scale
        )
        self.node_width = max(52 * font_scale, metrics.horizontalAdvance(self.display_id) + 20)
        self.node_height = 52 * font_scale
        self.fill = QColor(UNREACHED)
        self.is_target = False
        self.is_current = False
        self.is_affected = False
        self.drag_origin = QPointF()
        self.show_state_labels = True
        self.caption_roles: list[str] = []
        self.state_caption = ""
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setZValue(1)
        self.setAcceptHoverEvents(True)
        self.hovered = False
        self.label = AnnotationLabel(self)
        label_font = QFont("Sans Serif")
        label_font.setPointSizeF(11 * font_scale)
        self.label.setFont(label_font)
        self.label.setBrush(QColor(self.palette.text))
        self.label.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.caption = AnnotationLabel(self)
        caption_font = QFont("Sans Serif")
        caption_font.setPointSizeF(9 * font_scale)
        self.caption.setFont(caption_font)
        self.caption.setBrush(QColor(self.palette.muted))
        self.caption.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.set_state(math.inf, None, False, False, False, False, False)

    def boundingRect(self) -> QRectF:
        return self.node_rect().adjusted(-8, -8, 8, 8)

    def node_rect(self):
        return QRectF(
            -self.node_width / 2, -self.node_height / 2, self.node_width, self.node_height
        )

    def shape(self):
        path = QPainterPath()
        path.addEllipse(self.node_rect().adjusted(-7, -7, 7, 7))
        return path

    def connection_zone(self, point):
        radius = math.hypot(point.x() / (self.node_width / 2), point.y() / (self.node_height / 2))
        return 0.70 <= radius <= 1.3

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.hovered and self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable:
            painter.setPen(QPen(QColor(self.palette.accent), 2, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(self.node_rect().adjusted(-4, -4, 4, 4))
        if self.is_current or option.state & QStyle.StateFlag.State_Selected:
            painter.setPen(QPen(QColor(self.palette.current), 1.5, Qt.PenStyle.DashLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(self.node_rect().adjusted(-6, -6, 6, 6))
        painter.setPen(
            QPen(
                QColor(self.palette.target if self.is_target else self.palette.edge),
                3 if self.is_target else 1.5,
            )
        )
        painter.setBrush(self.fill)
        painter.drawEllipse(self.node_rect())
        painter.setPen(
            QColor(
                self.palette.current_text
                if self.is_current and not self.is_affected
                else self.palette.text
            )
        )
        painter.setFont(self.id_font)
        painter.drawText(
            self.node_rect(),
            Qt.AlignmentFlag.AlignCenter,
            self.display_id,
        )

    def set_state(
        self,
        distance,
        predecessor,
        visited,
        current,
        start,
        target,
        updated,
        *,
        predecessor_label=None,
    ) -> None:
        self.is_target, self.is_current = target, current
        self.is_affected = distance == -math.inf
        color = (
            self.palette.error_fill
            if self.is_affected
            else self.palette.current
            if current
            else self.palette.visited
            if visited
            else (self.palette.tentative if math.isfinite(distance) else self.palette.unreached)
        )
        self.fill = QColor(color)
        pred = predecessor if predecessor is not None else "—"
        if predecessor is not None:
            pred = QFontMetricsF(self.label.font()).elidedText(
                predecessor_label or pred, Qt.TextElideMode.ElideMiddle, 180 * self.font_scale
            )
        self.label.setText(f"[{format_distance(distance)}, {pred}]")
        font = self.label.font()
        font.setBold(updated)
        self.label.setFont(font)
        self.label.setPos(-self.label.boundingRect().width() / 2, self.node_height / 2 + 9)
        state = (
            "sin mínimo finito"
            if self.is_affected
            else "actual"
            if current
            else "fijado"
            if visited
            else ("tentativo" if math.isfinite(distance) else "sin alcanzar")
        )
        self.caption_roles = (["INICIO"] if start else []) + (["DESTINO"] if target else [])
        self.state_caption = state
        self._update_caption()
        full_caption = " · ".join([*self.caption_roles, state])
        self.setToolTip(
            f"Nodo {self.node_id} — {full_caption}\n"
            f"Distancia: {distance!r} · Predecesor: {predecessor or '—'}\n"
            "En edición: arrastra el centro para mover o el borde para conectar."
        )
        self.update()

    def set_state_labels_visible(self, visible: bool) -> None:
        self.show_state_labels = visible
        self._update_caption()

    def _update_caption(self) -> None:
        parts = [*self.caption_roles]
        if self.show_state_labels and self.state_caption:
            parts.append(self.state_caption)
        self.caption.setText(" · ".join(parts))
        self.caption.setVisible(bool(parts))
        self.caption.setPos(
            -self.caption.boundingRect().width() / 2, -self.node_height / 2 - 27 * self.font_scale
        )

    def hoverEnterEvent(self, event) -> None:
        self.hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverMoveEvent(self, event) -> None:
        if self.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsMovable:
            self.setCursor(
                Qt.CursorShape.CrossCursor
                if self.connection_zone(event.pos())
                else Qt.CursorShape.SizeAllCursor
            )
        else:
            self.unsetCursor()
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self.hovered = False
        self.unsetCursor()
        self.update()
        super().hoverLeaveEvent(event)

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
