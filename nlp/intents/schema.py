from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IntentMatch:
    name: str
    confidence: float
    slots: dict[str, Any]
    raw_text: str
