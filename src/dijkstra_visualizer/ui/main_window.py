from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from dijkstra_visualizer.core.dijkstra import dijkstra_steps, reconstruct_path
from dijkstra_visualizer.core.models import DijkstraState
from dijkstra_visualizer.export.image_exporter import ExportKind, export_graph
from dijkstra_visualizer.io.graph_io import load_graph
from dijkstra_visualizer.io.layout_io import load_layout, save_layout
from dijkstra_visualizer.paths import DATA_DIR, OUTPUT_DIR
from dijkstra_visualizer.ui.graph_view import GraphView
from dijkstra_visualizer.ui.node_item import format_distance


class MainWindow(QMainWindow):
    def __init__(self, data_dir: Path = DATA_DIR, output_dir: Path = OUTPUT_DIR):
        super().__init__()
        self.data_dir, self.output_dir = data_dir, output_dir
        self.graph = load_graph(data_dir / "nodes.csv", data_dir / "edges.csv")
        positions = load_layout(data_dir / "layout.json", self.graph)
        self.states: list[DijkstraState] = []
        self.state_index = 0
        self.layout_dirty = False
        self.setWindowTitle("Dijkstra Visualizer · Fundamentals of AI")
        self.resize(1280, 800)
        self.setMinimumSize(900, 620)
        self.graph_view = GraphView(self.graph, positions)
        self.graph_view.layout_changed.connect(self._save_layout)
        self._build_ui()
        self._build_menu()
        self._apply_style()
        self.reset()
        QTimer.singleShot(0, self.graph_view.fit_graph)

    @property
    def start(self) -> int:
        return self.start_combo.currentData()

    @property
    def target(self) -> int:
        return self.target_combo.currentData()

    def _build_ui(self) -> None:
        central = QWidget()
        row = QHBoxLayout(central)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(280)
        controls = QVBoxLayout(sidebar)
        controls.setContentsMargins(22, 22, 22, 22)
        controls.setSpacing(12)
        title = QLabel("Dijkstra")
        title.setObjectName("title")
        controls.addWidget(title)
        controls.addWidget(QLabel("Fundamentals of AI\nShortest paths, one step at a time."))
        self.mode_label = QLabel()
        self.mode_label.setObjectName("mode")
        controls.addWidget(self.mode_label)
        self.start_combo, self.target_combo = QComboBox(), QComboBox()
        for node in sorted(self.graph):
            self.start_combo.addItem(f"Node {node}", node)
            self.target_combo.addItem(f"Node {node}", node)
        self.target_combo.setCurrentIndex(self.target_combo.count() - 1)
        for label, combo in (("Start node", self.start_combo), ("Target node", self.target_combo)):
            controls.addWidget(QLabel(label))
            controls.addWidget(combo)
            combo.currentIndexChanged.connect(self._selection_changed)
        self.run_button = QPushButton("Initialize Dijkstra")
        self.run_button.setObjectName("primary")
        self.run_button.clicked.connect(self.initialize)
        controls.addWidget(self.run_button)
        navigation = QHBoxLayout()
        self.previous_button, self.next_button = QPushButton("← Previous"), QPushButton("Next →")
        self.previous_button.clicked.connect(lambda: self.show_state(self.state_index - 1))
        self.next_button.clicked.connect(lambda: self.show_state(self.state_index + 1))
        navigation.addWidget(self.previous_button)
        navigation.addWidget(self.next_button)
        controls.addLayout(navigation)
        self.reset_button = QPushButton("Reset to Edit mode")
        self.reset_button.clicked.connect(self.reset)
        controls.addWidget(self.reset_button)
        self.step_label = QLabel()
        self.step_label.setObjectName("step")
        controls.addWidget(self.step_label)
        self.detail_label = QLabel()
        self.detail_label.setWordWrap(True)
        self.detail_label.setMinimumHeight(90)
        controls.addWidget(self.detail_label)
        controls.addStretch()
        legend = QLabel(
            '<span style="color:#64748b">●</span> Unreached &nbsp; '
            '<span style="color:#b48412">●</span> Tentative<br>'
            '<span style="color:#329758">●</span> Visited &nbsp; '
            '<span style="color:#18794e">●</span> Current<br>'
            '<span style="color:#dc3545">○</span> Target border &nbsp; '
            '<span style="color:#087e8b">━</span> Final path<br><br>'
            "[distance, predecessor]<br>Bold label = improved this step"
        )
        controls.addWidget(legend)
        graph_panel = QWidget()
        graph_column = QVBoxLayout(graph_panel)
        graph_column.setContentsMargins(0, 0, 0, 0)
        toolbar = QHBoxLayout()
        hint = QLabel("  Drag nodes to arrange · Drag background to pan · Scroll to zoom")
        hint.setObjectName("hint")
        toolbar.addWidget(hint)
        toolbar.addStretch()
        fit_button = QPushButton("Fit graph")
        fit_button.clicked.connect(self.graph_view.fit_graph)
        toolbar.addWidget(fit_button)
        toolbar.setContentsMargins(8, 10, 16, 10)
        graph_column.addLayout(toolbar)
        graph_column.addWidget(self.graph_view)
        row.addWidget(sidebar)
        row.addWidget(graph_panel, 1)
        self.setCentralWidget(central)
        self.statusBar().showMessage(
            f"Loaded {len(self.graph)} nodes and {self.graph.number_of_edges()} edges"
        )

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        self.export_actions: list[QAction] = []
        for label, kind in (
            ("Export current phase", "current"),
            ("Export all phases individually", "all"),
            ("Export combined image", "combined"),
            ("Export final shortest path", "final"),
        ):
            action = file_menu.addAction(label)
            action.setToolTip("Initialize Dijkstra, then export to output/ automatically")
            action.triggered.connect(lambda checked=False, kind=kind: self.export(kind))
            self.export_actions.append(action)
        file_menu.addSeparator()
        open_output = file_menu.addAction("Open output folder")
        open_output.triggered.connect(self.open_output_folder)
        file_menu.addSeparator()
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        view_menu = self.menuBar().addMenu("&View")
        fit = view_menu.addAction("Fit graph")
        fit.setShortcut("Ctrl+0")
        fit.triggered.connect(self.graph_view.fit_graph)

    def _apply_style(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget { background: #f8fafc; color: #172b4d; }
            QWidget { font-family: 'Sans Serif'; font-size: 13px; }
            QFrame#sidebar { background: #ffffff; border-right: 1px solid #dce3ed; }
            QFrame#sidebar QLabel { background: transparent; }
            QLabel#title { font-size: 30px; font-weight: 700; }
            QLabel#mode { color: #087e8b; font-weight: 600; padding: 8px 0; }
            QLabel#step { font-size: 17px; font-weight: 600; padding-top: 10px; }
            QLabel#hint { color: #64748b; font-size: 12px; }
            QPushButton, QComboBox {
                background: #ffffff; border: 1px solid #cbd5e1;
                border-radius: 6px; padding: 8px 10px;
            }
            QPushButton:hover { background: #edf3f8; border-color: #94a3b8; }
            QPushButton#primary { background: #0f766e; color: white; border-color: #0f766e; }
            QPushButton#primary:hover { background: #115e59; }
            QPushButton:disabled, QPushButton#primary:disabled, QComboBox:disabled {
                background: #f1f5f9; color: #94a3b8; border-color: #e2e8f0;
            }
            QComboBox QAbstractItemView { selection-background-color: #ccfbf1; }
            QStatusBar { border-top: 1px solid #dce3ed; color: #526179; }
            QMenu { background: white; }
            QMenu::item:selected { background: #ccfbf1; }
        """)

    def _selection_changed(self) -> None:
        if not self.states:
            self.graph_view.apply_state(None, self.start, self.target)

    def initialize(self) -> None:
        try:
            self.states = dijkstra_steps(self.graph, self.start, self.target)
        except ValueError as error:
            QMessageBox.warning(self, "Cannot initialize Dijkstra", str(error))
            return
        self.graph_view.set_editable(False)
        self.start_combo.setEnabled(False)
        self.target_combo.setEnabled(False)
        self.run_button.setEnabled(False)
        self.reset_button.setEnabled(True)
        self.mode_label.setText("ALGORITHM MODE")
        for action in self.export_actions:
            action.setEnabled(True)
        self.show_state(0)

    def show_state(self, index: int) -> None:
        if not self.states or not 0 <= index < len(self.states):
            return
        self.state_index = index
        state = self.states[index]
        final = index == len(self.states) - 1
        self.graph_view.apply_state(state, self.start, self.target, final)
        self.previous_button.setEnabled(index > 0)
        self.next_button.setEnabled(not final)
        self.step_label.setText(f"Step {index} / {len(self.states) - 1}")
        if final:
            path = reconstruct_path(state, self.start, self.target)
            self.detail_label.setText(
                f"Target settled · distance {format_distance(state.distances[self.target])}\n"
                + " → ".join(map(str, path))
                if path
                else f"Target {self.target} is unreachable from node {self.start}.\n"
                "No reachable unvisited nodes remain."
            )
        elif state.current_node is None:
            self.detail_label.setText(
                "Current node: —\nStart distance is 0; all others are ∞.\n"
                "Next selects the smallest tentative distance."
            )
        else:
            updated = ", ".join(map(str, sorted(state.updated_nodes))) or "none"
            self.detail_label.setText(
                f"Current node: {state.current_node}\n"
                f"Settled nodes: {len(state.visited)}\nImproved labels: {updated}"
            )

    def reset(self) -> None:
        for action in self.export_actions:
            action.setEnabled(False)
        self.states = []
        self.state_index = 0
        self.graph_view.set_editable(True)
        self.graph_view.apply_state(None, self.start, self.target)
        self.start_combo.setEnabled(True)
        self.target_combo.setEnabled(True)
        self.run_button.setEnabled(True)
        self.previous_button.setEnabled(False)
        self.next_button.setEnabled(False)
        self.reset_button.setEnabled(False)
        self.mode_label.setText("EDIT MODE")
        self.step_label.setText("Ready to explore")
        self.detail_label.setText(
            "Arrange the graph, choose a start and target, then initialize.\n"
            "Positions are saved when you finish dragging."
        )

    def export(self, kind: ExportKind) -> None:
        self.statusBar().showMessage("Rendering export…")
        self.statusBar().repaint()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            destination = export_graph(
                self.graph,
                self.graph_view.positions(),
                self.states,
                self.start,
                self.target,
                self.state_index,
                kind,
                self.output_dir,
            )
        except (OSError, ValueError) as error:
            self.statusBar().showMessage("Export failed", 8000)
            QMessageBox.warning(self, "Export failed", str(error))
        else:
            self.statusBar().showMessage(f"Export completed · {destination}", 15000)
        finally:
            QApplication.restoreOverrideCursor()

    def open_output_folder(self) -> None:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_dir.resolve()))):
                raise OSError(f"Could not open the file manager. Output folder: {self.output_dir}")
        except OSError as error:
            QMessageBox.warning(self, "Cannot open output folder", str(error))

    def _save_layout(self) -> None:
        self.layout_dirty = True
        try:
            save_layout(self.data_dir / "layout.json", self.graph_view.positions())
        except (OSError, ValueError) as error:
            QMessageBox.warning(self, "Layout could not be saved", str(error))
        else:
            self.layout_dirty = False
            self.statusBar().showMessage("Layout saved", 4000)

    def closeEvent(self, event) -> None:
        if self.layout_dirty:
            self._save_layout()
            if self.layout_dirty:
                answer = QMessageBox.question(
                    self,
                    "Unsaved layout",
                    "The layout could not be saved. Close and discard the unsaved positions?",
                    QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                    QMessageBox.StandardButton.Cancel,
                )
                if answer != QMessageBox.StandardButton.Discard:
                    event.ignore()
                    return
        super().closeEvent(event)
