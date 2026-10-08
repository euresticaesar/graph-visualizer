"""One complete landscape slide per state, shared by PNG, PDF, SVG and preview.

Lists reflow into columns and tables scale together to fit the available area.
No matrix cells, arcs, explanations or ID references continue onto another page.
"""

import math
from dataclasses import dataclass

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QImage, QPainter, QPen

from graph_visualizer.core.dijkstra import route_description
from graph_visualizer.core.graph import ordered_arcs
from graph_visualizer.core.models import format_number
from graph_visualizer.ui.graph_view import GraphView
from graph_visualizer.ui.themes import matrix_colors, palette_for, row_color

WRAP = Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap
CELL_WRAP = Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWrapAnywhere
SLIDE_WIDTH, SLIDE_HEIGHT = 1920, 1080
MARGIN, GAP = 32, 12


def text_font(size, bold=False):
    result = QFont("Sans Serif")
    result.setPixelSize(max(1, round(size)))
    result.setBold(bold)
    return result


@dataclass(frozen=True)
class SlideOptions:
    simple: bool = False
    show_state_labels: bool = True
    show_edge_ids: bool = False
    theme: str = "light"
    accent: str = ""
    resolution: int = 1920
    font_scale: float = 1.0
    graph_font_scale: float = 1.0
    layout: str = "balanced"
    show_legend: bool = True
    show_explanation: bool = True
    title: str = ""
    group_size: int = 4

    def __post_init__(self):
        if self.resolution not in {1920, 2560, 3840}:
            raise ValueError("Selecciona una resolución de 1920, 2560 o 3840 píxeles.")
        if not 0.8 <= self.font_scale <= 1.5 or not 0.8 <= self.graph_font_scale <= 1.5:
            raise ValueError("La escala de texto debe estar entre 0.8 y 1.5.")
        if self.layout not in {"balanced", "graph", "tables"} or self.group_size not in {2, 4}:
            raise ValueError("Distribución de exportación no válida.")


@dataclass
class TableBlock:
    kind: str
    title: str
    headers: list
    entries: tuple
    columns: tuple
    widths: list
    row_height: float
    header_height: float = 26
    title_height: float = 28
    row_offset: int = 0
    col_offset: int = 0
    scale: float = 1.0

    @property
    def natural_width(self):
        return sum(self.widths)

    @property
    def natural_height(self):
        return self.title_height + self.header_height + len(self.entries) * self.row_height

    @property
    def width(self):
        return self.natural_width * self.scale

    @property
    def height(self):
        return self.natural_height * self.scale

    def values(self, state, entry):
        f = format_number
        if self.kind == "matrix":
            return [state.nodes[entry]] + [f(state.matrix[entry][j]) for j in self.columns]
        if self.kind == "intermediates":
            return [state.nodes[entry]] + [
                state.intermediates[entry][j] or "—" for j in self.columns
            ]
        if self.kind == "arcs":
            u, v, key, weight = entry
            return [u, v, str(key), f(weight)]
        if self.kind == "glossary":
            return list(entry)
        node = entry
        if self.kind == "astar":
            return [
                node,
                f(state.distances[node]),
                f(state.heuristics[node]),
                f(state.distances[node] + state.heuristics[node]),
                state.predecessors[node] or "—",
            ]
        return [node, f(state.distances[node]), state.predecessors[node] or "—"]


@dataclass
class PagePlan:
    graph: bool
    blocks: list
    graph_rect: QRectF | None = None


def wrapped_height(text, width, metrics, flags=WRAP):
    return math.ceil(metrics.boundingRect(QRectF(0, 0, width, 100000), flags, text).height())


def header_geometry(options, graph=True):
    scale = options.font_scale
    title_height = (
        min(
            2 * QFontMetricsF(text_font(28 * scale, True)).height(),
            wrapped_height(options.title, 1856, QFontMetricsF(text_font(28 * scale, True))),
        )
        + 8
        if options.title
        else 0
    )
    heading_height = QFontMetricsF(text_font(26 * scale, True)).height() + 6
    text_height = QFontMetricsF(text_font(18 * scale)).height() + 4
    title_y = 22
    heading_y = title_y + title_height
    page_y = heading_y + heading_height
    explanation_y = page_y + text_height + 6
    explanation_height = 3 * text_height if graph and options.show_explanation else 0
    return title_y, heading_y, page_y, explanation_y, explanation_height


def content_top(options, graph=True):
    *_, explanation_y, explanation_height = header_geometry(options, graph)
    return explanation_y + explanation_height + GAP


