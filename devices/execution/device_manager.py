from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from core.event_bus import EventBus
from core.security.audit_log import AuditLog
from core.security.rate_limits import RateLimiter
from core.security.policy_engine import PolicyEngine
from core.security.auth.auth_window import AuthWindow
from devices.execution.action_request import ActionRequest, ActionOutcome, PolicyDecision, AuthLevel
from devices.execution.verifier import Verifier
from devices.registry.models import DeviceTarget
from devices.registry.store import RegistryStore
from devices.drivers.registry import DriverRegistry
from devices.drivers.base import DriverResult


class DeviceManager:
    """
    Milestone 3 orchestrator:
      resolve -> rate limit -> auth -> policy -> execute -> verify -> audit -> events
    """

    def __init__(
        self,
        *,
        event_bus: EventBus,
        registry: RegistryStore,
        drivers: DriverRegistry,
        policy: PolicyEngine,
        auth_window: AuthWindow,
        rate_limiter: RateLimiter,
        audit_log: AuditLog,
        verifier: Optional[Verifier] = None,
        offline_only: bool = True,
    ):
        self.bus = event_bus
        self.registry = registry
        self.drivers = drivers
        self.policy = policy
        self.auth_window = auth_window
        self.rate_limiter = rate_limiter
        self.audit = audit_log
        self.verifier = verifier or Verifier()
        self.offline_only = bool(offline_only)

    def handle(self, req: ActionRequest, *, target: DeviceTarget) -> ActionOutcome:
        # 0) publish requested
        self._emit("action.requested", {"request": asdict(req), "target": asdict(target)})

        # 1) resolve device
        device = self.registry.resolve_device(target)
        if not device:
            decision = self.policy.decide(req, offline_only=self.offline_only, device_known=False)
            self._audit_policy(req, decision)
            self._emit("action.failed", {"request_id": req.request_id, "stage": "resolve", "code": decision.reason_code, "details": decision.message})
            return ActionOutcome(request=req, policy=decision)

        # attach resolved ids
        req.device_id = device.device_id
        req.room_id = device.room_id

        # 2) capability check (very simple for Milestone 3)
        capability_ok = self._capability_ok(req, device.capabilities)

        # 3) slot check (very simple for Milestone 3)
        slots_ok = self._slots_ok(req)

        # 4) rate limit
        rate_key = f"{req.intent_name}:{device.device_id}"
        rate = self.rate_limiter.check(rate_key)
        rate_limited = rate.limited

        # 5) auth
        # DeviceManager sets req.auth_level based on current auth window state (PIN/PTT)
        st = self.auth_window.get_state()
        req.auth_level = st.auth_level
        auth_granted = st.is_valid()

        # 6) policy decision
        decision = self.policy.decide(
            req,
            offline_only=self.offline_only,
            device_known=True,
            capability_ok=capability_ok,
            slots_ok=slots_ok,
            rate_limited=rate_limited,
            auth_granted=auth_granted,
        )
        self._audit_policy(req, decision)
        self._emit("action.policy_decided", {"request_id": req.request_id, "decision": asdict(decision)})

        if not decision.allowed:
            self._emit("action.failed", {"request_id": req.request_id, "stage": "policy", "code": decision.reason_code, "details": decision.message})
            return ActionOutcome(request=req, policy=decision)

        # 7) execute via driver
        driver = self.drivers.get(device.driver_kind)
        if not driver:
            exec_result = DriverResult(ok=False, driver_code="ERR_UNREACHABLE", details=f"No driver registered for kind '{device.driver_kind}'")
            self._audit_exec(req, device.device_id, exec_result)
            self._emit("action.executed", {"request_id": req.request_id, "driver_result": asdict(exec_result)})
            self._emit("action.failed", {"request_id": req.request_id, "stage": "execute", "code": exec_result.driver_code, "details": exec_result.details})
            return ActionOutcome(request=req, policy=decision, execution_result=asdict(exec_result))

        exec_result = driver.execute(device, req)
        self._audit_exec(req, device.device_id, exec_result)
        self._emit("action.executed", {"request_id": req.request_id, "driver_result": asdict(exec_result)})

        # 8) verify (best effort)
        state = None
        try:
            state = driver.read_state(device)
        except Exception:
            state = None

        ver = self.verifier.verify(req, exec_result, state=state)
        self._audit_verify(req, ver.__dict__)
        self._emit("action.verified", {"request_id": req.request_id, "verification": ver.__dict__})

        return ActionOutcome(
            request=req,
            policy=decision,
            execution_result=asdict(exec_result),
            verification_result=ver.__dict__,
        )

    # -------------------------
    # Helpers
    # -------------------------

    def _emit(self, topic: str, payload: Dict[str, Any]) -> None:
        try:
            # EventBus already has a (topic, data, ts) style event.
            # We'll standardize payload shape without refactoring bus.
            self.bus.publish(topic, payload)
        except Exception:
            pass

    def _capability_ok(self, req: ActionRequest, caps: Dict[str, Any]) -> bool:
        # Map intents to capability requirements
        if req.intent_name in ("device.set_power", "device.toggle"):
            return bool(caps.get("power", False))
        if req.intent_name == "device.set_level":
            return bool(caps.get("level", False))
        return True

    def _slots_ok(self, req: ActionRequest) -> bool:
        # Minimal checks
        if req.intent_name == "device.set_power":
            return "state" in req.slots or "power" in req.slots or "enabled" in req.slots
        if req.intent_name == "device.set_level":
            return "level" in req.slots
        return True

    def _audit_policy(self, req: ActionRequest, decision: PolicyDecision) -> None:
        self.audit.write(
            event_type="action.policy_decided",
            request_id=req.request_id,
            summary=f"{decision.reason_code} allowed={decision.allowed}",
            record={"request": asdict(req), "decision": asdict(decision)},
        )

    def _audit_exec(self, req: ActionRequest, device_id: str, exec_result: DriverResult) -> None:
        self.audit.write(
            event_type="action.executed",
            request_id=req.request_id,
            summary=f"{exec_result.driver_code} ok={exec_result.ok} device={device_id}",
            record={"request": asdict(req), "device_id": device_id, "driver_result": asdict(exec_result)},
        )

    def _audit_verify(self, req: ActionRequest, verification: Dict[str, Any]) -> None:
        self.audit.write(
            event_type="action.verified",
            request_id=req.request_id,
            summary=f"verified={verification.get('verified')} method={verification.get('method')}",
            record={"request": asdict(req), "verification": verification},
        )