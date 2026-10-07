"""PNG rendering of the same immutable states used by the desktop navigation."""

import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen

from graph_visualizer.core.dijkstra import route_description
from graph_visualizer.core.graph import ordered_arcs
from graph_visualizer.core.models import format_number
from graph_visualizer.ui.graph_view import GraphView
from graph_visualizer.ui.state_panel import matrix_style

ExportKind = Literal["current", "all", "combined", "final"]
MAX_COMBINED_PIXELS = 24_000_000
MAX_COMBINED_SIDE = 12000


def save_image(image: QImage, path: Path) -> None:
    if not image.save(str(path), "PNG"):
        raise OSError(f"No se pudo guardar la imagen en {path}.")


def font(size, bold=False):
    result = QFont("Sans Serif")
    result.setPixelSize(size)
    result.setBold(bold)
    return result


def table_data(graph, state):
    f = format_number
    if state.algorithm == "Floyd-Warshall":
        return [
            (
                "Distancias D",
                [""] + list(state.nodes),
                [[node] + [f(v) for v in state.matrix[i]] for i, node in enumerate(state.nodes)],
            ),
            (
                "Recorridos · intermedios",
                [""] + list(state.nodes),
                [
                    [node] + [v if v is not None else "—" for v in state.intermediates[i]]
                    for i, node in enumerate(state.nodes)
                ],
            ),
        ]
    if state.algorithm == "Bellman-Ford":
        return [
            (
                "V / d / π",
                ["Nodo", "Distancia", "Predecesor"],
                [[n, f(state.distances[n]), state.predecessors[n] or "—"] for n in sorted(graph)],
            ),
            (
                "Arcos ordenados",
                ["Origen", "Destino", "ID", "Peso"],
                [[u, v, str(k), f(w)] for u, v, k, w in ordered_arcs(graph)],
            ),
        ]
    return []


def table_widths(headers, rows):
    metrics = QFontMetricsF(font(18))
    return [
        max(
            62,
            math.ceil(max(metrics.horizontalAdvance(str(row[col])) for row in [headers, *rows]))
            + 24,
        )
        for col in range(len(headers))
    ]


def draw_table(painter, x, y, title, headers, rows, widths, state, graph):
    painter.setFont(font(22, True))
    painter.setPen(QColor("#172b4d"))
    painter.drawText(QRectF(x, y, sum(widths), 32), title)
    painter.setFont(font(18))
    arcs = ordered_arcs(graph) if state.algorithm == "Bellman-Ford" else ()
    for row_index, row in enumerate([headers, *rows]):
        offset = x
        for col, (value, width) in enumerate(zip(row, widths, strict=True)):
            rect = QRectF(offset, y + 38 + row_index * 32, width, 32)
            background, green, active = "#ffffff", False, False
            if row_index == 0 or (state.algorithm == "Floyd-Warshall" and col == 0):
                background = "#e2e8f0"
            if state.algorithm == "Floyd-Warshall":
                if row_index and col:
                    background, green, active = matrix_style(state, row_index - 1, col - 1)
                elif state.k is not None and (
                    (row_index == 0 and col - 1 == state.k)
                    or (col == 0 and row_index - 1 == state.k)
                ):
                    background = "#bbf7d0"
            elif row_index:
                if title.startswith("Arcos") and arcs[row_index - 1][:3] == state.current_edge:
                    background = "#fed7aa"
                elif title.startswith("V"):
                    node = rows[row_index - 1][0]
                    if node in state.affected:
                        background = "#fecaca"
                    elif node in state.updated_nodes:
                        background = "#fef08a"
            painter.fillRect(rect, QColor(background))
            painter.setPen(QPen(QColor("#cbd5e1"), 1))
            painter.drawRect(rect)
            if green:
                painter.setPen(QPen(QColor("#15803d"), 2))
                painter.drawRect(rect.adjusted(1, 1, -1, -1))
            if active:
                painter.setPen(QPen(QColor("#7c3aed"), 2))
                painter.drawRect(rect.adjusted(3, 3, -3, -3))
            painter.setPen(QColor("#172b4d"))
            painter.drawText(rect.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignCenter, str(value))
            offset += width