def footer_height(options, algorithm):
    if not options.show_legend:
        return 20
    metrics = QFontMetricsF(text_font(14 * options.font_scale))
    return wrapped_height(legend_text(algorithm), 1856, metrics) + 24


def fitted_font(text, rect, preferred, flags=WRAP):
    """Preserve the entire string, reducing its font only when it would overflow."""
    size = preferred.pixelSize()
    metrics = QFontMetricsF(preferred)
    bounds = metrics.boundingRect(rect, flags, text)
    if bounds.height() <= rect.height() and bounds.width() <= rect.width():
        return preferred
    low, high = 1, size
    while low < high:
        mid = (low + high + 1) // 2
        candidate = QFont(preferred)
        candidate.setPixelSize(mid)
        bounds = QFontMetricsF(candidate).boundingRect(rect, flags, text)
        if bounds.height() <= rect.height() and bounds.width() <= rect.width():
            low = mid
        else:
            high = mid - 1
    result = QFont(preferred)
    result.setPixelSize(low)
    return result


def draw_fitted_text(painter, rect, text, *, centered=False, cell=False):
    flags = CELL_WRAP if cell else WRAP
    metrics = QFontMetricsF(painter.font())
    if any(metrics.horizontalAdvance(word) > rect.width() for word in str(text).split()):
        flags = CELL_WRAP
    if centered:
        flags = Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWrapAnywhere
    painter.save()
    painter.setFont(fitted_font(str(text), rect, painter.font(), flags))
    painter.drawText(rect, flags, str(text))
    painter.restore()


def table_blocks(graph, algorithm, options, aliases=None, *, rows_per_block=None):
    """Retain every entry; list blocks are columns on the same slide."""
    if options.simple:
        return []
    nodes = tuple(sorted(graph))
    aliases = aliases or {n: n for n in nodes}
    scale = options.font_scale
    metrics = QFontMetricsF(text_font(18 * scale))
    row_height = metrics.height() + 4
    arcs = ordered_arcs(graph)
    max_weight = max((abs(w) for *_, w in arcs), default=0)
    magnitude = max_weight * max(1, len(nodes)) * 2
    number_sample = (
        "-0.123456789012e-123" if any(w != int(w) for *_, w in arcs) else format_number(-magnitude)
    )

    def width(texts, minimum=26, maximum=None):
        result = max(
            minimum, max((metrics.horizontalAdvance(str(t)) for t in texts), default=0) + 10
        )
        return min(maximum, result) if maximum else result

    id_width = width([aliases[n] for n in nodes], maximum=260)
    numeric = width([number_sample, "∞", "−∞"])
    result = []

    def add(kind, title, headers, entries, widths, *, columns=(), height=row_height):
        header_height = max(
            row_height,
            *(
                wrapped_height(aliases.get(h, h), w - 8, metrics, CELL_WRAP) + 4
                for h, w in zip(headers, widths, strict=True)
            ),
        )
        limit = len(entries) if kind in {"matrix", "intermediates"} else rows_per_block
        limit = max(1, limit or len(entries))
        for offset in range(0, len(entries), limit):
            rows = entries[offset : offset + limit]
            name = title + (f" · {offset + 1}–{offset + len(rows)}" if len(entries) > limit else "")
            title_height = (
                wrapped_height(name, sum(widths), QFontMetricsF(text_font(20 * scale, True))) + 6
            )
            result.append(
                TableBlock(
                    kind=kind,
                    title=name,
                    headers=headers,
                    entries=tuple(rows),
                    columns=tuple(columns),
                    widths=widths,
                    row_height=height,
                    header_height=header_height,
                    title_height=title_height,
                    row_offset=offset,
                )
            )

    if algorithm == "Floyd-Warshall":
        # A few long numbers should shrink inside their cells, rather than force
        # every value in both matrices into smaller text. Keep all digits intact.
        cell_width = max(id_width, min(numeric, width(["−999"])))
        height = max(
            row_height,
            *(wrapped_height(aliases[n], cell_width - 8, metrics, CELL_WRAP) + 4 for n in nodes),
        )
        for kind, title in (
            ("matrix", "Distancias D"),
            ("intermediates", "Recorridos · intermedios"),
        ):
            add(
                kind,
                title,
                [""] + list(nodes),
                tuple(range(len(nodes))),
                [id_width] + [cell_width] * len(nodes),
                columns=tuple(range(len(nodes))),
                height=height,
            )
    elif algorithm == "A*":
        add(
            "astar",
            "A* · prioridades",
            ["Nodo", "g", "h", "f = g + h", "π"],
            nodes,
            [
                max(id_width, width(["Nodo"])),
                numeric,
                numeric,
                max(numeric, width(["f = g + h"])),
                max(id_width, width(["π"])),
            ],
        )
    elif algorithm == "Bellman-Ford" or (algorithm == "Dijkstra" and options.layout == "tables"):
        add(
            "distances",
            "V / d / π",
            ["Nodo", "d", "π"],
            nodes,
            [max(id_width, width(["Nodo"])), numeric, id_width],
        )
        if algorithm == "Bellman-Ford":
            add(
                "arcs",
                "Arcos ordenados",
                ["De", "A", "ID", "Peso"],
                arcs,
                [
                    max(id_width, width(["De"])),
                    max(id_width, width(["A"])),
                    width(["ID", *(k for _, _, k, _ in arcs)]),
                    width(["Peso", *(format_number(w) for *_, w in arcs)]),
                ],
            )
    entries = tuple((alias, node) for node, alias in aliases.items() if alias != node)
    if entries:
        full_width = width([n for _, n in entries], maximum=640)
        height = max(
            row_height,
            *(wrapped_height(n, full_width - 8, metrics, CELL_WRAP) + 4 for _, n in entries),
        )
        add(
            "glossary",
            "IDs completos · referencia de etiquetas",
            ["Etiqueta", "ID completo"],
            entries,
            [max(id_width, width(["Etiqueta"])), max(full_width, width(["ID completo"]))],
            height=height,
        )
    return result


