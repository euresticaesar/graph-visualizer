"""Didactic text with semantic emphasis, shared by raster and vector slides."""

from dataclasses import dataclass, replace

from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor, QTextDocument, QTextOption

from graph_visualizer.core.dijkstra import route_description
from graph_visualizer.core.models import format_number
from graph_visualizer.ui.themes import luminance


@dataclass(frozen=True)
class TextRun:
    text: str
    bold: bool = False
    role: str = "text"


def comparison_runs(state):
    """Describe operands and decisions from the record, without connection IDs."""
    comparison = state.comparison
    f = format_number
    if state.algorithm == "Floyd-Warshall":
        context = (
            f"Intermedio k = {state.nodes[state.k]} · "
            f"i = {comparison.source} · j = {comparison.target}. "
        )
        before = f"Anterior D[i,j]: {f(comparison.before)}; candidata D[i,k] + D[k,j]: "
    else:
        context = (
            f"Conexión {comparison.source} → {comparison.target} · Peso {f(comparison.weight)}. "
        )
        if state.phase == "Verificación":
            context = "Sondeo de ciclo negativo. " + context
        before = f"Anterior: {f(comparison.before)}; candidata: "
    decision_role = (
        "error"
        if state.phase == "Verificación" and comparison.improved
        else "current"
        if comparison.improved
        else "comparison"
    )
    runs = [
        TextRun(context, True, "active"),
        TextRun(before),
        TextRun(
            f"{f(comparison.left)} + {f(comparison.right)} = {f(comparison.candidate)}. ",
            True,
            "comparison",
        ),
        TextRun(
            f"¿Mejora estricta? {'Sí' if comparison.improved else 'No'}. "
            f"Resultante: {f(comparison.after)}.",
            True,
            decision_role,
        ),
    ]
    if state.algorithm != "Floyd-Warshall":
        runs.append(
            TextRun(
                f" Predecesor: {comparison.predecessor_before or '—'} → "
                f"{comparison.predecessor_after or '—'}.",
            )
        )
    return runs


def alias_runs(runs, aliases):
    substitutions = sorted(
        ((node, alias) for node, alias in aliases.items() if node != alias),
        key=lambda pair: len(pair[0]),
        reverse=True,
    )
    result = []
    for run in runs:
        text = run.text
        for node, alias in substitutions:
            text = text.replace(node, alias)
        result.append(replace(run, text=text))
    return result


def explanation_runs(state, start, target, aliases):
    if state.comparison:
        runs = comparison_runs(state)
    else:
        detail = state.explanation
        if state.algorithm == "Bellman-Ford" and state.phase == "Inicialización":
            detail = detail.replace(
                "en orden origen, destino, ID.",
                "por origen y destino, con orden estable entre conexiones paralelas.",
            )
        first, separator, rest = detail.partition(". ")
        runs = [TextRun(first + separator, True, "error" if state.affected else "text")]
        if rest:
            runs.append(TextRun(rest))
    route = route_description(state, start, target)
    route_role = "error" if route.startswith("−∞") else "target"
    runs += [TextRun("\n"), TextRun(route, True, route_role)]
    return alias_runs(runs, aliases)


def text_color(palette, role, background, *, monochrome=False):
    """Keep small emphasized text legible even with a custom accent or theme."""
    color = palette.text if monochrome else getattr(palette, role)
    light, dark = sorted((luminance(color), luminance(background)), reverse=True)
    return color if (light + 0.05) / (dark + 0.05) >= 4.5 else palette.text


def fitted_document(runs, rect, font, palette, background, *, monochrome=False):
    """Fit rich text as one unit; literal node names never become HTML markup."""
    document = QTextDocument()
    document.setDocumentMargin(0)
    option = QTextOption()
    option.setWrapMode(QTextOption.WrapMode.WrapAtWordBoundaryOrAnywhere)
    document.setDefaultTextOption(option)
    document.setTextWidth(rect.width())
    document.setDefaultFont(font)
    cursor = QTextCursor(document)
    for run in runs:
        style = QTextCharFormat()
        style.setFontWeight(QFont.Weight.Bold if run.bold else QFont.Weight.Normal)
        style.setForeground(
            QColor(text_color(palette, run.role, background, monochrome=monochrome))
        )
        cursor.insertText(run.text, style)

    def fits(size):
        candidate = QFont(font)
        candidate.setPixelSize(size)
        document.setDefaultFont(candidate)
        return document.size().height() <= rect.height() and document.idealWidth() <= rect.width()

    size = font.pixelSize()
    if not fits(size):
        low, high = 1, size
        while low < high:
            mid = (low + high + 1) // 2
            if fits(mid):
                low = mid
            else:
                high = mid - 1
        fits(low)
    return document


def draw_document(painter, rect, document):
    painter.save()
    painter.translate(rect.topLeft())
    document.drawContents(painter)
    painter.restore()
