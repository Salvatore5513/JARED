from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
import uuid
import time


# -----------------------------
# Enums
# -----------------------------

class SafetyClass(int, Enum):
    CLASS_0 = 0   # harmless (lights, volume)
    CLASS_1 = 1   # moderate (garage door)
    CLASS_2 = 2   # hazardous (heater, stove, etc.)


class AuthLevel(str, Enum):
    NONE = "none"
    PTT = "ptt"
    PIN = "pin"


# -----------------------------
# Core Runtime Objects
# -----------------------------

@dataclass
class ActionRequest:
    intent_name: str
    slots: Dict[str, Any]

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ts_ms: int = field(default_factory=lambda: int(time.time() * 1000))

    source: str = "voice"
    device_id: Optional[str] = None
    room_id: Optional[str] = None

    auth_level: AuthLevel = AuthLevel.NONE
    safety_class: SafetyClass = SafetyClass.CLASS_0

    requires_verification: bool = False
    confidence: Optional[float] = None


@dataclass
class PolicyDecision:
    allowed: bool
    reason_code: str
    message: str

    required_auth: AuthLevel = AuthLevel.NONE
    requires_verification: bool = False


@dataclass
class ActionOutcome:
    request: ActionRequest
    policy: PolicyDecision
    execution_result: Optional[Dict[str, Any]] = None
    verification_result: Optional[Dict[str, Any]] = None