def pack_blocks(blocks, area, scale):
    x, y, shelf = area.left(), area.top(), 0
    placements = []
    for block in blocks:
        width, height = block.natural_width * scale, block.natural_height * scale
        if width > area.width() + 0.001:
            return None
        if x > area.left() and x + width > area.right() + 0.001:
            x, y, shelf = area.left(), y + shelf + GAP, 0
        if y + height > area.bottom() + 0.001:
            return None
        placements.append((block, x, y))
        x += width + GAP
        shelf = max(shelf, height)
    return placements


def fit_blocks(blocks, area):
    placements = pack_blocks(blocks, area, 1)
    if placements is not None:
        return 1.0, placements
    low, high = 0.0, 1.0
    for _ in range(14):
        scale = (low + high) / 2
        packed = pack_blocks(blocks, area, scale)
        if packed is None:
            high = scale
        else:
            low, placements = scale, packed
    return low, placements


def page_plans(graph, algorithm, options, aliases=None, *, graph_bounds=None):
    if options.simple:
        return [PagePlan(True, [], QRectF(0, 0, SLIDE_WIDTH, SLIDE_HEIGHT))]
    top, footer = content_top(options), footer_height(options, algorithm)
    body = QRectF(MARGIN, top, SLIDE_WIDTH - 2 * MARGIN, SLIDE_HEIGHT - top - footer)
    graph_bounds = graph_bounds or QRectF(0, 0, 1800, 1000)
    fractions = {
        "balanced": (0.46, 0.52, 0.40),
        "graph": (0.62, 0.56),
        "tables": (0.34, 0.40),
    }[options.layout]
    layouts = []
    for fraction in fractions:
        plot = QRectF(body.left(), body.top(), body.width() * fraction - GAP, body.height())
        tables = QRectF(
            plot.right() + GAP, body.top(), body.right() - plot.right() - GAP, body.height()
        )
        layouts.append((plot, tables))
    for fraction in (0.35, 0.45):
        plot = QRectF(body.left(), body.top(), body.width(), body.height() * fraction - GAP)
        tables = QRectF(
            body.left(), plot.bottom() + GAP, body.width(), body.bottom() - plot.bottom() - GAP
        )
        layouts.append((plot, tables))
    arc_count = len(ordered_arcs(graph)) if algorithm == "Bellman-Ford" else 0
    count = max(len(graph), arc_count)
    limits = {len(graph), count, 8, 12, 16, 20, 24, 30, 40, 48, 64, 96}
    limits.update(math.ceil(count / k) for k in range(1, 13))
    limits.update(math.ceil(len(graph) / k) for k in range(1, 5))
    if algorithm == "Floyd-Warshall":
        limits = {len(graph)}
    best = None
    for limit in sorted(n for n in limits if 0 < n <= count):
        blocks = table_blocks(graph, algorithm, options, aliases, rows_per_block=limit)
        if not blocks:
            return [PagePlan(True, [], body)]
        for plot, tables in layouts:
            scale, placements = fit_blocks(blocks, tables)
            if not scale:
                continue
            graph_scale = min(
                plot.width() / graph_bounds.width(), plot.height() / graph_bounds.height()
            )
            table_font = 18 * options.font_scale * scale
            graph_font = 15 * options.graph_font_scale * graph_scale
            score = table_font**0.45 * graph_font**0.55 - len(blocks) * 0.002
            if best is None or score > best[0]:
                best = score, plot, placements, scale
    if best is None:
        raise ValueError("No se pudo componer el contenido de la diapositiva.")
    _, plot, placements, scale = best
    for block, _, _ in placements:
        block.scale = scale
    return [PagePlan(True, placements, plot)]


