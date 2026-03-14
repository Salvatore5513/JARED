from __future__ import annotations

import json
from typing import Any

from core.event_bus import Event, EventBus
from nlp.memory.stores import MemoryStore


class WorkingMemoryService:
    """
    Step 2:
    Record recognized command intents into memory_command_history.

    This is recall-only for now.
    It does not change execution behavior.
    """

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def attach(self, bus: EventBus) -> None:
        bus.subscribe("nlp.intent", self._on_intent)

    def _on_intent(self, evt: Event) -> None:
        data = evt.data or {}

        raw_text = data.get("raw_text", "")
        intent_name = data.get("name")
        intent_confidence = data.get("confidence")
        slots = data.get("slots") or {}

        if not isinstance(slots, dict):
            slots = {}

        device_id = self._first_present(
            slots,
            "device_id",
            "target_device_id",
        )
        room_id = self._first_present(
            slots,
            "room_id",
            "target_room_id",
        )
        source_endpoint_id = data.get("source_endpoint_id")
        request_id = data.get("request_id")

        self.record_command(
            transcript=raw_text,
            intent_name=intent_name,
            intent_confidence=intent_confidence,
            device_id=device_id,
            room_id=room_id,
            slots=slots,
            source_endpoint_id=source_endpoint_id,
            outcome="intent_detected",
            request_id=request_id,
        )

    def record_command(
        self,
        *,
        transcript: str,
        intent_name: str | None,
        intent_confidence: float | None,
        device_id: str | None,
        room_id: str | None,
        slots: dict[str, Any] | None,
        source_endpoint_id: str | None = None,
        outcome: str | None = None,
        request_id: str | None = None,
    ) -> None:
        payload = json.dumps(slots or {}, ensure_ascii=False)

        with self.store._connect() as conn:
            conn.execute(
                """
                INSERT INTO memory_command_history (
                    project_id,
                    ts,
                    source,
                    source_endpoint_id,
                    room_id,
                    request_id,
                    raw_text,
                    normalized_text,
                    intent_name,
                    intent_confidence,
                    device_id,
                    outcome,
                    slots_json
                )
                VALUES (?, strftime('%s','now'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self.store.default_project_id,
                    "voice",
                    source_endpoint_id,
                    room_id,
                    request_id,
                    transcript,
                    transcript,
                    intent_name,
                    intent_confidence,
                    device_id,
                    outcome,
                    payload,
                ),
            )
            conn.commit()

    @staticmethod
    def _first_present(data: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = data.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None