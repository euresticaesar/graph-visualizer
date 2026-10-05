# Dijkstra Visualizer

An educational desktop application for **Fundamentals of AI**. Explore Dijkstra's
shortest-path algorithm on a weighted, undirected graph, one iteration at a time.
The included 12-node example has competing routes and is ready to run.

Built with Python 3.12+, uv, PySide6 / Qt 6, and NetworkX. Tests use pytest and Qt's
own interaction tools; Ruff handles linting and formatting.

## Run

From this checkout, with uv installed:

```sh
uv sync
uv run dijkstra-visualizer
```

`uv run python -m dijkstra_visualizer` also works. A graphical desktop is required
for normal use. From another directory, point uv at the checkout:

```sh
uv run --project /path/to/dijkstra-visualizer dijkstra-visualizer
```

Data and output paths are resolved relative to the source checkout, independent
of the shell's current directory. Keep the `data/` directory with the project;
a standalone packaged installer is not provided.

## Use

The interface, export captions, errors, and source comments are in Mexican Spanish.
Code identifiers and CSV headers remain in English. All controls are in the main
window; there is no menu bar.

1. In **MODO EDICIÓN**, drag nodes to arrange the graph. Connections follow
   immediately; positions are saved when you release the mouse.
2. In **Recorrido**, select **Nodo de inicio** and **Nodo de destino**, then click
   **Iniciar Dijkstra**. Use **Siguiente** and **Anterior** to browse stored phases.
   **Volver a editar** clears the run and keeps the graph and edit history.
3. In **Editar grafo**, use **ID nuevo** to add a node or rename the selected one.
   **Eliminar nodo seleccionado** also removes its connections. At least one node
   must remain. Clicking a node on the canvas selects it in the editor.
4. Choose **Desde**, **Hasta**, and a positive **Peso**, then **Guardar conexión**
   to create an edge or change its weight. Use a decimal point, for example `2.5`.
   **Eliminar conexión** removes the selected edge.
5. Export with the buttons below the graph. **Abrir carpeta** opens the output
   directory; **Salir** closes the application.

Graph edits save automatically. **↶ / ↷**, beside **Ajustar vista**, undo or redo
node movements, additions, deletions, ID changes, edge changes, and start/target
selections. A drag counts as one action. Up to 100 actions are kept for the current
session; a new edit after undo clears the redo branch. Algorithm mode locks edits
and undo/redo. Undoing a data edit also updates the saved files.

| Shortcut / gesture | Action |
| --- | --- |
| `Ctrl+Z` / `Ctrl+Y` (also `Ctrl+Shift+Z`) | Undo / redo graph edits |
| `Ctrl+0` | Fit the graph |
| `Ctrl+Q` | Exit |
| Background drag / mouse wheel | Pan / zoom |

Every node shows `[distancia, predecesor]`, keeping the classroom symbols `∞` and
`null`. Gray means unreached, yellow means tentative, and green means visited.
The current node has a dark fill and dashed ring. Captions identify the start and
node state; the target keeps its red border. Bold labels indicate improvements in
the current step. Teal edges highlight the final path. The legend uses two columns.

## How the algorithm works

Dijkstra is implemented by this project in `core/dijkstra.py`; application logic
does **not** call NetworkX's shortest-path algorithms. NetworkX stores the graph
and serves as an independent reference in tests.

Step 0 sets the start distance to zero and all others to infinity. Each subsequent
step selects the smallest tentative distance, permanently visits that node, and
relaxes its unvisited neighbors. Ties are resolved by node ID. Execution stops
when the target is settled, before expanding it, or when the reachable nodes are
exhausted. Labels on unvisited nodes may therefore remain tentative at completion.

Snapshots use immutable mappings and sets, so navigation never reruns the
algorithm or changes earlier phases. The final path is reconstructed from the
predecessors. Unreachable targets are reported explicitly. Choosing the same start
and target is supported and produces a zero-distance path.

The default run, from 1 to 12, has distance **16** and path
**1 → 5 → 6 → 7 → 11 → 12**.

## Data files

