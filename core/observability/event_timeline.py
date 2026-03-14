from __future__ import annotations

import time
from core.event_bus import EventBus
from core.observability.logger import get_logger


class EventTimeline:
    """
    Debug helper that logs every event flowing through the EventBus.
    Extremely useful for debugging pipelines.
    """

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus
        self.log = get_logger("JARED")

        # Subscribe to everything
        bus.subscribe("*", self._on_event)

    def _on_event(self, evt) -> None:
        ts = time.strftime("%H:%M:%S")
        topic = evt.topic

        # Trim payload so logs stay readable
        payload = evt.data
        if isinstance(payload, dict):
            payload = {k: payload[k] for k in list(payload)[:3]}

        self.log.debug(f"[timeline] {ts} {topic} {payload}")