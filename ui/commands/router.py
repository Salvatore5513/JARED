from __future__ import annotations

from core.contracts.action_request import ActionRequest, AuthLevel, SafetyClass
from devices.execution.device_manager import DeviceManager
from devices.registry.models import DeviceTarget


class UiCommandRouter:
    """
    Translates UI-originated command events into ActionRequest executions.

    UI widgets publish high-level UI events onto the EventBus.
    This router is the application-layer adapter that converts them
    into the normal device execution pipeline.
    """

    def __init__(self, bus, device_manager: DeviceManager) -> None:
        self.bus = bus
        self.device_manager = device_manager

        self.bus.subscribe("ui.device.set_power_request", self._on_device_set_power_request)

    def _on_device_set_power_request(self, evt) -> None:
        device_id = str(evt.data.get("device_id", "")).strip()
        state = str(evt.data.get("state", "")).strip().lower()

        if not device_id:
            return
        if state not in {"on", "off"}:
            return

        req = ActionRequest(
            intent_name="device.set_power",
            slots={"state": state},
            source="ui",
            device_id=device_id,
            auth_level=AuthLevel.NONE,
            safety_class=SafetyClass.CLASS_0,
            confidence=1.0,
        )

        target = DeviceTarget(device_id=device_id)
        self.device_manager.handle(req, target=target)