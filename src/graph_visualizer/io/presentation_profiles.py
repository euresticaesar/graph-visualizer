"""Portable presentation preferences, independent of graph topology and execution."""

import json
from pathlib import Path

from graph_visualizer.io.files import atomic_write_files
from graph_visualizer.io.preferences import DEFAULTS, validated_preferences

PROFILE_KEYS = tuple(
    key for key in DEFAULTS if key not in {"window_size", "workspace_sizes", "results_sizes"}
)


def profile_document(name, values):
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 80:
        raise ValueError("El perfil necesita un nombre de 1 a 80 caracteres.")
    clean = validated_preferences(values)
    return {
        "version": 1,
        "kind": "graph-visualizer-presentation",
        "name": name.strip(),
        "preferences": {key: clean[key] for key in PROFILE_KEYS},
    }


def parse_profile(document):
    if (
        not isinstance(document, dict)
        or type(document.get("version")) is not int
        or document["version"] != 1
        or document.get("kind") != "graph-visualizer-presentation"
        or not isinstance(document.get("preferences"), dict)
    ):
        raise ValueError("El archivo no es un perfil de presentación compatible.")
    values = document["preferences"]
    clean = validated_preferences(values)
    for key, value in values.items():
        valid_type = key in clean and (
            type(value) in (int, float)
            if type(clean[key]) is float
            else type(value) is type(clean[key])
        )
        if key not in PROFILE_KEYS or not valid_type or value != clean[key]:
            raise ValueError(f"Ajuste de presentación no válido: {key}.")
    return profile_document(document.get("name"), clean)


def read_profile(path: Path):
    try:
        return parse_profile(json.loads(path.read_text(encoding="utf-8")))
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"JSON de perfil no válido: {error}") from error


def write_profile(path: Path, document):
    clean = parse_profile(document)
    atomic_write_files({path: json.dumps(clean, ensure_ascii=False, indent=2) + "\n"})
