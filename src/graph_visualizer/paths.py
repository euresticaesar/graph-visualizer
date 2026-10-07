import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
# A source checkout keeps its existing working CSVs. Installed wheels use user-local data.
DEFAULT_DATA = (
    PROJECT_ROOT / "data"
    if (PROJECT_ROOT / "pyproject.toml").is_file()
    else Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    / "graph-visualizer"
)
DATA_DIR = Path(os.environ.get("GRAPH_VISUALIZER_DATA_DIR", DEFAULT_DATA)).expanduser()
DEFAULT_OUTPUT = (
    PROJECT_ROOT / "output" if (PROJECT_ROOT / "pyproject.toml").is_file() else DATA_DIR / "output"
)
OUTPUT_DIR = Path(os.environ.get("GRAPH_VISUALIZER_OUTPUT_DIR", DEFAULT_OUTPUT)).expanduser()
