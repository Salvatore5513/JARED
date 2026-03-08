from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class EventBridge(QObject):
    event_received = Signal(str, dict)

    def __init__(self, bus):
        super().__init__()
        self.bus = bus
        self._bus = bus
        self._bus.subscribe("*", self._on_event)

    def _on_event(self, evt) -> None:
        self.event_received.emit(evt.topic, dict(evt.data))