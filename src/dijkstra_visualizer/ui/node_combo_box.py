from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox


class NodeComboBox(QComboBox):
    # Guarda texto en QVariant para no limitar los ID al rango de enteros de Qt.
    def addItem(self, text, userData=None) -> None:
        super().addItem(text, str(userData) if userData is not None else None)

    def itemData(self, index, role=Qt.ItemDataRole.UserRole):
        value = super().itemData(index, role)
        return int(value) if role == Qt.ItemDataRole.UserRole and value is not None else value

    def currentData(self, role=Qt.ItemDataRole.UserRole):
        return self.itemData(self.currentIndex(), role)

    def findData(
        self,
        data,
        role=Qt.ItemDataRole.UserRole,
        flags=Qt.MatchFlag.MatchExactly | Qt.MatchFlag.MatchCaseSensitive,
    ) -> int:
        value = str(data) if role == Qt.ItemDataRole.UserRole and data is not None else data
        return super().findData(value, role, flags)