def legend(state, graph):
    common = "Turquesa: ruta consultada · Naranja: conexión comparada · Rojo: ciclo negativo."
    if state.algorithm == "Floyd-Warshall":
        return (
            common + " Verde: fila y columna k; amarillo: mejoras de k; violeta: (i,j). "
            "Recorridos: destino directo, k intermedio, nodo propio en diagonal, — sin ruta. "
            "Origen/destino solo consultan la ruta. −∞: sin mínimo finito."
        )
    if state.algorithm == "Bellman-Ford":
        return (
            common
            + " Tabla: V nodo, d distancia, π predecesor. −∞: sin mínimo finito. "
            + (
                "Cada conexión no dirigida se examina como dos arcos."
                if not graph.is_directed()
                else "Arcos ordenados por origen, destino e ID."
            )
        )
    return common + " [distancia, predecesor] · Verde: fijado · Amarillo: tentativo."


@dataclass
class ImageLayout:
    bounds: QRectF
    width: int
    height: int
    graph_height: int
    tables: list
    widths: list
    detail: str
    detail_height: int
    legend_height: int
    top: int


def measure_state(view, graph, state, start, target, *, simple=False):
    """Measure the export using its scene and fonts, without allocating a raster image."""
    if simple:
        for item in view.nodes.values():
            item.label.hide()
            item.caption.hide()
    bounds = view.scene().itemsBoundingRect().adjusted(-35, -35, 35, 35)
    graph_width = max(1200, math.ceil(bounds.width()))
    graph_height = max(650, math.ceil(bounds.height()))
    tables = [] if simple else table_data(graph, state)
    widths = [table_widths(headers, rows) for _, headers, rows in tables]
    for (title, _, _), columns in zip(tables, widths, strict=True):
        extra = math.ceil(QFontMetricsF(font(22, True)).horizontalAdvance(title)) + 8 - sum(columns)
        if extra > 0:
            columns[-1] += extra
    width = max(graph_width + 64, sum(sum(w) for w in widths) + 96)
    detail = f"Origen: {start} · Destino: {target}. {state.explanation}\n" + route_description(
        state, start, target
    )
    flags = Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap
    metrics = QFontMetricsF(font(20))
    detail_height = (
        math.ceil(metrics.boundingRect(QRectF(0, 0, width - 64, 100000), flags, detail).height())
        + 16
    )
    legend_height = (
        math.ceil(
            metrics.boundingRect(
                QRectF(0, 0, width - 64, 100000), flags, legend(state, graph)
            ).height()
        )
        + 16
    )
    top = 0 if simple else 78 + detail_height
    tables_height = max((len(rows) * 32 + 80 for _, _, rows in tables), default=0)
    height = graph_height if simple else top + graph_height + tables_height + legend_height + 40
    if simple:
        width = graph_width
    if width * height > 100_000_000:
        raise ValueError("La imagen individual supera 100 megapíxeles; reduce el layout del grafo.")
    return ImageLayout(
        bounds,
        width,
        height,
        graph_height,
        tables,
        widths,
        detail,
        detail_height,
        legend_height,
        top,
    )


def render_state(
    graph,
    positions,
    state,
    start,
    target,
    index,
    count,
    *,
    simple=False,
    show_state_labels=True,
    show_edge_ids=False,
):
    view = GraphView(graph, positions)
    view.set_editable(False)
    view.set_state_labels_visible(show_state_labels)
    view.set_edge_ids_visible(show_edge_ids)
    try:
        view.apply_state(state, start, target, state.phase == "Resultado")
        layout = measure_state(view, graph, state, start, target, simple=simple)
        bounds, width, height = layout.bounds, layout.width, layout.height
        graph_height, top = layout.graph_height, layout.top
        tables, widths = layout.tables, layout.widths
        detail_height, legend_height = layout.detail_height, layout.legend_height
        flags = Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap
        image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
        if image.isNull():
            raise ValueError("No hay memoria suficiente para la imagen.")
        image.fill(QColor("#f8fafc"))
        painter = QPainter(image)
        try:
            painter.setRenderHints(
                QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing
            )
            if not simple:
                painter.setPen(QColor("#172b4d"))
                painter.setFont(font(28, True))
                painter.drawText(
                    QRectF(32, 22, width - 64, 45),
                    f"{state.algorithm} · {state.phase} · Iteración {state.iteration} "
                    f"· Paso {index}/{count - 1} · Evento {state.step}",
                )
                painter.setFont(font(20))
                painter.drawText(QRectF(32, 78, width - 64, detail_height), flags, layout.detail)
            area = QRectF(
                32 if not simple else 0, top, width - 64 if not simple else width, graph_height
            )
            scale = min(area.width() / bounds.width(), area.height() / bounds.height())
            graph_area = QRectF(0, 0, bounds.width() * scale, bounds.height() * scale)
            graph_area.moveCenter(area.center())
            view.scene().render(painter, graph_area, bounds, Qt.AspectRatioMode.KeepAspectRatio)
            x = 32
            for (title, headers, rows), columns in zip(tables, widths, strict=True):
                draw_table(
                    painter, x, top + graph_height, title, headers, rows, columns, state, graph
                )
                x += sum(columns) + 32
            if not simple:
                painter.setFont(font(20))
                painter.setPen(QColor("#475569"))
                painter.drawText(
                    QRectF(32, height - legend_height - 16, width - 64, legend_height),
                    flags,
                    legend(state, graph),
                )
        finally:
            painter.end()
        return image
    finally:
        view.close()
        view.deleteLater()


