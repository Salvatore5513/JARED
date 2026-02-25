from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, DefaultDict
from collections import defaultdict
import threading
import time


@dataclass(frozen=True)
class Event:
    topic: str
    data: dict[str, Any]
    ts: float = field(default_factory=time.time)


Handler = Callable[[Event], None]


class EventBus:
    def __init__(self) -> None:
        self._subs: DefaultDict[str, list[Handler]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, topic: str, handler: Handler) -> None:
        with self._lock:
            self._subs[topic].append(handler)

    def publish(self, topic: str, **data: Any) -> None:
        evt = Event(topic=topic, data=data)

        # Copy handlers under lock; execute outside lock
        with self._lock:
            exact = list(self._subs.get(topic, []))
            star = topic.split(".", 1)[0] + ".*"
            wildcard = list(self._subs.get(star, []))

        # Fan-out to exact topic subscribers
        for h in exact:
            try:
                h(evt)
            except Exception as e:
                print(f"[EventBus] handler error (topic={topic}): {e}")

        # Optional wildcard: "voice.*"
        for h in wildcard:
            try:
                h(evt)
            except Exception as e:
                print(f"[EventBus] handler error (topic={star}): {e}")
