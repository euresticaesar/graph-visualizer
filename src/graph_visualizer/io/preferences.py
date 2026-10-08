"""Validated, local UI preferences, separate from graph and preset data."""

import json
import re
from pathlib import Path

from graph_visualizer.io.files import atomic_write_files

DEFAULTS = {
    "theme": "light",
    "accent": "",
    "ui_layout": "classic",
    "ui_font_size": 13,
    "graph_font_scale": 1.0,
    "state_labels": True,
    "edge_ids": False,
    "export_theme": "light",
    "export_layout": "balanced",
    "export_composition": "auto",
    "export_graph_fraction": 0.48,
    "export_dim_unrelated": False,
    "export_focus": False,
    "export_resolution": 1920,
    "export_font_scale": 1.0,
    "export_group": 4,
    "export_legend": True,
    "export_explanation": True,
    "export_title": "",
    "export_format": "png",
    "export_style": 0,
    "export_detail": 0,
    "preview_before_export": True,
    "window_size": [1380, 940],
    "workspace_sizes": [365, 1015],
    "results_sizes": [],
}
CHOICES = {
    "theme": {"light", "dark", "paper", "contrast", "print", "colorblind"},
    "export_theme": {"light", "dark", "paper", "contrast", "print", "colorblind", "app"},
    "ui_layout": {"classic", "right", "bottom", "focus"},
    "export_layout": {"balanced", "graph", "tables"},
    "export_composition": {"auto", "side", "top"},
    "export_resolution": {1920, 2560, 3840},
    "export_group": {2, 4},
    "export_format": {"png", "pdf", "svg"},
    "export_style": {0, 1},
    "export_detail": {0, 1, 2},
}


def validated_preferences(data):
    result = DEFAULTS.copy()
    if not isinstance(data, dict):
        return result
    for key, value in data.items():
        if key not in DEFAULTS:
            continue
        if key in CHOICES:
            if type(value) is type(DEFAULTS[key]) and value in CHOICES[key]:
                result[key] = value
        elif type(DEFAULTS[key]) is bool:
            if type(value) is bool:
                result[key] = value
        elif key == "accent":
            if isinstance(value, str) and (not value or re.fullmatch(r"#[0-9a-fA-F]{6}", value)):
                result[key] = value
        elif key == "export_title":
            if isinstance(value, str):
                result[key] = value[:200]
        elif key == "ui_font_size":
            if type(value) is int and 11 <= value <= 18:
                result[key] = value
        elif key in {"graph_font_scale", "export_font_scale"}:
            if type(value) in (int, float) and 0.8 <= value <= 1.5:
                result[key] = float(value)
        elif key == "export_graph_fraction":
            if type(value) in (int, float) and 0.2 <= value <= 0.65:
                result[key] = float(value)
        elif key in {"window_size", "workspace_sizes", "results_sizes"}:
            if (
                isinstance(value, list)
                and len(value) == 2
                and all(type(v) is int and 0 <= v <= 10000 for v in value)
            ):
                if key != "window_size" or (value[0] >= 900 and value[1] >= 640):
                    result[key] = value
    return result


def load_preferences(path: Path):
    try:
        return validated_preferences(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError, UnicodeError):
        return DEFAULTS.copy()


def save_preferences(path: Path, values):
    atomic_write_files(
        {path: json.dumps(validated_preferences(values), ensure_ascii=False, indent=2) + "\n"}
    )