def combined_capacity(width, height, remaining):
    return max(
        1,
        min(4, MAX_COMBINED_PIXELS // (width * height), MAX_COMBINED_SIDE // height, remaining),
    )


def combined_image_count_job(
    graph,
    positions,
    states,
    start,
    target,
    *,
    simple=False,
    show_state_labels=True,
    show_edge_ids=False,
):
    """Cooperative preview with the same sizes and page limits as the PNG exporter."""
    view = GraphView(graph, positions)
    view.set_editable(False)
    view.set_state_labels_visible(show_state_labels)
    view.set_edge_ids_visible(show_edge_ids)
    size = None
    capacity = used = pages = 0
    try:
        for index, state in enumerate(states):
            view.apply_state(state, start, target, state.phase == "Resultado")
            layout = measure_state(view, graph, state, start, target, simple=simple)
            current_size = (layout.width, layout.height)
            if current_size != size or used == capacity:
                pages += 1
                size = current_size
                used = 0
                capacity = combined_capacity(*size, len(states) - index)
            used += 1
            yield index + 1, pages
        return pages
    finally:
        view.close()
        view.deleteLater()


def export_job(
    graph,
    positions,
    states,
    start,
    target,
    index,
    kind,
    output_dir,
    *,
    show_state_labels=True,
    show_edge_ids=False,
    simple=False,
):
    """Cooperative job: one render per yield; callers may use a Qt timer between frames."""
    if not states or not 0 <= index < len(states):
        raise ValueError("Inicia un algoritmo antes de exportar.")
    if kind not in {"current", "all", "combined", "final"}:
        raise ValueError(f"Tipo de exportación desconocido: {kind}.")
    run_dir = output_dir / datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
    run_dir.mkdir(parents=True)
    indices = (
        list(range(len(states)))
        if kind in {"all", "combined"}
        else [len(states) - 1 if kind == "final" else index]
    )
    destination = run_dir
    combined = None
    painter = None
    page = 0
    used = 0
    capacity = 1
    cell_width = cell_height = 0

    def flush():
        nonlocal painter, combined, page, used
        if painter:
            painter.end()
            painter = None
            page += 1
            save_image(combined, run_dir / f"conjunta_{page:04d}.png")
            combined = None
            used = 0

    try:
        for progress, state_index in enumerate(indices):
            image = render_state(
                graph,
                positions,
                states[state_index],
                start,
                target,
                state_index,
                len(states),
                simple=simple,
                show_state_labels=show_state_labels,
                show_edge_ids=show_edge_ids,
            )
            if kind == "combined":
                # A page is a vertical sequence, with no reduction of individual frames.
                if combined is not None and (
                    image.width() != cell_width or image.height() != cell_height
                ):
                    flush()
                if combined is None:
                    cell_width, cell_height = image.width(), image.height()
                    capacity = combined_capacity(cell_width, cell_height, len(indices) - progress)
                    combined = QImage(
                        cell_width,
                        cell_height * capacity,
                        QImage.Format.Format_ARGB32_Premultiplied,
                    )
                    if combined.isNull():
                        raise ValueError("Memoria insuficiente para la imagen conjunta.")
                    combined.fill(QColor("#dce3ed"))
                    painter = QPainter(combined)
                painter.drawImage(0, used * cell_height, image)
                used += 1
                if used == capacity:
                    flush()
            else:
                path = run_dir / (
                    f"paso_{state_index:06d}.png"
                    if kind == "all"
                    else "resultado_final.png"
                    if kind == "final"
                    else f"paso_actual_{index:06d}.png"
                )
                save_image(image, path)
                if kind != "all":
                    destination = path
            yield progress + 1, len(indices)
        flush()
        return destination
    finally:
        if painter:
            painter.end()


def export_graph(*args, **kwargs) -> Path:
    job = export_job(*args, **kwargs)
    while True:
        try:
            next(job)
        except StopIteration as result:
            return result.value
