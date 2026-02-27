from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict

from core.event_bus import EventBus
from core.security.policy_engine import SafetyClass, AuthLevel
from core.contracts.action_request import ActionRequest
from devices.registry.models import DeviceTarget

# Import your real builder from app.main
from app.bootstrap import build_device_manager


def main() -> None:
    bus = EventBus()
    dm = build_device_manager(bus, offline_only=True)

    req = ActionRequest(
        intent_name="device.toggle",
        slots={"state": "on"},
        source="test",
        confidence=1.0,
        safety_class=SafetyClass.CLASS_0,
        auth_level=AuthLevel.NONE,
        device_id=None,
        room_id=None,
    )
    target = DeviceTarget(room_name="garage", device_name="lights")

    before = deepcopy(asdict(req))
    _ = dm.handle(req, target=target)
    after = asdict(req)

    assert before == after, "DeviceManager mutated ActionRequest input (req should be immutable in practice)!"

    print("OK: guardrails_smoke passed")


if __name__ == "__main__":
    main()