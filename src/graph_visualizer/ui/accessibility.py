"""Native announcements for state changes, progress and recoverable errors."""

from PySide6.QtGui import QAccessible, QAccessibleAnnouncementEvent
from PySide6.QtWidgets import QLabel


def announce(widget, message, *, urgent=False):
    if not message or not QAccessible.isActive():
        return
    event = QAccessibleAnnouncementEvent(widget, message)
    event.setPoliteness(
        QAccessible.AnnouncementPoliteness.Assertive
        if urgent
        else QAccessible.AnnouncementPoliteness.Polite
    )
    QAccessible.updateAccessibility(event)


class MessageLabel(QLabel):
    def __init__(self, parent=None, *, urgent=False):
        super().__init__(parent)
        self.urgent = urgent

    def setText(self, message):
        changed = message != self.text()
        super().setText(message)
        if changed:
            announce(self, message, urgent=self.urgent)
