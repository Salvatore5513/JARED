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

    Supported subscription patterns:
      - Exact:         "voice.wake"
      - Head wildcard: "voice.*"          (matches "voice.<anything>")
      - Prefix glob:   "voice.wake*"      (matches "voice.wake", "voice.wake.detected", etc.)
      - All:           "*"                (matches everything)
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
            subs_snapshot = list(self._subs.items())

        matched: list[Handler] = []
        for pattern, handlers in subs_snapshot:
            if self._matches(pattern, topic):
                matched.extend(handlers)

        self._fanout(evt, matched)

    @staticmethod
    def _matches(pattern: str, topic: str) -> bool:
        # "*" = everything
        if pattern == "*":
            return True

        # exact match
        if pattern == topic:
            return True

        # head wildcard: "voice.*" => matches "voice.<anything>"
        if pattern.endswith(".*"):
            prefix = pattern[:-1]  # "voice."
            return topic.startswith(prefix)

        # prefix glob: "voice.wake*" => matches anything starting with "voice.wake"
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return topic.startswith(prefix)

        return False

    @staticmethod
    def _fanout(evt: Event, handlers: Iterable[Handler]) -> None:
        for h in handlers:
            try:
                h(evt)
            except Exception:
                print(f"[EventBus] handler error (topic={evt.topic})")
                traceback.print_exc()