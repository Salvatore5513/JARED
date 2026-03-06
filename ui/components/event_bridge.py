from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Qt


class EventBridge(QObject):
    """
    Bridges EventBus events (runtime thread) -> Qt signals (UI thread).
    """
    event_received = Signal(str, dict)

    def __init__(self, bus):
        super().__init__()
        self.bus = bus
        self._bus = bus
        # Subscribe to everything for logs + routing
        self._bus.subscribe("*", self._on_event)

    def _on_event(self, evt):
        # evt is your Event dataclass instance
        # emit payload as a plain dict (Qt-friendly)
        self.event_received.emit(evt.topic, dict(evt.data))
        