from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from core.contracts.action_request import ActionRequest
from devices.execution.device_manager import DeviceManager
from devices.registry.models import DeviceTarget


def _to_dict(payload: Any) -> dict[str, Any]:
    if payload is None:
        return {}

    if isinstance(payload, dict):
        return dict(payload)

    if is_dataclass(payload) and not isinstance(payload, type):
        return dict(asdict(payload))

    raise TypeError(f"Unsupported payload type: {type(payload)!r}")


class ReviewExecutor:
    def __init__(self, device_manager: DeviceManager) -> None:
        self._device_manager = device_manager

    def execute(self, *, request_payload: Any, target_payload: Any) -> None:
        request_data = _to_dict(request_payload)
        target_data = _to_dict(target_payload)

        req = ActionRequest(**request_data)
        target = DeviceTarget(**target_data)

        self._device_manager.handle(req, target=target)