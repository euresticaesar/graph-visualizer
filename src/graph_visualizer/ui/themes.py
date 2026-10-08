"""Shared semantic colors for widgets, the graph and exported documents."""

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Palette:
    canvas: str = "#f8fafc"
    surface: str = "#ffffff"
    inset: str = "#edf2f7"
    text: str = "#172b4d"
    muted: str = "#526179"
    border: str = "#cbd5e1"
    header: str = "#e2e8f0"
    accent: str = "#087e8b"
    accent_text: str = "#ffffff"
    selection: str = "#d6eee8"
    visited: str = "#a7e3bd"
    tentative: str = "#fef3c7"
    current: str = "#18794e"
    current_text: str = "#ffffff"
    unreached: str = "#e2e8f0"
    target: str = "#2563eb"
    error: str = "#b42318"
    error_fill: str = "#fecaca"
    comparison: str = "#a66300"
    comparison_fill: str = "#fed7aa"
    improvement: str = "#fef08a"
    k_fill: str = "#bbf7d0"
    k_border: str = "#15803d"
    active: str = "#7c3aed"
    edge: str = "#64748b"


THEME_NAMES = {
    "light": "Claro",
    "dark": "Oscuro",
    "paper": "Sepia",
    "contrast": "Alto contraste",
    "print": "Impresión",
}
PALETTES = {
    "light": Palette(),
    "dark": Palette(
        canvas="#101820",
        surface="#192530",
        inset="#223340",
        text="#edf3f8",
        muted="#b6c7d5",
        border="#526574",
        header="#293c4a",
        accent="#6dd8d0",
        accent_text="#102a2d",
        selection="#21494c",
        visited="#244d39",
        tentative="#514329",
        current="#85e3ac",
        current_text="#10271b",
        unreached="#293c4a",
        target="#90baff",
        error="#ffb4ab",
        error_fill="#633733",
        comparison="#ffcc80",
        comparison_fill="#594225",
        improvement="#514c20",
        k_fill="#244d39",
        k_border="#85e3ac",
        active="#c4a7ff",
        edge="#8da4b6",
    ),
    "paper": Palette(
        canvas="#faf5e9",
        surface="#fffaf0",
        inset="#f0e8d7",
        text="#382d22",
        muted="#665748",
        border="#c3b59c",
        header="#eadeca",
        accent="#805224",
        selection="#ebdcc7",
        visited="#c8dec0",
        tentative="#f3dfa6",
        current="#385e3b",
        unreached="#eadeca",
        target="#365da4",
        edge="#8b7963",
    ),
    "contrast": Palette(
        canvas="#ffffff",
        surface="#ffffff",
        inset="#f0f0f0",
        text="#000000",
        muted="#303030",
        border="#333333",
        header="#e5e5e5",
        accent="#005a70",
        selection="#d5eff5",
        visited="#bce5cf",
        tentative="#ffe0a0",
        current="#004d35",
        unreached="#e5e5e5",
        target="#003cba",
        error="#a00000",
        comparison="#8a4700",
        active="#5200a8",
        edge="#383838",
    ),
    "print": Palette(
        canvas="#ffffff",
        surface="#ffffff",
        inset="#f4f4f4",
        text="#101010",
        muted="#404040",
        border="#909090",
        header="#eeeeee",
        accent="#00556b",
        selection="#e0edf0",
        edge="#555555",
    ),
}


def luminance(color):
    channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))


def foreground(color):
    """Choose the more legible text color for a user-selected accent."""
    return "#000000" if luminance(color) > 0.179 else "#ffffff"


def palette_for(name="light", accent=None):
    palette = PALETTES.get(name, PALETTES["light"])
    if accent:
        return replace(palette, accent=accent, accent_text=foreground(accent))
    return palette


def matrix_colors(state, row, col, palette=None):
    p = palette or PALETTES["light"]
    green = state.k is not None and (row == state.k or col == state.k)
    affected = (row, col) in state.affected
    background = (
        p.error_fill
        if affected
        else p.improvement
        if (row, col) in state.changed
        else p.k_fill
        if green
        else p.surface
    )
    return background, green, state.cell == (row, col)


def row_color(state, kind, values, palette=None):
    p = palette or PALETTES["light"]
    if kind == "arcs":
        return (
            p.comparison_fill
            if tuple(values[:2]) + (int(values[2]),) == state.current_edge
            else p.surface
        )
    node = values[0]
    if node in state.affected:
        return p.error_fill
    if kind == "astar" and node == state.current_node:
        return p.comparison_fill
    return p.improvement if node in state.updated_nodes else p.surface
