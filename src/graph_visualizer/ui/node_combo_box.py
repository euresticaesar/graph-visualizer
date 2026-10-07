from PySide6.QtWidgets import QComboBox


class NodeComboBox(QComboBox):
    """Selectors preserve string node IDs and integer connection keys."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.setMinimumContentsLength(6)
        self.currentTextChanged.connect(self.setToolTip)
