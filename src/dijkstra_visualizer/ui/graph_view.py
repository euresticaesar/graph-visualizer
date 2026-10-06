import math
from collections import defaultdict

import networkx as nx
from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView

from dijkstra_visualizer.core.dijkstra import reconstruct_edge_path
from dijkstra_visualizer.core.graph import EdgeId, edge_id, edges_with_keys
from dijkstra_visualizer.core.models import DijkstraState
from dijkstra_visualizer.io.layout_io import PositionMap
from dijkstra_visualizer.ui.edge_item import EdgeItem
from dijkstra_visualizer.ui.node_item import NodeItem


class GraphView(QGraphicsView):
    layout_changed = Signal()
    node_selected = Signal(object)

    def __init__(self, graph: nx.Graph, positions: PositionMap, parent=None):
        super().__init__(parent)
        self.graph = graph
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
        self.setBackgroundBrush(QColor("#f8fafc"))
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.nodes: dict[int, NodeItem] = {}
        self.edges: dict[EdgeId, EdgeItem] = {}
        self.set_graph(graph, positions)
        self.scene().selectionChanged.connect(self._selection_changed)

    def set_graph(self, graph: nx.Graph, positions: PositionMap) -> None:
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
                self.scene().addItem(item)
                item.setPos(*positions[node])
                item.movement_finished.connect(self._movement_finished)
                self.nodes[node] = item
            groups = defaultdict(list)
            for source, target, key, data in edges_with_keys(graph):
                groups[min(source, target), max(source, target)].append((key, data["weight"]))
            for (source, target), connections in groups.items():
                for index, (key, weight) in enumerate(sorted(connections)):
                    offset = (index - (len(connections) - 1) / 2) * 40
                    edge = EdgeItem(self.nodes[source], self.nodes[target], weight, key, offset)
                    self.scene().addItem(edge)
                    self.edges[edge_id(source, target, key)] = edge
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
        self.scene().clearSelection()
        for item in self.nodes.values():
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, editable)
            item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, editable)
            item.setAcceptedMouseButtons(
                Qt.MouseButton.LeftButton if editable else Qt.MouseButton.NoButton
            )

    def apply_state(
        self, state: DijkstraState | None, start: int, target: int, final: bool = False
    ) -> None:
        path_edges = (
            set(reconstruct_edge_path(state, start, target))
            if state is not None and final
            else set()
        )
        for node, item in self.nodes.items():
            item.set_state(
                state.distances[node] if state else math.inf,
                state.predecessors[node] if state else None,
                state is not None and node in state.visited,
                state is not None and node == state.current_node,
                node == start,
                node == target,
                state is not None and node in state.updated_nodes,
            )
        for pair, edge in self.edges.items():
            edge.set_highlighted(pair in path_edges)
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
