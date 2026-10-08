import pytest
from PySide6.QtCore import QEvent, QPoint, QRect, Qt
from PySide6.QtGui import QHelpEvent
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QAbstractButton, QCheckBox, QScrollArea, QToolTip

from graph_visualizer.core.models import StateView


@pytest.mark.parametrize("algorithm", ["Dijkstra", "A*", "Bellman-Ford", "Floyd-Warshall"])
def test_export_detail_and_filter_share_a_section_and_preserve_exact_events(window, algorithm):
    window.algorithm_combo.setCurrentText(algorithm)
    window.initialize()
    window.tabs.setCurrentIndex(3)
    events, visible, index = window.states.events, window.states, window.state_index
    form = window.export_selection_form
    assert window.export_detail.parentWidget() is window.export_selection.parentWidget()
    assert form.labelForField(window.export_detail).text() == "Detalle"
    assert form.labelForField(window.export_selection).text() == "Filtro"
    assert not window.export_from.isVisible() and not window.export_to.isVisible()
    window.export_detail.setCurrentIndex(1)
    base = StateView(events, False) if algorithm != "Bellman-Ford" else visible
    window.export_selection.setCurrentIndex(1)
    window.export_from.setValue(1)
    window.export_to.setValue(2)
    assert window.export_from.isVisible() and window.export_to.isVisible()
    assert [state.step for state in window._export_states("all")] == [
        base[1].step,
        base[2].step,
    ]
    assert window._export_states("current") is visible
    assert window._export_states("final") is visible
    for mode in (0, 2, 3):
        window.export_selection.setCurrentIndex(mode)
        assert not window.export_from.isVisible() and not window.export_to.isVisible()
    window.export_selection.setCurrentIndex(1)
    assert (window.export_from.value(), window.export_to.value()) == (1, 2)
    assert window.states is visible and window.state_index == index
    assert window.states.events is events and not window.output_dir.exists()


@pytest.mark.parametrize("font_size", [13, 18])
@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("layout", ["classic", "right", "bottom"])
def test_export_page_reflows_without_horizontal_scroll_or_clipped_controls(
    window, font_size, theme, layout
):
    window.preferences.update(ui_font_size=font_size, theme=theme, ui_layout=layout)
    window.apply_appearance()
    window.tabs.setCurrentIndex(3)
    scroll = window.tabs.widget(3).findChild(QScrollArea, "controlScroll")
    page = scroll.widget()
    for sidebar_width, height in ((310, 680), (365, 940), (520, 940), (310, 680)):
        window.resize(940 if sidebar_width == 310 else 1380, height)
        sizes = [sidebar_width, window.width() - sidebar_width]
        window.workspace_splitter.setSizes(sizes[::-1] if layout == "right" else sizes)
        for expanded in (False, True):
            window.export_advanced_button.setChecked(expanded)
            for mode in (0, 1):
                window.export_selection.setCurrentIndex(mode)
                QTest.qWait(10)
                assert scroll.horizontalScrollBarPolicy() == Qt.ScrollBarPolicy.ScrollBarAlwaysOff
                assert scroll.horizontalScrollBar().maximum() == 0
                assert not scroll.horizontalScrollBar().isVisible()
                assert page.width() == scroll.viewport().width()
                assert page.minimumSizeHint().width() <= page.width()
                for button in page.findChildren(QAbstractButton):
                    if button.isVisible():
                        rect = QRect(button.mapTo(page, QPoint()), button.size())
                        assert page.rect().contains(rect)
                        assert button.width() >= button.minimumSizeHint().width()
                for field in (
                    window.export_format,
                    window.export_style,
                    window.export_theme,
                    window.export_resolution,
                    window.export_detail,
                    window.export_selection,
                    window.export_layout,
                    window.export_composition,
                    window.export_graph_fraction,
                    window.export_group,
                    window.export_font_scale,
                    window.export_title,
                    window.export_from,
                    window.export_to,
                ):
                    if field.isVisible():
                        rect = QRect(field.mapTo(page, QPoint()), field.size())
                        assert page.rect().contains(rect)
                        assert field.width() >= field.minimumSizeHint().width()
                scroll.ensureWidgetVisible(window.output_button)
                rect = QRect(
                    window.output_button.mapTo(scroll.viewport(), QPoint()),
                    window.output_button.size(),
                )
                assert scroll.viewport().rect().contains(rect)


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_checkbox_help_is_available_on_startup_and_shown_by_native_tooltips(window, qapp, theme):
    window.preferences["theme"] = theme
    window.apply_appearance()
    boxes = window.findChildren(QCheckBox)
    assert boxes
    for checkbox in boxes:
        assert checkbox.toolTip().strip()
        assert len(checkbox.toolTip()) <= 120
    window.tabs.setCurrentIndex(3)
    window.export_advanced_button.click()
    scroll = window.tabs.widget(3).findChild(QScrollArea, "controlScroll")
    for checkbox in (
        window.export_legend,
        window.export_explanation,
        window.export_dim_unrelated,
        window.export_focus,
        window.preview_before_export,
    ):
        scroll.ensureWidgetVisible(checkbox)
        qapp.processEvents()
        point = checkbox.rect().center()
        help_event = QHelpEvent(QEvent.Type.ToolTip, point, checkbox.mapToGlobal(point))
        qapp.sendEvent(checkbox, help_event)
        assert QToolTip.isVisible() and QToolTip.text() == checkbox.toolTip()
        QToolTip.hideText()
    window.algorithm_combo.setCurrentText("Floyd-Warshall")
    assert "intermedio k" in window.detail_checkbox.toolTip()
    window.algorithm_combo.setCurrentText("A*")
    assert "nodo procesado" in window.detail_checkbox.toolTip()
