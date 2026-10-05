from datetime import datetime
from pathlib import Path
from typing import Literal

import networkx as nx
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import QGraphicsScene

from dijkstra_visualizer.core.dijkstra import reconstruct_path
from dijkstra_visualizer.core.models import DijkstraState
from dijkstra_visualizer.io.layout_io import PositionMap
from dijkstra_visualizer.ui.graph_view import GraphView
from dijkstra_visualizer.ui.node_item import format_distance

ExportKind = Literal["current", "all", "combined", "final"]


def render_scene(
    scene: QGraphicsScene,
    source_rect: QRectF,
    title: str,
    detail: str,
    width: int = 1600,
    height: int = 1100,
) -> QImage:
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    if image.isNull():
        raise ValueError("The export image is too large to allocate.")
    image.fill(QColor("#f8fafc"))
    painter = QPainter(image)
    try:
        painter.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing
        )
        painter.setPen(QColor("#172b4d"))
        font = QFont("Sans Serif")
        font.setPixelSize(26)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(32, 22, width - 64, 38), Qt.AlignmentFlag.AlignLeft, title)
        font.setPixelSize(17)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(
            QRectF(32, 66, width - 64, 76),
            Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
            detail,
        )
        area = QRectF(28, 154, width - 56, height - 208)
        scale = min(area.width() / source_rect.width(), area.height() / source_rect.height())
        target = QRectF(0, 0, source_rect.width() * scale, source_rect.height() * scale)
        target.moveCenter(area.center())
        scene.render(painter, target, source_rect, Qt.AspectRatioMode.KeepAspectRatio)
        font.setPixelSize(15)
        painter.setFont(font)
        painter.setPen(QColor("#526179"))
        painter.drawText(
            QRectF(32, height - 38, width - 64, 25),
            Qt.AlignmentFlag.AlignLeft,
            "[distance, predecessor]  ·  Yellow: tentative  ·  Green: visited  ·  "
            "Red border: target  ·  Teal edges: shortest path",
        )
    finally:
        painter.end()
    return image


def save_image(image: QImage, path: Path) -> None:
    if not image.save(str(path), "PNG"):
        raise OSError(f"Could not write image to {path}.")


def _detail(state: DijkstraState, start: int, target: int, final: bool) -> str:
    detail = (
        f"Start: {start}   Target: {target}   Current: "
        f"{state.current_node if state.current_node is not None else '—'}   "
        f"Settled nodes: {len(state.visited)}\n"
    )
    if final:
        path = reconstruct_path(state, start, target)
        if not path:
            return detail + "Target unreachable — no reachable unvisited nodes remain."
        return (
            detail
            + f"Shortest distance: {format_distance(state.distances[target])}   Path: "
            + (" → ".join(map(str, path)))
        )
    if state.current_node is None:
        return detail + "Initial labels: the start distance is 0; every other distance is ∞."
    updated = ", ".join(map(str, sorted(state.updated_nodes))) or "none"
    return detail + f"Settled node {state.current_node}; improved labels: {updated}."


def export_graph(
    graph: nx.Graph,
    positions: PositionMap,
    states: list[DijkstraState],
    start: int,
    target: int,
    index: int,
    kind: ExportKind,
    output_dir: Path,
) -> Path:
    if not states or not 0 <= index < len(states):
        raise ValueError("Initialize Dijkstra before exporting a phase.")
    if kind not in {"current", "all", "combined", "final"}:
        raise ValueError(f"Unknown export type: {kind}.")
    view = GraphView(graph, positions)
    view.set_editable(False)
    try:
        # Use one shared extent, including every label, so phases align in exports.
        bounds = QRectF()
        for state in states:
            view.apply_state(state, start, target)
            bounds = bounds.united(view.scene().itemsBoundingRect())
        bounds = bounds.adjusted(-30, -30, 30, 30)

        def render(state_index: int, width=1600, height=1100) -> QImage:
            final = state_index == len(states) - 1
            state = states[state_index]
            view.apply_state(state, start, target, final)
            return render_scene(
                view.scene(),
                bounds,
                f"Dijkstra · Step {state.step} / {len(states) - 1}",
                _detail(state, start, target, final),
                width,
                height,
            )

        run_dir = output_dir / datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        run_dir.mkdir(parents=True)
        if kind == "all":
            destination = run_dir / "steps"
            destination.mkdir()
            for state_index in range(len(states)):
                save_image(render(state_index), destination / f"step_{state_index:02d}.png")
        elif kind == "combined":
            from dijkstra_visualizer.export.composite_exporter import combine_phases

            destination = run_dir / "all_steps.png"
            images = (render(i, 1200, 860) for i in range(len(states)))
            save_image(combine_phases(images, len(states)), destination)
        else:
            state_index = len(states) - 1 if kind == "final" else index
            name = "final_path.png" if kind == "final" else f"current_step_{index:02d}.png"
            destination = run_dir / name
            save_image(render(state_index), destination)
        return destination
    finally:
        view.close()
        view.deleteLater()
