import math
from collections import defaultdict

import networkx as nx
from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QApplication, QGraphicsItem, QGraphicsScene, QGraphicsView

from graph_visualizer.core.dijkstra import reconstruct_edge_path
from graph_visualizer.core.graph import EdgeId, edge_id, edges_with_keys
from graph_visualizer.core.models import DijkstraState
from graph_visualizer.io.layout_io import PositionMap
from graph_visualizer.ui.edge_item import EdgeItem
from graph_visualizer.ui.node_item import NodeItem


class GraphView(QGraphicsView):
    layout_changed = Signal()
    node_selected = Signal(object)
    node_creation_requested = Signal(object)
    edge_edit_requested = Signal(object, object, object)
    connection_requested = Signal(object, object)

    def __init__(self, graph: nx.Graph, positions: PositionMap, parent=None):
        super().__init__(parent)
        self.graph = graph
        self.editable = True
        self.show_state_labels = True
        self.connection_source = None
        self.connection_preview = None
        self.pressed_edge = None
        self.press_position = None
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setBackgroundBrush(QColor("#f8fafc"))
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.nodes: dict[str, NodeItem] = {}
        self.edges: dict[EdgeId, EdgeItem] = {}
        self.set_graph(graph, positions)
        self.scene().selectionChanged.connect(self._selection_changed)

    def set_graph(self, graph: nx.Graph, positions: PositionMap) -> None:
        self.cancel_gesture()
        self.graph = graph
        with QSignalBlocker(self.scene()):
            for edge in self.edges.values():
                edge.source.position_changed.disconnect(edge.update_position)
                edge.target.position_changed.disconnect(edge.update_position)
            self.edges.clear()
            self.nodes.clear()
            self.scene().clear()
            for node in sorted(graph):
                item = NodeItem(node)
                item.set_state_labels_visible(self.show_state_labels)
                self.scene().addItem(item)
                item.setPos(*positions[node])
                item.movement_finished.connect(self._movement_finished)
                self.nodes[node] = item
            groups = defaultdict(list)
            for source, target, key, data in edges_with_keys(graph):
                groups[min(source, target), max(source, target)].append(
                    (source, target, key, data["weight"])
                )
            for connections in groups.values():
                for index, (source, target, key, weight) in enumerate(sorted(connections)):
                    offset = (index - (len(connections) - 1) / 2) * 48
                    if source > target:
                        offset = -offset
                    edge = EdgeItem(
                        self.nodes[source],
                        self.nodes[target],
                        weight,
                        key,
                        offset,
                        graph.is_directed(),
                    )
                    self.scene().addItem(edge)
                    self.edges[edge_id(source, target, key, graph.is_directed())] = edge
        self._update_scene_rect()

    def _selection_changed(self) -> None:
        selected = self.scene().selectedItems()
        if len(selected) == 1 and isinstance(selected[0], NodeItem):
            self.node_selected.emit(selected[0].node_id)

    def positions(self) -> PositionMap:
        return {node: (item.pos().x(), item.pos().y()) for node, item in self.nodes.items()}

    def _movement_finished(self) -> None:
        self._update_scene_rect()
        self.layout_changed.emit()

    def _update_scene_rect(self) -> None:
        self.setSceneRect(self.scene().itemsBoundingRect().adjusted(-100, -100, 100, 100))

    def set_editable(self, editable: bool) -> None:
        self.cancel_gesture()
        self.editable = editable
        self.scene().clearSelection()
        for item in self.nodes.values():
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, editable)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, editable)
            item.setAcceptedMouseButtons(
                Qt.MouseButton.LeftButton if editable else Qt.MouseButton.NoButton
            )

    def set_state_labels_visible(self, visible: bool) -> None:
        self.show_state_labels = visible
        for item in self.nodes.values():
            item.set_state_labels_visible(visible)
        self._update_scene_rect()

    def apply_state(
        self, state: DijkstraState | None, start: str, target: str, final: bool = False
    ) -> None:
        path_edges = (
            set(reconstruct_edge_path(state, start, target))
            if state is not None and (final or state.algorithm == "Floyd-Warshall")
            else set()
        )
        for node, item in self.nodes.items():
            item.set_state(
                (
                    state.matrix[state.nodes.index(start)][state.nodes.index(node)]
                    if state.algorithm == "Floyd-Warshall"
                    else state.distances[node]
                )
                if state
                else math.inf,
                state.predecessors.get(node) if state else None,
                state is not None and node in state.visited,
                state is not None and node == state.current_node,
                node == start,
                node == target,
                state is not None and node in state.updated_nodes,
            )
            if state and state.algorithm != "Dijkstra":
                item.state_caption = "sin mínimo finito" if node in state.affected else ""
                if state.algorithm == "Floyd-Warshall":
                    from graph_visualizer.core.models import format_number

                    distance = state.matrix[state.nodes.index(start)][state.nodes.index(node)]
                    item.label.setText(format_number(distance))
                    item.label.setPos(-item.label.boundingRect().width() / 2, 35)
                item._update_caption()
                if node in state.affected:
                    item.fill = QColor("#fecaca")
        for pair, edge in self.edges.items():
            edge.set_highlighted(pair in path_edges)
            if state and pair in {edge_id(*e, self.graph.is_directed()) for e in state.cycle}:
                edge.setPen(QPen(QColor("#dc2626"), 5))
            if (
                state
                and state.current_edge
                and pair == edge_id(*state.current_edge, self.graph.is_directed())
            ):
                edge.setPen(QPen(QColor("#e69b00"), 5))
        self._update_scene_rect()

    def fit_graph(self) -> None:
        self.fitInView(
            self.scene().itemsBoundingRect().adjusted(-45, -45, 45, 45),
            Qt.AspectRatioMode.KeepAspectRatio,
        )

    def wheelEvent(self, event) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        scale = self.transform().m11() * factor
        if 0.15 <= scale <= 4:
            self.scale(factor, factor)
        event.accept()

    def _graph_item_at(self, position):
        item = self.itemAt(position)
        while item is not None and not isinstance(item, (NodeItem, EdgeItem)):
            item = item.parentItem()
        return item

    def cancel_gesture(self) -> None:
        if self.connection_preview is not None:
            self.scene().removeItem(self.connection_preview)
            self.connection_preview = None
        self.connection_source = None
        self.pressed_edge = None
        self.viewport().unsetCursor()

    def mouseDoubleClickEvent(self, event) -> None:
        if (
            self.editable
            and event.button() == Qt.MouseButton.LeftButton
            and self.itemAt(event.position().toPoint()) is None
        ):
            position = self.mapToScene(event.position().toPoint())
            self.cancel_gesture()
            event.accept()
            self.node_creation_requested.emit(position)
            return
        super().mouseDoubleClickEvent(event)

    def mousePressEvent(self, event) -> None:
        if self.editable and event.button() == Qt.MouseButton.LeftButton:
            point = event.position().toPoint()
            item = self._graph_item_at(point)
            self.press_position = point
            if isinstance(item, NodeItem):
                local = item.mapFromScene(self.mapToScene(point))
                if 19 <= math.hypot(local.x(), local.y()) <= 34:
                    self.connection_source = item.node_id
                    pen = QPen(QColor("#087e8b"), 2, Qt.PenStyle.DashLine)
                    self.connection_preview = self.scene().addPath(QPainterPath(item.pos()), pen)
                    self.connection_preview.setZValue(-2)
                    self.connection_preview.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
                    self.viewport().setCursor(Qt.CursorShape.CrossCursor)
                    event.accept()
                    return
            elif isinstance(item, EdgeItem):
                self.pressed_edge = edge_id(
                    item.source.node_id, item.target.node_id, item.key, self.graph.is_directed()
                )
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self.connection_source is not None:
            path = QPainterPath(self.nodes[self.connection_source].pos())
            path.lineTo(self.mapToScene(event.position().toPoint()))
            self.connection_preview.setPath(path)
            event.accept()
            return
        if self.pressed_edge is not None:
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        point = event.position().toPoint()
        if event.button() == Qt.MouseButton.LeftButton and self.connection_source is not None:
            source = self.connection_source
            self.cancel_gesture()
            item = self._graph_item_at(point)
            event.accept()
            if isinstance(item, NodeItem) and item.node_id != source:
                local = item.mapFromScene(self.mapToScene(point))
                if math.hypot(local.x(), local.y()) <= 34:
                    self.connection_requested.emit(source, item.node_id)
            return
        if event.button() == Qt.MouseButton.LeftButton and self.pressed_edge is not None:
            selected = self.pressed_edge
            self.cancel_gesture()
            item = self._graph_item_at(point)
            event.accept()
            if (
                isinstance(item, EdgeItem)
                and edge_id(
                    item.source.node_id, item.target.node_id, item.key, self.graph.is_directed()
                )
                == selected
                and (point - self.press_position).manhattanLength()
                < QApplication.startDragDistance()
            ):
                self.edge_edit_requested.emit(*selected)
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_gesture()
            event.accept()
            return
        super().keyPressEvent(event)

    def focusOutEvent(self, event) -> None:
        self.cancel_gesture()
        super().focusOutEvent(event)
