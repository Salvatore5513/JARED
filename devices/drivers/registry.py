from __future__ import annotations

from typing import Dict, Optional

from devices.drivers.base import Driver


class DriverRegistry:
    def __init__(self):
        self._drivers: Dict[str, Driver] = {}

    def register(self, driver: Driver) -> None:
        self._drivers[str(driver.kind)] = driver

    def get(self, kind: str) -> Optional[Driver]:
        return self._drivers.get(str(kind))