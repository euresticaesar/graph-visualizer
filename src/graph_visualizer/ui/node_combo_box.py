import re
from collections.abc import Iterable
from decimal import Decimal, InvalidOperation

from PySide6.QtCore import QSignalBlocker
from PySide6.QtWidgets import QComboBox

NUMERIC_ID = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\Z")


def sorted_node_ids(nodes: Iterable[str]) -> list[str]:
    """Alphabetical names precede numeric IDs; identity and algorithm order stay intact."""

    def key(node: str):
        if NUMERIC_ID.fullmatch(node):
            try:
                return 1, Decimal(node), node
            except InvalidOperation:
                pass
        return 0, node.casefold(), node

    return sorted(nodes, key=key)


class NodeComboBox(QComboBox):
    """Selectors preserve string node IDs and integer connection keys."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(6)
        self.currentTextChanged.connect(self.setToolTip)

    def set_nodes(self, nodes: Iterable[str], selected: str | None = None) -> None:
        selected = self.currentData() if selected is None else selected
        ordered = sorted_node_ids(nodes)
        with QSignalBlocker(self):
            if [self.itemData(index) for index in range(self.count())] != ordered:
                self.clear()
                for node in ordered:
                    self.addItem(f"Nodo {node}", node)
            index = self.findData(selected)
            self.setCurrentIndex(index if index >= 0 else 0)
        self.setToolTip(self.currentText())
