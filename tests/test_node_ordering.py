from pathlib import Path

import pytest

from graph_visualizer.ui.node_combo_box import NodeComboBox, sorted_node_ids


@pytest.mark.parametrize(
    ("nodes", "expected"),
    [
        (["10", "2", "1", "12"], ["1", "2", "10", "12"]),
        (["-2", "3.5", "0", "-10", "1e2"], ["-10", "-2", "0", "3.5", "1e2"]),
        (["10", "b", "2", "Z", "a", "A"], ["A", "a", "b", "Z", "2", "10"]),
        (["1.0", "01", "1", "2"], ["01", "1", "1.0", "2"]),
        (["inf", "NaN", "3", "A10", "A2"], ["A10", "A2", "inf", "NaN", "3"]),
        ([str(10**40), "2", str(10**30)], ["2", str(10**30), str(10**40)]),
    ],
)
def test_numeric_and_mixed_node_order(nodes, expected):
    assert sorted_node_ids(nodes) == expected


def test_combo_reordering_preserves_the_selected_string_id(qapp):
    combo = NodeComboBox()
    combo.set_nodes(["10", "2", "01", "1"], "01")
    changes = []
    combo.currentIndexChanged.connect(changes.append)
    combo.set_nodes(["10", "B", "2", "01", "1", "A"])
    assert combo.currentData() == "01"
    assert combo.itemData(combo.findData("1")) == "1"
    assert combo.toolTip() == "Nodo 01"
    assert not changes


def test_every_node_selector_uses_the_order_after_edit_undo_and_preset_load(window):
    selectors = (
        window.start_combo,
        window.target_combo,
        window.editor.node_combo,
        window.editor.source_combo,
        window.editor.target_combo,
    )
    expected = [str(index) for index in range(1, 13)]
    assert (window.start, window.target) == ("1", "12")
    assert all([combo.itemData(i) for i in range(combo.count())] == expected for combo in selectors)
    window.add_node("Z")
    window.add_node("A")
    window.add_node("20")
    assert (window.start, window.target) == ("1", "12")
    expected = ["A", "Z", *expected, "20"]
    assert all([combo.itemData(i) for i in range(combo.count())] == expected for combo in selectors)
    window.undo()
    assert window.target_combo.itemData(window.target_combo.count() - 1) == "12"
    window.redo()
    assert window.target == "12"
    window.preset_baseline = window.preset_fingerprint()
    window.load_preset_path(Path("src/graph_visualizer/examples/bellman_ford.json"))
    assert [window.start_combo.itemData(i) for i in range(window.start_combo.count())] == list(
        "uvxyz"
    )
    assert (window.start, window.target) == ("z", "y")


def test_deleting_destination_selects_the_largest_remaining_numeric_id(window):
    window.delete_node("12")
    assert window.target == "11"
    window.undo()
    assert window.target == "12"