def page_count(graph, algorithm, options):
    """Every state is one complete slide, independent of density and typography."""
    return 1


def draw_block(painter, block, x, y, state, palette, options, aliases=None):
    aliases = aliases or {}
    painter.save()
    painter.translate(x, y)
    painter.scale(block.scale, block.scale)
    painter.setFont(text_font(20 * options.font_scale, True))
    painter.setPen(QColor(palette.text))
    draw_fitted_text(
        painter, QRectF(0, 0, block.natural_width, block.title_height - 4), block.title
    )
    painter.setFont(text_font(18 * options.font_scale))
    for row, entry in enumerate([None, *block.entries]):
        values = block.headers if entry is None else block.values(state, entry)
        cursor = 0
        for col, (value, width) in enumerate(zip(values, block.widths, strict=True)):
            top = block.title_height + (
                block.header_height + (row - 1) * block.row_height if row else 0
            )
            rect = QRectF(cursor, top, width, block.row_height if row else block.header_height)
            green = active = False
            color = palette.header if row == 0 else palette.surface
            if block.kind in {"matrix", "intermediates"}:
                if row and col:
                    color, green, active = matrix_colors(
                        state, entry, block.columns[col - 1], palette
                    )
                elif (col == 0 and row and entry == state.k) or (
                    row == 0 and col and block.columns[col - 1] == state.k
                ):
                    color = palette.k_fill
            elif row and block.kind != "glossary":
                color = row_color(state, block.kind, values, palette)
            painter.fillRect(rect, QColor(color))
            painter.setPen(QPen(QColor(palette.border), 1))
            painter.drawRect(rect)
            if green:
                painter.setPen(QPen(QColor(palette.k_border), 2))
                painter.drawRect(rect.adjusted(1, 1, -1, -1))
            if active:
                painter.setPen(QPen(QColor(palette.active), 2))
                painter.drawRect(rect.adjusted(3, 3, -3, -3))
            painter.setPen(QColor(palette.text))
            if block.kind != "glossary":
                value = aliases.get(str(value), value)
            draw_fitted_text(
                painter, rect.adjusted(4, 2, -4, -2), str(value), centered=True, cell=True
            )
            cursor += width
    painter.restore()


def legend_text(algorithm):
    common = (
        "Línea gruesa: ruta · Naranja: comparación · Borde azul: destino · "
        "Rojo: sin mínimo finito. "
    )
    if algorithm == "Floyd-Warshall":
        return (
            common + "Matrices: verde = fila/columna k; amarillo = mejora; violeta = (i,j). "
            "∞: sin ruta; −∞: ciclo negativo."
        )
    if algorithm == "A*":
        return (
            common + "g: costo acumulado · h: estimación admisible · f = g + h · "
            "π: predecesor; —: sin predecesor."
        )
    return (
        common + "[distancia, predecesor] · π: predecesor · Negritas/amarillo: mejora · "
        "∞: sin ruta · —: sin predecesor."
    )


