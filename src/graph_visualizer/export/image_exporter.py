"""PNG rendering of the same immutable states used by the desktop navigation."""

import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QMarginsF, QRectF, QSizeF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QImage,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QPen,
)

from graph_visualizer.core.dijkstra import route_description
from graph_visualizer.core.graph import ordered_arcs
from graph_visualizer.core.models import format_number
from graph_visualizer.ui.graph_view import GraphView as GraphView
from graph_visualizer.ui.state_panel import matrix_style

ExportKind = Literal["current", "all", "combined", "final"]
MAX_COMBINED_PIXELS = 100_000_000
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
    if state.algorithm == "A*":
        return [
            (
                "A* · prioridades",
                ["Nodo", "g", "h", "f = g + h", "Predecesor"],
                [
                    [
                        n,
                        f(state.distances[n]),
                        f(state.heuristics[n]),
                        f(state.distances[n] + state.heuristics[n]),
                        state.predecessors[n] or "—",
                    ]
                    for n in sorted(graph)
                ],
            )
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
                if (
                    title.startswith("Arcos")
                    and tuple(rows[row_index - 1][:2]) + (int(rows[row_index - 1][2]),)
                    == state.current_edge
                ):
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
    if state.algorithm == "A*":
        return "A*: g = costo acumulado; h = saltos mínimos × menor peso; f = g + h. " + common
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
    if state.algorithm in {"Bellman-Ford", "A*"}:
        block_rows = max(12, math.ceil(sum(len(rows) for _, _, rows in tables) / 6))
        tables = [
            (
                title
                if len(rows) <= block_rows
                else f"{title} · {offset + 1}–{min(offset + block_rows, len(rows))}",
                headers,
                rows[offset : offset + block_rows],
            )
            for title, headers, rows in tables
            for offset in range(0, len(rows), block_rows)
        ]
    widths = [table_widths(headers, rows) for _, headers, rows in tables]
    for (title, _, _), columns in zip(tables, widths, strict=True):
        extra = math.ceil(QFontMetricsF(font(22, True)).horizontalAdvance(title)) + 8 - sum(columns)
        if extra > 0:
            columns[-1] += extra
    width = max(1920, graph_width + 64, sum(sum(w) + 32 for w in widths) + 32)
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
        width = max(1920, graph_width)
    height = max(height, math.ceil(width * 9 / 16))
    width = max(width, math.ceil(height * 16 / 9))
    if simple:
        graph_height = height
    elif not tables:
        graph_height = height - top - legend_height - 40
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


def render_state(graph, positions, state, start, target, index, count, **options):
    """Render one complete landscape slide for the selected state."""
    from graph_visualizer.export.slide_renderer import SlideOptions, SlideRenderer

    renderer = SlideRenderer(graph, positions, SlideOptions(**options))
    image = QImage(
        renderer.options.resolution,
        renderer.options.resolution * 9 // 16,
        QImage.Format.Format_ARGB32_Premultiplied,
    )
    image.fill(QColor(renderer.palette.canvas))
    painter = QPainter(image)
    try:
        painter.scale(renderer.options.resolution / 1920, renderer.options.resolution / 1920)
        renderer.paint(painter, state, start, target, index, count)
    finally:
        painter.end()
        renderer.close()
    return image


def combined_capacity(width, height, remaining, group_size=4):
    # A 16:9 montage reserves a full 2×2 canvas, including a two-page montage.
    if width * height * 4 > MAX_COMBINED_PIXELS or max(width * 2, height * 2) > MAX_COMBINED_SIDE:
        return 1
    return max(1, min(group_size, remaining))


def combined_image_count_job(graph, positions, states, start, target, **options):
    """Count the fixed page plan once, without visiting every algorithm event."""
    from graph_visualizer.export.slide_renderer import SlideOptions, page_count

    if not states:
        return 0
    settings = SlideOptions(**options)
    pages = len(states) * page_count(graph, states[0].algorithm, settings)
    capacity = combined_capacity(
        settings.resolution, settings.resolution * 9 // 16, pages, settings.group_size
    )
    count = math.ceil(pages / capacity)
    yield len(states), count
    return count


def _page_groups(renderer, states, index, kind):
    if not states or not 0 <= index < len(states):
        raise ValueError("Inicia un algoritmo antes de exportar.")
    if kind not in {"current", "all", "combined", "final"}:
        raise ValueError(f"Tipo de exportación desconocido: {kind}.")
    indices = (
        range(len(states))
        if kind in {"all", "combined"}
        else [len(states) - 1 if kind == "final" else index]
    )
    total = sum(len(renderer.plan(states[i].algorithm)) for i in indices)
    capacity = (
        combined_capacity(
            renderer.options.resolution,
            renderer.options.resolution * 9 // 16,
            total,
            renderer.options.group_size,
        )
        if kind == "combined"
        else 1
    )
    pending = []
    progress = 0
    for i in indices:
        for part in range(len(renderer.plan(states[i].algorithm))):
            pending.append((i, part))
            progress += 1
            if len(pending) == capacity or progress == total:
                yield pending, progress, total
                pending = []
            else:
                yield None, progress, total


def export_frames(graph, positions, states, start, target, index, kind, **options):
    from graph_visualizer.export.slide_renderer import SlideOptions, SlideRenderer

    renderer = SlideRenderer(graph, positions, SlideOptions(**options))
    try:
        for refs, progress, total in _page_groups(renderer, states, index, kind):
            image = renderer.image(refs, states, start, target) if refs else None
            yield image, refs[-1][0] if refs else index, progress, total
    finally:
        renderer.close()


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
    output_format="png",
    execution_settings=None,
    **options,
):
    """Publish a complete, reproducible export atomically; closing the job cancels it."""
    import json
    import shutil
    import tempfile
    from dataclasses import asdict
    from importlib.metadata import version

    from PySide6.QtCore import QIODevice, QSaveFile, QSize
    from PySide6.QtSvg import QSvgGenerator

    from graph_visualizer.export.slide_renderer import SlideOptions, SlideRenderer
    from graph_visualizer.io.presets import Preset

    if output_format not in {"png", "pdf", "svg"}:
        raise ValueError("Formato de exportación desconocido.")
    if not states or not 0 <= index < len(states):
        raise ValueError("Inicia un algoritmo antes de exportar.")
    settings = SlideOptions(**options)
    renderer = SlideRenderer(graph, positions, settings)
    groups = _page_groups(renderer, states, index, kind)
    root = Path(output_dir)
    run_dir = None
    painter = device = None
    completed = False
    records = []
    event_records = {}
    pdf = None
    try:
        first = next(groups)
        root.mkdir(parents=True, exist_ok=True)
        run_dir = Path(tempfile.mkdtemp(prefix=".exportando_", dir=root))
        final_dir = root / datetime.now().strftime("%Y-%m-%d_%H-%M-%S_%f")
        from itertools import chain

        page = 0
        if output_format == "pdf":
            device = QSaveFile(str(run_dir / "diapositivas.pdf"))
            if not device.open(QIODevice.OpenModeFlag.WriteOnly):
                raise OSError(device.errorString())
            pdf = QPdfWriter(device)
            pdf.setResolution(96)
            pdf.setPageMargins(QMarginsF(0, 0, 0, 0), QPageLayout.Unit.Point)
            pdf.setTitle(settings.title or f"{states[0].algorithm} · {start} → {target}")
        for refs, progress, total in chain([first], groups):
            if refs:
                page += 1
                columns = 2 if len(refs) > 1 else 1
                width = settings.resolution * columns
                height = settings.resolution * 9 // 16 * columns
                state_index, _ = refs[0]
                name = (
                    f"conjunta_{page:04d}"
                    if kind == "combined"
                    else f"paso_{state_index:06d}"
                    if kind == "all"
                    else "resultado_final"
                    if kind == "final"
                    else f"paso_actual_{state_index:06d}"
                )
                if output_format == "pdf":
                    pdf.setPageSize(
                        QPageSize(QSizeF(width * 0.75, height * 0.75), QPageSize.Unit.Point)
                    )
                    if painter is None:
                        painter = QPainter(pdf)
                        if not painter.isActive():
                            raise OSError("No se pudo iniciar el documento PDF.")
                    elif not pdf.newPage():
                        raise OSError("No se pudo crear la página PDF.")
                    renderer.paint_group(painter, refs, states, start, target)
                    file_name = "diapositivas.pdf"
                elif output_format == "svg":
                    file_name = name + ".svg"
                    svg_file = QSaveFile(str(run_dir / file_name))
                    if not svg_file.open(QIODevice.OpenModeFlag.WriteOnly):
                        raise OSError(svg_file.errorString())
                    generator = QSvgGenerator()
                    generator.setOutputDevice(svg_file)
                    generator.setSize(QSize(width, height))
                    generator.setViewBox(QRectF(0, 0, width, height))
                    generator.setTitle(settings.title or states[state_index].algorithm)
                    svg_painter = QPainter(generator)
                    try:
                        if not svg_painter.isActive():
                            raise OSError("No se pudo iniciar el documento SVG.")
                        renderer.paint_group(svg_painter, refs, states, start, target)
                    finally:
                        if svg_painter.isActive() and not svg_painter.end():
                            raise OSError("No se pudo finalizar el SVG.")
                    if not svg_file.commit():
                        raise OSError(svg_file.errorString())
                else:
                    file_name = name + ".png"
                    save_image(renderer.image(refs, states, start, target), run_dir / file_name)
                records.append(
                    {
                        "file": file_name,
                        "page": page,
                        "size": [width, height],
                        "states": [
                            {
                                "index": i,
                                "event": states[i].step,
                                "part": j + 1,
                                "parts": len(renderer.plan(states[i].algorithm)),
                            }
                            for i, j in refs
                        ],
                    }
                )
                for i, _ in refs:
                    state = states[i]
                    if state.step not in event_records:
                        event_records[state.step] = {
                            "event": state.step,
                            "phase": state.phase,
                            "iteration": state.iteration,
                            "explanation": state.explanation,
                            "route": route_description(state, start, target),
                        }
            yield progress, total
        if painter is not None:
            if not painter.end():
                raise OSError("No se pudo finalizar el PDF.")
            painter = None
            if not device.commit():
                raise OSError(device.errorString())
        snapshot = Preset(
            settings.title or "Grafo exportado",
            graph,
            positions,
            {
                "algorithm": states[0].algorithm,
                "start": start,
                "target": target,
                "detail": len(states) == len(getattr(states, "events", states)),
            },
        ).document()
        if execution_settings:
            snapshot["settings"].update(execution_settings)
        manifest = {
            "version": 1,
            "application_version": version("graph-visualizer"),
            "status": "complete",
            "kind": kind,
            "format": output_format,
            "options": asdict(settings),
            "labels": renderer.aliases,
            "events": list(event_records.values()),
            "output_count": len(records),
            "outputs": records,
        }
        for filename, document in (("manifest.json", manifest), ("grafo.json", snapshot)):
            (run_dir / filename).write_text(
                json.dumps(document, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
                encoding="utf-8",
            )
        run_dir.rename(final_dir)
        completed = True
        if output_format == "pdf":
            return final_dir / "diapositivas.pdf"
        if kind in {"current", "final"} and len(records) == 1:
            return final_dir / records[0]["file"]
        return final_dir
    finally:
        groups.close()
        if painter is not None:
            painter.end()
        if device is not None and not completed:
            device.cancelWriting()
        renderer.close()
        if run_dir is not None and not completed:
            shutil.rmtree(run_dir, ignore_errors=True)


def export_graph(*args, **kwargs) -> Path:
    job = export_job(*args, **kwargs)
    while True:
        try:
            next(job)
        except StopIteration as result:
            return result.value


def slide_image(image):
    """Compatibility helper: fit a legacy raster into an HD slide."""
    if image.width() == 1920 and image.height() == 1080:
        return image
    slide = QImage(1920, 1080, QImage.Format.Format_ARGB32_Premultiplied)
    slide.fill(QColor("#f8fafc"))
    scaled = image.scaled(
        1920, 1080, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
    )
    painter = QPainter(slide)
    try:
        painter.drawImage((1920 - scaled.width()) // 2, (1080 - scaled.height()) // 2, scaled)
    finally:
        painter.end()
    return slide
