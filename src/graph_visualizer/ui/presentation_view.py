"""A full-screen viewer of the exact exported slides, without changing the workspace."""

from bisect import bisect_left, bisect_right

from PySide6.QtCore import QSignalBlocker, Qt, QTimer
from PySide6.QtGui import QAction, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from graph_visualizer.export.slide_renderer import SlideOptions, SlideRenderer
from graph_visualizer.ui.accessibility import announce


class PresentationView(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.states = owner.states
        self.start, self.target = owner.start, owner.target
        self.index = owner.state_index
        self.bookmarks = owner.bookmarks
        self.event_indices = {state.step: i for i, state in enumerate(self.states)}
        phases, seen = [], set()
        for i, state in enumerate(self.states):
            key = state.iteration, state.phase
            if key not in seen:
                phases.append(i)
                seen.add(key)
        self.phase_indices = tuple(phases)
        self.renderer = SlideRenderer(
            owner.graph.copy(), owner.graph_view.positions(), SlideOptions(**owner.export_options())
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowModality(Qt.WindowModality.WindowModal)
        self.setWindowTitle("Presentación del recorrido")
        self.resize(1280, 800)
        self.timer = QTimer(self)
        self.timer.setInterval(owner.speed.value())
        self.timer.timeout.connect(lambda: self.advance(1))
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        self.canvas = QLabel()
        self.canvas.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.canvas.setMinimumSize(320, 180)
        self.canvas.setAccessibleName("Diapositiva completa del recorrido")
        column.addWidget(self.canvas, 1)
        self.controls = QWidget()
        controls = QGridLayout(self.controls)
        self.mode = QComboBox()
        self.mode.addItems(["Pasos", "Fases", "Marcas"])
        self.mode.setAccessibleName("Avanzar por pasos, fases o marcas")
        self.step = QSpinBox()
        self.step.setRange(0, len(self.states) - 1)
        self.step.setKeyboardTracking(False)
        self.step.setSuffix(f" / {len(self.states) - 1}")
        self.step.setAccessibleName("Paso de la presentación")
        self.previous = QPushButton("Anterior")
        self.next = QPushButton("Siguiente")
        self.play = QPushButton("Reproducir")
        self.mark = QPushButton("Marcar")
        self.mark.setCheckable(True)
        hide = QPushButton("Ocultar controles (H)")
        close = QPushButton("Salir (Esc)")
        self.previous.clicked.connect(lambda: self.advance(-1))
        self.next.clicked.connect(lambda: self.advance(1))
        self.play.clicked.connect(self.toggle_playback)
        self.mark.clicked.connect(self.toggle_mark)
        hide.clicked.connect(self.toggle_controls)
        close.clicked.connect(self.reject)
        for index, widget in enumerate(
            (
                self.mode,
                self.previous,
                self.step,
                self.next,
                self.play,
                self.mark,
                hide,
                close,
            )
        ):
            controls.addWidget(widget, index // 4, index % 4)
        column.addWidget(self.controls)
        self.caption = QLabel()
        self.caption.setWordWrap(True)
        self.caption.setAccessibleName("Estado y controles de la presentación")
        column.addWidget(self.caption)
        self.mode.currentIndexChanged.connect(self.mode_changed)
        self.step.valueChanged.connect(self.show_state)
        for key, callback in (
            ("Right", lambda: self.advance(1)),
            ("Left", lambda: self.advance(-1)),
            ("Home", lambda: self.show_state(self.indices()[0] if self.indices() else self.index)),
            ("End", lambda: self.show_state(self.indices()[-1] if self.indices() else self.index)),
            ("Space", self.toggle_playback),
            ("M", self.toggle_mark),
            ("H", self.toggle_controls),
            ("F11", self.reject),
        ):
            action = QAction(self)
            action.setShortcut(key)
            action.triggered.connect(callback)
            self.addAction(action)
        self.closed = False
        self.finished.connect(self.cleanup)
        try:
            self.show_state(self.index)
        except Exception:
            self.renderer.close()
            raise

    def indices(self):
        if self.mode.currentIndex() == 0:
            return range(len(self.states))
        if self.mode.currentIndex() == 2:
            return tuple(
                sorted(
                    self.event_indices[event]
                    for event in self.bookmarks
                    if event in self.event_indices
                )
            )
        return self.phase_indices

    def advance(self, direction):
        indices = self.indices()
        position = (
            bisect_right(indices, self.index)
            if direction > 0
            else bisect_left(indices, self.index) - 1
        )
        if 0 <= position < len(indices):
            self.show_state(indices[position])
        else:
            self.stop_playback()

    def mode_changed(self):
        self.stop_playback()
        self.refresh_controls()

    def show_state(self, index):
        if not 0 <= index < len(self.states):
            return
        self.index = index
        self.image = self.renderer.image([(index, 0)], self.states, self.start, self.target)
        self.refresh_image()
        with QSignalBlocker(self.step):
            self.step.setValue(index)
        state = self.states[index]
        self.canvas.setAccessibleDescription(
            self.renderer.explanation(state, self.start, self.target)
        )
        self.refresh_controls()
        announce(
            self.canvas, f"Paso {index}. {state.algorithm}. {state.phase}. {state.explanation}"
        )

    def refresh_controls(self):
        indices = self.indices()
        self.previous.setEnabled(bool(indices) and self.index > indices[0])
        self.next.setEnabled(bool(indices) and self.index < indices[-1])
        if not self.next.isEnabled():
            self.stop_playback()
        self.play.setEnabled(bool(indices))
        marked = self.states[self.index].step in self.bookmarks
        self.mark.setChecked(marked)
        self.mark.setText("Quitar marca" if marked else "Marcar")
        state = self.states[self.index]
        self.caption.setText(
            f"{state.algorithm} · {state.phase} · Evento {state.step} · "
            + ("No hay pasos marcados; pulsa M para marcar este paso. " if not indices else "")
            + "← / →: avanzar · Espacio: reproducir · M: marcar · H: controles · Esc: salir"
        )

    def toggle_mark(self):
        event = self.states[self.index].step
        if event in self.bookmarks:
            self.bookmarks.remove(event)
        else:
            self.bookmarks.add(event)
        self.refresh_controls()
        announce(self.caption, "Marca quitada." if event not in self.bookmarks else "Paso marcado.")

    def toggle_controls(self):
        visible = not self.controls.isVisible()
        self.controls.setVisible(visible)
        self.caption.setVisible(visible)

    def toggle_playback(self):
        if self.timer.isActive():
            self.stop_playback()
        elif self.indices():
            if not self.next.isEnabled():
                self.show_state(self.indices()[0])
            self.timer.start()
            self.play.setText("Pausar")

    def stop_playback(self):
        self.timer.stop()
        self.play.setText("Reproducir")

    def refresh_image(self):
        if hasattr(self, "image"):
            self.canvas.setPixmap(
                QPixmap.fromImage(self.image).scaled(
                    self.canvas.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.refresh_image()

    def cleanup(self):
        if self.closed:
            return
        self.closed = True
        self.stop_playback()
        self.renderer.close()
        self.owner.refresh_bookmarks()
        self.owner.refresh_export_preview()