class SlideRenderer:
    def __init__(self, graph, positions, options):
        self.graph, self.options = graph, options
        self.palette = palette_for(options.theme, options.accent)
        self.view = GraphView(
            graph, positions, palette=self.palette, font_scale=options.graph_font_scale
        )
        self.view.set_editable(False)
        self.view.set_state_labels_visible(options.show_state_labels)
        self.view.set_edge_ids_visible(options.show_edge_ids)
        self.aliases = {n: item.display_id for n, item in self.view.nodes.items()}
        self.plans = {}
        self.bounds = self.view.scene().itemsBoundingRect()
        if not options.simple:
            for item in self.view.nodes.values():
                reserve = QRectF(
                    item.pos().x() - 220 * options.graph_font_scale,
                    item.pos().y() - 70 * options.graph_font_scale,
                    440 * options.graph_font_scale,
                    150 * options.graph_font_scale,
                )
                self.bounds = self.bounds.united(reserve)
        self.bounds = self.bounds.adjusted(-35, -35, 35, 35)

    def plan(self, algorithm):
        if algorithm not in self.plans:
            self.plans[algorithm] = page_plans(
                self.graph, algorithm, self.options, self.aliases, graph_bounds=self.bounds
            )
        return self.plans[algorithm]

    def paint(self, painter, state, start, target, index, count, part=0):
        options, palette = self.options, self.palette
        plan = self.plan(state.algorithm)[part]
        painter.save()
        try:
            painter.setRenderHints(
                QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing
            )
            painter.fillRect(QRectF(0, 0, SLIDE_WIDTH, SLIDE_HEIGHT), QColor(palette.canvas))
            if not options.simple:
                painter.setPen(QColor(palette.text))
                title_y, heading_y, page_y, detail_y, detail_height = header_geometry(options)
                if options.title:
                    painter.setFont(text_font(28 * options.font_scale, True))
                    draw_fitted_text(
                        painter, QRectF(32, title_y, 1856, heading_y - title_y - 4), options.title
                    )
                painter.setFont(text_font(26 * options.font_scale, True))
                draw_fitted_text(
                    painter,
                    QRectF(32, heading_y, 1856, page_y - heading_y),
                    f"{state.algorithm} · {state.phase} · Iteración {state.iteration} · "
                    f"Paso {index}/{count - 1} · Evento {state.step}",
                )
                painter.setFont(text_font(18 * options.font_scale))
                draw_fitted_text(
                    painter,
                    QRectF(32, page_y, 1856, detail_y - page_y),
                    f"Origen: {self.aliases[start]} · Destino: {self.aliases[target]}",
                )
                if options.show_explanation:
                    detail = state.explanation + "\n" + route_description(state, start, target)
                    for node in sorted(self.aliases, key=len, reverse=True):
                        if self.aliases[node] != node:
                            detail = detail.replace(node, self.aliases[node])
                    draw_fitted_text(painter, QRectF(32, detail_y, 1856, detail_height), detail)
            self.view.apply_state(state, start, target, state.phase == "Resultado")
            if options.simple:
                for item in self.view.nodes.values():
                    item.label.hide()
                    item.caption.hide()
            graph_rect = QRectF(plan.graph_rect)
            graph_scale = min(
                graph_rect.width() / self.bounds.width(),
                graph_rect.height() / self.bounds.height(),
            )
            graph_rect.setSize(self.bounds.size() * graph_scale)
            graph_rect.moveCenter(plan.graph_rect.center())
            self.view.scene().render(
                painter, graph_rect, self.bounds, Qt.AspectRatioMode.KeepAspectRatio
            )
            for block, x, y in plan.blocks:
                draw_block(painter, block, x, y, state, palette, options, self.aliases)
            if options.show_legend and not options.simple:
                painter.setFont(text_font(14 * options.font_scale))
                painter.setPen(QColor(palette.muted))
                footer = footer_height(options, state.algorithm)
                draw_fitted_text(
                    painter,
                    QRectF(32, 1080 - footer + 4, 1856, footer - 12),
                    legend_text(state.algorithm),
                )
        finally:
            painter.restore()

    def image(self, references, states, start, target):
        """Keep every complete slide at its chosen resolution, also in a montage."""
        width = self.options.resolution
        columns = 2 if len(references) > 1 else 1
        image = QImage(
            width * columns, width * 9 // 16 * columns, QImage.Format.Format_ARGB32_Premultiplied
        )
        if image.isNull() or image.width() * image.height() > 100_000_000:
            raise ValueError("No hay memoria suficiente para la imagen.")
        image.fill(QColor(self.palette.canvas))
        painter = QPainter(image)
        try:
            self.paint_group(painter, references, states, start, target)
        finally:
            painter.end()
        return image

    def paint_group(self, painter, references, states, start, target):
        scale = self.options.resolution / SLIDE_WIDTH
        columns = 2 if len(references) > 1 else 1
        vertical_offset = 540 if len(references) == 2 else 0
        for slot, (index, part) in enumerate(references):
            painter.save()
            painter.scale(scale, scale)
            painter.translate(
                (slot % columns) * SLIDE_WIDTH, (slot // columns) * SLIDE_HEIGHT + vertical_offset
            )
            self.paint(painter, states[index], start, target, index, len(states), part)
            painter.restore()

    def close(self):
        self.view.close()
        self.view.deleteLater()
