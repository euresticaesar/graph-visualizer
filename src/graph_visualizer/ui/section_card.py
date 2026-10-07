from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class SectionCard(QFrame):
    """A titled group of related controls, shared by the sidebar pages."""

    def __init__(self, title: str, description: str = "", parent=None):
        super().__init__(parent)
        self.setObjectName("sectionCard")
        self.content = QVBoxLayout(self)
        self.content.setContentsMargins(12, 10, 12, 12)
        self.content.setSpacing(8)
        heading = QLabel(title)
        heading.setObjectName("section")
        self.content.addWidget(heading)
        if description:
            hint = QLabel(description)
            hint.setObjectName("hint")
            hint.setWordWrap(True)
            self.content.addWidget(hint)
