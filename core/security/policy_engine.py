from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple

from devices.execution.action_request import ActionRequest, PolicyDecision, SafetyClass, AuthLevel


@dataclass(frozen=True)
class PolicyConfig:
    """
    Milestone 3 policy config.
    Keep it simple and local/offline-first.
    """
    # How long an auth grant is considered valid (PIN/PTT window)
    auth_window_ms: int = 60_000

    # Require verification on all SafetyClass >= this threshold (in addition to any per-intent rules)
    verify_threshold: SafetyClass = SafetyClass.CLASS_2

    # Rate limiting (very simple per-intent throttle)
    default_cooldown_ms: int = 700


class PolicyEngine:
    """
    Single gate for device execution.

    Inputs:
      - ActionRequest (intent_name, slots, safety_class, auth_level, etc.)
      - optional context (auth state, rate limits, offline mode flags)

    Output:
      - PolicyDecision (allow/deny + requirements)
    """

    def __init__(self, config: Optional[PolicyConfig] = None):
        self.config = config or PolicyConfig()

        # Simple maps you can grow later (or move to config files).
        # For Milestone 3 keep it readable.
        self.intent_safety_map: Dict[str, SafetyClass] = {
            # power/level on normal devices
            "device.set_power": SafetyClass.CLASS_0,
            "device.toggle": SafetyClass.CLASS_0,
            "device.set_level": SafetyClass.CLASS_0,

            # examples of higher-risk intents (you can expand later)
            "device.garage_door": SafetyClass.CLASS_1,
            "device.heater_power": SafetyClass.CLASS_2,
            "device.stove_power": SafetyClass.CLASS_2,
        }

        # Intent-specific verification requirements (in addition to safety threshold)
        self.intent_verify_map: Dict[str, bool] = {
            "device.garage_door": True,
        }

        # Class 2 rules: ON vs OFF behavior
        # We treat OFF as safer: no auth, but verify.
        self.class2_on_requires_auth: AuthLevel = AuthLevel.PIN

    def decide(
        self,
        req: ActionRequest,
        *,
        offline_only: bool = True,
        device_known: bool = True,
        capability_ok: bool = True,
        slots_ok: bool = True,
        rate_limited: bool = False,
        now_ms: Optional[int] = None,
        # If you already have an auth-window module, you can pass its result here.
        auth_granted: bool = False,
    ) -> PolicyDecision:
        """
        Returns a PolicyDecision. This function must be the only execution gate.

        The booleans (device_known/capability_ok/slots_ok/rate_limited/auth_granted)
        are fed by DeviceManager + Registry + RateLimiter + AuthWindow.
        """
        _ = now_ms  # reserved for future time-based policies

        # Basic input validation gates (keep them explicit)
        if not device_known:
            return PolicyDecision(
                allowed=False,
                reason_code="DENY_UNKNOWN_DEVICE",
                message="I can't find that device.",
                required_auth=AuthLevel.NONE,
                requires_verification=False,
            )

        if not capability_ok:
            return PolicyDecision(
                allowed=False,
                reason_code="DENY_UNKNOWN_CAPABILITY",
                message="That device can't do that.",
                required_auth=AuthLevel.NONE,
                requires_verification=False,
            )

        if not slots_ok:
            return PolicyDecision(
                allowed=False,
                reason_code="DENY_BAD_SLOTS",
                message="That command is missing information.",
                required_auth=AuthLevel.NONE,
                requires_verification=False,
            )

        if rate_limited:
            return PolicyDecision(
                allowed=False,
                reason_code="DENY_RATE_LIMIT",
                message="Too many commands too quickly.",
                required_auth=AuthLevel.NONE,
                requires_verification=False,
            )

        # Determine safety class
        safety_class = self.intent_safety_map.get(req.intent_name, req.safety_class)
        requires_verification = bool(self.intent_verify_map.get(req.intent_name, False))

        # Safety threshold verification
        if safety_class >= self.config.verify_threshold:
            requires_verification = True

        # Class 2 special rules: ON requires auth, OFF does not (but verify)
        if safety_class == SafetyClass.CLASS_2:
            is_on = self._extract_on_off(req.slots)

            if is_on is True:
                # Must be within auth window (PIN by default)
                if not auth_granted or req.auth_level != self.class2_on_requires_auth:
                    return PolicyDecision(
                        allowed=False,
                        reason_code="DENY_CLASS2_REQUIRES_AUTH",
                        message="That requires authorization.",
                        required_auth=self.class2_on_requires_auth,
                        requires_verification=True,  # still verify once executed
                    )
            elif is_on is False:
                # OFF allowed, but verification required
                requires_verification = True
            else:
                # Unknown state: treat as risky
                return PolicyDecision(
                    allowed=False,
                    reason_code="DENY_BAD_SLOTS",
                    message="For safety, say on or off.",
                    required_auth=AuthLevel.NONE,
                    requires_verification=False,
                )

        # Offline-only enforcement placeholder:
        # In Milestone 3, most device drivers are local (MQTT/LAN).
        # If later you mark certain intents as 'network_required', deny them here when offline_only=True.
        # For now we keep it permissive because NetPolicy enforces outbound anyway.
        if offline_only is False:
            pass

        return PolicyDecision(
            allowed=True,
            reason_code="OK",
            message="Allowed.",
            required_auth=AuthLevel.NONE,
            requires_verification=requires_verification,
        )

    @staticmethod
    def _extract_on_off(slots: Dict[str, Any]) -> Optional[bool]:
        """
        Returns:
          True  => ON
          False => OFF
          None  => unknown
        """
        # Common slot keys you might emit from NLP:
        # state: "on"/"off", power: "on"/"off", value: 1/0, enabled: true/false
        for key in ("state", "power", "enabled"):
            if key in slots:
                v = slots[key]
                if isinstance(v, bool):
                    return v
                if isinstance(v, (int, float)):
                    if v == 1:
                        return True
                    if v == 0:
                        return False
                if isinstance(v, str):
                    s = v.strip().lower()
                    if s in ("on", "true", "enabled", "enable", "start", "open"):
                        return True
                    if s in ("off", "false", "disabled", "disable", "stop", "close"):
                        return False

        # Also accept level semantics (level > 0 implies on)
        if "level" in slots and isinstance(slots["level"], (int, float)):
            return slots["level"] > 0

        return None