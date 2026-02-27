from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class Room:
    room_id: str
    name: str


@dataclass(frozen=True)
class DeviceTemplate:
    template_id: str
    name: str
    driver_kind: str
    capabilities: Dict[str, Any]


@dataclass(frozen=True)
class DeviceRecord:
    device_id: str
    name: str
    room_id: str
    template_id: str
    driver_kind: str
    capabilities: Dict[str, Any]
    driver_config: Dict[str, Any]
    enabled: bool = True


@dataclass(frozen=True)
class DeviceTarget:
    """
    A minimal target object DeviceManager can pass in.
    You can build this from slots: room/device.
    """
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    room_id: Optional[str] = None
    room_name: Optional[str] = None