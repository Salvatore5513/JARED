from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Callable, DefaultDict, Iterable
import threading
import time
import traceback


@dataclass(frozen=True)
class Event:
    topic: str
    data: dict[str, Any]
    ts: float = field(default_factory=time.time)


Handler = Callable[[Event], None]


class EventBus:
    """
    Lightweight in-process pub/sub.

    Topics are dotted strings: "voice.wake", "voice.transcript", etc.

    Wildcards:
      - Subscribe to "voice.*" to receive any event whose topic starts with "voice."
    """

    def __init__(self) -> None:
        self._subs: DefaultDict[str, list[Handler]] = defaultdict(list)
        self._lock = threading.RLock()

    def subscribe(self, topic: str, handler: Handler) -> None:
        with self._lock:
            self._subs[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Handler) -> None:
        with self._lock:
            handlers = self._subs.get(topic)
            if not handlers:
                return
            try:
                handlers.remove(handler)
            except ValueError:
                return

    def publish(self, topic: str, **data: Any) -> None:
        evt = Event(topic=topic, data=data)

        # Copy handlers under lock; execute outside lock
        with self._lock:
            exact = list(self._subs.get(topic, []))
            wildcard = list(self._subs.get(self._wildcard(topic), []))

        self._fanout(evt, exact)
        self._fanout(evt, wildcard)

    @staticmethod
    def _wildcard(topic: str) -> str:
        # "voice.wake" -> "voice.*"
        head = topic.split(".", 1)[0]
        return f"{head}.*"

    @staticmethod
    def _fanout(evt: Event, handlers: Iterable[Handler]) -> None:
        for h in handlers:
            try:
                h(evt)
            except Exception:
                # local-only: print is acceptable for now; later route to observability logger
                print(f"[EventBus] handler error (topic={evt.topic})")
                traceback.print_exc()