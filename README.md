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

1. In **Edit mode**, drag nodes to arrange the graph. Edges and weights follow
   immediately; coordinates are saved after releasing the mouse.
2. Choose a **Start node** and **Target node**, then click **Initialize Dijkstra**.
3. Use **Next** and **Previous** to navigate the stored phases. Nodes are locked
   during Algorithm mode. **Reset to Edit mode** clears the run and keeps the layout.
4. Drag the background to pan, scroll to zoom, and use **Fit graph** or `Ctrl+0`
   to frame the graph.
5. Use the **File** menu to export images or open the output folder.

Every node shows `[distance, predecessor]`, using `∞` and `null` where appropriate.
Gray means unreached, yellow means tentative, and green means visited. The current
node has a dark fill and dashed outer ring. Captions identify states and the start;
the target keeps its red border throughout. Bold labels indicate improvements in
the current iteration. Teal edges highlight the final shortest path.

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
that already have saved positions. Layout saves use an atomic file replacement.

Edit the CSV files while the application is closed and restart to load changes.
Start/target selections and algorithm state are never written into the data files.
Graph topology editing in the GUI is outside this version's scope.

## Exports

After initialization, the **File** menu provides:

- **Export current phase** → `current_step_05.png`, for example.
- **Export all phases individually** → `steps/step_00.png`, `step_01.png`, etc.
- **Export combined image** → `all_steps.png`, a grid with up to three columns.
- **Export final shortest path** → `final_path.png`, even while viewing an earlier phase.

Each action creates a new timestamped directory inside `output/`, including
microseconds to avoid overwrites. No file or directory prompt is required. A
non-blocking status-bar message shows the destination; **Open output folder**
opens it in the system file manager.

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
├── ui/         # Qt window, graph scene, node and edge items
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
NetworkX reference comparisons, mouse interaction, layout restoration, and all
export workflows. Qt tests run offscreen by default and use temporary data/output
folders; they do not alter the example graph.

Possible future additions include topology editing, automatic playback, and a
packaged desktop installer.
