from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Protocol

from devices.registry.models import DeviceRecord
from devices.execution.action_request import ActionRequest


@dataclass
class DriverResult:
    ok: bool
    driver_code: str
    details: str
    raw: Optional[Dict[str, Any]] = None


class Driver(Protocol):
    kind: str

    def supports(self, capability: str) -> bool: ...
    def execute(self, device: DeviceRecord, action: ActionRequest) -> DriverResult: ...
    def read_state(self, device: DeviceRecord) -> Optional[Dict[str, Any]]: ...