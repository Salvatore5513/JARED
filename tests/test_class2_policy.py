from devices.execution.action_request import ActionRequest, SafetyClass, AuthLevel
from core.security.policy_engine import PolicyEngine

pe = PolicyEngine()

# Class 2 ON without auth should deny
req = ActionRequest(
    intent_name="device.heater_power",
    slots={"state": "on"},
    safety_class=SafetyClass.CLASS_2,
    auth_level=AuthLevel.NONE,
)

decision = pe.decide(req, device_known=True, capability_ok=True, slots_ok=True, rate_limited=False, auth_granted=False)
print(decision)