| File | Stores | Format |
| --- | --- | --- |
| `data/nodes.csv` | Vertices, including isolated nodes | `id` header, one positive integer ID per row |
| `data/edges.csv` | Weighted undirected edges | `source,target,weight` header, positive finite numeric weights |
| `data/layout.json` | Visual positions only | Node ID strings mapped to `{"x": 220.0, "y": 160.0}` |

Example CSV contents:

```csv
id
1
2
3
```

```csv
source,target,weight
1,2,7
2,3,2.5
```

An edge is listed only once: `1,2,7` also connects 2 to 1. Duplicate nodes or edges,
self-loops, unknown endpoints, malformed records, and invalid weights are rejected
with understandable errors. Invalid layouts are reported; absent layout files or
missing positions receive deterministic fallback coordinates without moving nodes
that already have saved positions. Layout saves use an atomic file replacement. Topology edits stage both CSV files
and the layout before replacing them. Write failures trigger a rollback; if the
rollback itself fails, recovery copies are retained and their paths are reported.

Edit the CSV files while the application is closed and restart to load changes.
Start/target selections and algorithm state are never written into the data files.


## Exports

After initialization, the export buttons below the graph provide:

- **Paso actual** → `current_step_05.png`, for example.
- **Pasos separados** → `steps/step_00.png`, `step_01.png`, etc.
- **Imagen conjunta** → `all_steps.png`, a grid with up to three columns.
- **Ruta final** → `final_path.png`, even while viewing an earlier phase.

Each action creates a new timestamped directory inside `output/`, including
microseconds to avoid overwrites. No file or directory prompt is required. A
persistent, non-blocking success banner shows the image count and destination,
with a button to open that export folder. There is also a status-bar confirmation
and a desktop attention request. Dismiss the banner with **×**. The sidebar's
**Abrir carpeta** opens the main output directory.

Exports render a separate Qt scene using the same graph coordinates, labels, and
colors. They include step information, never application controls, and leave the
live view untouched. Individual images are 1600 × 1100 pixels; combined images use
1200 × 860 cells with shared graph extents. Resolution does not depend on window
size. Very large combined images are rejected with a suggestion to export separate
phases instead. Exports are synchronous and may briefly pause the UI on large graphs.
Generated output is ignored by Git.

## Project structure

```text
src/dijkstra_visualizer/
├── core/       # Graph validation, immutable states, manual Dijkstra
├── io/         # CSV loading and layout persistence
├── ui/         # Qt window, graph editor, scene, node and edge items
├── export/     # Scene rendering and combined images
└── paths.py    # Source-checkout data and output locations
data/           # Demonstration graph and saved layout
tests/          # Algorithm, IO, Qt interaction, and export checks
output/         # Generated images (ignored)
```

The core has no Qt dependency. The UI consumes precomputed states, and persistence
contains no algorithm logic. The renderer uses `QGraphicsScene` / `QGraphicsView`,
with movable node items and connected edge items.

## Development checks

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

To apply formatting, use `uv run ruff format .`. Tests cover graph validation,
shortest paths, predecessors, disconnected graphs, snapshot immutability,
NetworkX reference comparisons, graph editing, persisted undo/redo, write-failure
recovery, mouse interaction, layout restoration, and export notifications. Qt tests
run offscreen and use temporary data/output folders; they do not alter your graph.

## Linux desktop messages

`This plugin supports grabbing the mouse only for popup windows` originates in
[Qt's Wayland platform integration](https://github.com/qt/qtbase/blob/dev/src/plugins/platforms/wayland/qwaylandwindow.cpp).
If input is affected and XWayland is installed, an optional per-launch workaround is:

```sh
QT_QPA_PLATFORM=xcb uv run dijkstra-visualizer
```

This uses Qt's X11 backend without changing desktop settings. Native Wayland remains
the default when selected by your environment. See [Qt's platform documentation](https://doc.qt.io/qt-6/qguiapplication.html#platformName-prop).

`WARNING: Glycin running without sandbox` comes from the desktop's
[Glycin image-loading library](https://github.com/GNOME/glycin#sandboxing-and-inner-workings).
The application does not use Glycin directly; desktop theme or file-manager image
loading is a possible source. The warning was not reproduced during application
startup and export checks. It is not evidence of a failed Dijkstra calculation or
PNG export. No sandbox protections are disabled and no warnings are suppressed.

Possible future additions include automatic playback and a packaged desktop installer.
