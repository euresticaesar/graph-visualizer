import pytest
from PySide6.QtCore import QSize
from PySide6.QtPdf import QPdfDocument
from PySide6.QtWidgets import QDialog

from graph_visualizer.core.bellman_ford import bellman_ford_steps
from graph_visualizer.export.image_exporter import (
    export_frames,
    export_graph,
    render_state,
)


@pytest.mark.parametrize("kind", ["current", "all", "combined", "final"])
def test_pdf_pages_and_preview(window, kind):
    window.detail_checkbox.setChecked(False)
    window.initialize()
    args = (
        window.graph,
        window.graph_view.positions(),
        window.states,
        window.start,
        window.target,
        0,
        kind,
    )
    frames = [image for image, *_ in export_frames(*args) if image is not None]
    path = export_graph(*args, window.output_dir, output_format="pdf")
    document = QPdfDocument()
    assert document.load(str(path)) == QPdfDocument.Error.None_
    assert document.pageCount() == len(frames)
    assert document.pagePointSize(0).width() / document.pagePointSize(0).height() == 16 / 9
    assert not document.render(0, QSize(1920, 1080)).isNull()
    assert all(image.width() / image.height() == 16 / 9 for image in frames)
    assert all(image.width() in {1920, 3840} for image in frames)
    assert frames[0].width() == (3840 if kind == "combined" else 1920)
    assert not list(path.parent.glob("*.png"))
    document.close()


def test_table_blocks_preserve_arcs(window):
    from graph_visualizer.core.graph import ordered_arcs
    from graph_visualizer.export.slide_renderer import SlideOptions, SlideRenderer

    states = bellman_ford_steps(window.graph, window.start)
    state = states[0]
    renderer = SlideRenderer(window.graph, window.graph_view.positions(), SlideOptions())
    try:
        plans = renderer.plan(state.algorithm)
        assert len(plans) == 1
        arcs = tuple(
            entry
            for block, *_ in plans[0].blocks
            if block.kind == "arcs"
            for entry in block.entries
        )
        assert arcs == ordered_arcs(window.graph)
    finally:
        renderer.close()
    image = render_state(
        window.graph,
        window.graph_view.positions(),
        state,
        window.start,
        window.target,
        0,
        len(states),
    )
    assert image.size() == QSize(1920, 1080)


def test_preview_does_not_export_or_change_navigation(window):
    window.initialize()
    index = window.state_index
    positions = window.graph_view.positions()
    window.show_export_sample()
    dialogs = window.findChildren(QDialog)
    assert any(dialog.windowTitle() == "Vista previa de exportación" for dialog in dialogs)
    assert window.state_index == index
    assert window.graph_view.positions() == positions
    assert not window.output_dir.exists()
    for dialog in dialogs:
        dialog.close()


def test_pdf_ui_and_cancelled_export(window):
    from conftest import wait_idle

    from graph_visualizer.export.image_exporter import export_job

    window.initialize()
    window.export_format.setCurrentIndex(1)
    assert window.export_count_labels["current"].text() == "1 página"
    window.preview_before_export.setChecked(False)
    window.export("current")
    wait_idle(window)
    assert window.last_export_path.suffix == ".pdf"
    assert window.last_export_path.exists()
    job = export_job(
        window.graph,
        window.graph_view.positions(),
        window.states,
        window.start,
        window.target,
        0,
        "all",
        window.output_dir,
        output_format="pdf",
    )
    next(job)
    job.close()
    assert len(list(window.output_dir.rglob("*.pdf"))) == 1


@pytest.mark.parametrize("kind", ["current", "all", "combined", "final"])
def test_pdf_preview_reuses_png_images(window, kind):
    from PySide6.QtWidgets import QLabel

    window.detail_checkbox.setChecked(False)
    window.initialize()
    previews = []
    for format_name in ("png", "pdf"):
        window.export_format.setCurrentIndex(window.export_format.findData(format_name))
        assert window.preview_before_export.isChecked()
        window.export(kind)
        title = "Vista previa del PDF" if format_name == "pdf" else "Vista previa de exportación"
        dialog = next(d for d in window.findChildren(QDialog) if d.windowTitle() == title)
        previews.append(
            [
                label.pixmap().toImage()
                for label in dialog.findChildren(QLabel)
                if not label.pixmap().isNull()
            ]
        )
        if format_name == "pdf":
            assert any(
                label.text() == "Página 1 de la muestra" for label in dialog.findChildren(QLabel)
            )
        dialog.close()
    assert previews[0] == previews[1]
    assert len(previews[1]) == (1 if kind in {"current", "final"} else 2)
    assert not window.output_dir.exists()


@pytest.mark.parametrize("format_name", ["png", "pdf"])
def test_export_preview_confirm_and_cancel(window, format_name):
    from conftest import wait_idle
    from PySide6.QtWidgets import QPushButton

    window.initialize()
    window.export_format.setCurrentIndex(window.export_format.findData(format_name))
    assert window.preview_before_export.isChecked()
    window.export_buttons[0].click()
    dialog = next(d for d in window.findChildren(QDialog) if d.isVisible())
    assert dialog.isModal()
    assert not window.output_dir.exists()
    dialog.reject()
    assert not window.output_dir.exists()
    window.export_buttons[0].click()
    dialog = next(d for d in window.findChildren(QDialog) if d.isVisible())
    dialog.findChild(QPushButton, "confirmExport").click()
    wait_idle(window)
    assert window.last_export_path.suffix == f".{format_name}"
    assert len(list(window.output_dir.iterdir())) == 1
