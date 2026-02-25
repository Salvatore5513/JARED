from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Optional
import numpy as np


@dataclass(frozen=True)
class WakeResult:
    triggered: bool
    confidence: float = 1.0
    reason: str = "unknown"
    audio: Optional[np.ndarray] = None #int16 mono pre-roll (optional)


class WakeWordEngine(Protocol):
    name: str

    def start(self) -> None: ...
    def stop(self) -> None: ...

    def poll(self) -> WakeResult:
        """Non-blocking check. Return triggered=True when wake detected."""
        ...
