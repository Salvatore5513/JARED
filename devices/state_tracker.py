from __future__ import annotations

import json
from pathlib import Path


class DeviceStateTracker:
    def __init__(self, bus, *, state_path: Path, registry) -> None:
        self.bus = bus
        self.state_path = state_path
        self.registry = registry

        self._device_power_state: dict[str, str] = self._load_state()
        self._pending_power_state_by_request_id: dict[str, str] = {}
        self._request_to_device_id: dict[str, str] = {}
        self._device_availability: dict[str, str] = {}

        self.bus.subscribe("action.requested", self._on_action_requested)
        self.bus.subscribe("action.policy_decided", self._on_action_policy_decided)
        self.bus.subscribe("action.executed", self._on_action_executed)
        self.bus.subscribe("device.state.changed", self._on_device_state_changed)
        self.bus.subscribe("action.failed", self._on_action_failed)
        self.bus.subscribe("device.availability.changed", self._on_device_availability_changed)

    def get_power_state(self, device_id: str) -> str:
        return self._device_power_state.get(device_id, "unknown")

    def get_availability(self, device_id: str) -> str:
        return self._device_availability.get(device_id, "unknown")

    def _load_state(self) -> dict[str, str]:
        try:
            if not self.state_path.exists():
                return {}

            raw = json.loads(self.state_path.read_text(encoding="utf-8"))
            if not isinstance(raw, dict):
                return {}

            cleaned: dict[str, str] = {}
            for k, v in raw.items():
                device_id = str(k).strip()
                state = str(v).strip().lower()
                if device_id and state in {"on", "off", "open", "closed", "unknown"}:
                    cleaned[device_id] = state
            return cleaned
        except Exception:
            return {}

    def _set_availability(self, device_id: str, availability: str) -> None:
        availability = str(availability).strip().lower()
        if availability not in {"online", "offline", "unknown"}:
            return

        current = self._device_availability.get(device_id)
        if current == availability:
            return

        self._device_availability[device_id] = availability
        self.bus.publish(
            "device.availability.changed.confirmed",
            device_id=device_id,
            availability=availability,
        )
        self.bus.publish("ui.devices.refresh")

    def _save_state(self) -> None:
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self.state_path.write_text(
                json.dumps(self._device_power_state, indent=2, sort_keys=True),
                encoding="utf-8",
            )
        except Exception:
            pass

    def _on_action_requested(self, evt) -> None:
        request = evt.data.get("request", {}) or {}
        if not isinstance(request, dict):
            return

        intent_name = str(request.get("intent_name", "")).strip()
        if intent_name not in {"device.set_power", "device.toggle"}:
            return

        request_id = str(request.get("request_id", "")).strip()
        if not request_id:
            return

        slots = request.get("slots", {}) or {}
        state = str(slots.get("state", "")).strip().lower()
        if state not in {"on", "off"}:
            return

        self._pending_power_state_by_request_id[request_id] = state

        device_id = str(evt.data.get("device_id", "")).strip()
        if device_id:
            self._request_to_device_id[request_id] = device_id

    def _on_action_policy_decided(self, evt) -> None:
        request_id = str(evt.data.get("request_id", "")).strip()
        device_id = str(evt.data.get("device_id", "")).strip()

        if request_id and device_id:
            self._request_to_device_id[request_id] = device_id

    def _on_action_executed(self, evt) -> None:
        request_id = str(evt.data.get("request_id", "")).strip()
        if not request_id:
            return

        state = self._pending_power_state_by_request_id.pop(request_id, "")
        device_id = str(evt.data.get("device_id", "")).strip() or self._request_to_device_id.pop(request_id, "")

        if state not in {"on", "off"}:
            return
        if not device_id:
            return

        driver_result = evt.data.get("driver_result", {}) or {}
        if not isinstance(driver_result, dict):
            return
        if not driver_result.get("ok", False):
            return

        self._set_state(device_id, state, source="command")
        self._set_availability(device_id, "online")

    def _on_action_failed(self, evt) -> None:
        request_id = str(evt.data.get("request_id", "")).strip()
        if not request_id:
            return

        stage = str(evt.data.get("stage", "")).strip().lower()
        device_id = str(evt.data.get("device_id", "")).strip() or self._request_to_device_id.get(request_id, "")

        if stage == "execute" and device_id:
            if request_id in self._pending_power_state_by_request_id:
                self._set_availability(device_id, "offline")

        if stage in {"resolve", "policy", "execute", "verify"}:
            self._pending_power_state_by_request_id.pop(request_id, None)
            self._request_to_device_id.pop(request_id, None)

    def _on_device_availability_changed(self, evt) -> None:
        device_id = str(evt.data.get("device_id", "")).strip()
        availability = str(evt.data.get("availability", "")).strip().lower()

        if not device_id:
            return

        self._set_availability(device_id, availability)

    def _on_device_state_changed(self, evt) -> None:
        device_id = str(evt.data.get("device_id", "")).strip()
        state = str(evt.data.get("state", "")).strip().lower()

        if not device_id:
            return
        if state not in {"on", "off", "open", "closed", "unknown"}:
            return

        self._set_state(device_id, state, source="external")

    def _set_state(self, device_id: str, state: str, *, source: str) -> None:
        current = self._device_power_state.get(device_id)
        if current == state:
            return

        self._device_power_state[device_id] = state
        self._save_state()

        self.bus.publish(
            "device.state.changed.confirmed",
            device_id=device_id,
            state=state,
            source=source,
        )
        self.bus.publish("ui.devices.refresh")