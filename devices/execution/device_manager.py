from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional
import time

from core.event_bus import EventBus
from core.security.audit_log import AuditLog
from core.security.rate_limits import RateLimiter
from core.security.policy_engine import PolicyEngine
from core.security.auth.auth_window import AuthWindow
from core.contracts.action_request import (
    ActionRequest,
    ActionOutcome,
    PolicyDecision,
    AuthLevel,
)
from devices.execution.verifier import Verifier
from devices.registry.models import DeviceTarget, DeviceRecord
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
        self._emit(
            "action.requested",
            self._base_payload(
                req=req,
                target=target,
                stage="requested",
            ),
        )

        matches = self.registry.resolve_candidates(target)

        if len(matches) > 1:
            options = [f"{d.room_id}:{d.name}" for d in matches]
            message = f"I found multiple matches for {target.device_name}. Which one did you mean?"

            decision = PolicyDecision(
                allowed=False,
                reason_code="AMBIGUOUS_DEVICE",
                message=message,
                required_auth=AuthLevel.NONE,
                requires_verification=False,
            )

            self._audit_policy(req, decision)
            self._emit(
                "action.failed",
                self._base_payload(
                    req=req,
                    target=target,
                    stage="resolve",
                    code="AMBIGUOUS_DEVICE",
                    details=message,
                    candidates=options,
                ),
            )
            return ActionOutcome(request=req, policy=decision)

        device = matches[0] if matches else None
        if not device:
            decision = self.policy.decide(req, offline_only=self.offline_only, device_known=False)
            self._audit_policy(req, decision)
            self._emit(
                "action.failed",
                self._base_payload(
                    req=req,
                    target=target,
                    stage="resolve",
                    code=decision.reason_code,
                    details=decision.message,
                ),
            )
            return ActionOutcome(request=req, policy=decision)

        capability_ok = self._capability_ok(req, device.capabilities)
        slots_ok = self._slots_ok(req)

        rate_key = f"{req.intent_name}:{device.device_id}"
        rate = self.rate_limiter.check(rate_key)
        rate_limited = rate.limited

        st = self.auth_window.get_state()
        auth_granted = st.is_valid()

        req2 = ActionRequest(
            request_id=req.request_id,
            ts_ms=req.ts_ms,
            intent_name=req.intent_name,
            slots=req.slots,
            source=req.source,
            confidence=req.confidence,
            safety_class=req.safety_class,
            auth_level=st.auth_level,
            device_id=device.device_id,
            room_id=device.room_id,
            requires_verification=req.requires_verification,
        )

        decision = self.policy.decide(
            req2,
            offline_only=self.offline_only,
            device_known=True,
            capability_ok=capability_ok,
            slots_ok=slots_ok,
            rate_limited=rate_limited,
            retry_in_ms=rate.retry_in_ms,
            auth_granted=auth_granted,
        )
        self._audit_policy(req2, decision)
        self._emit(
            "action.policy_decided",
            self._base_payload(
                req=req2,
                target=target,
                device=device,
                stage="policy",
                decision=asdict(decision),
            ),
        )

        if not decision.allowed:
            self._emit(
                "action.failed",
                self._base_payload(
                    req=req2,
                    target=target,
                    device=device,
                    stage="policy",
                    code=decision.reason_code,
                    details=decision.message,
                    decision=asdict(decision),
                ),
            )
            return ActionOutcome(request=req2, policy=decision)

        verification_default = {
            "verified": True,
            "method": "none",
            "details": "Verification not required.",
            "state": None,
        }

        driver = self.drivers.get(device.driver_kind)
        if not driver:
            exec_result = DriverResult(
                ok=False,
                driver_code="NO_DRIVER",
                details="No driver registered",
            )
            latency_ms = 0

            self._audit_exec(req2, device.device_id, exec_result, latency_ms)
            self._emit(
                "action.executed",
                self._base_payload(
                    req=req2,
                    target=target,
                    device=device,
                    stage="execute",
                    latency_ms=latency_ms,
                    driver_result=asdict(exec_result),
                ),
            )
            self._emit(
                "action.failed",
                self._base_payload(
                    req=req2,
                    target=target,
                    device=device,
                    stage="execute",
                    code=exec_result.driver_code,
                    details=exec_result.details,
                    latency_ms=latency_ms,
                    driver_result=asdict(exec_result),
                ),
            )
            return ActionOutcome(
                request=req2,
                policy=decision,
                execution_result=asdict(exec_result),
                verification_result=verification_default,
            )

        started = time.perf_counter()
        exec_result = driver.execute(device, req2)
        latency_ms = int((time.perf_counter() - started) * 1000)

        self._audit_exec(req2, device.device_id, exec_result, latency_ms)
        self._emit(
            "action.executed",
            self._base_payload(
                req=req2,
                target=target,
                device=device,
                stage="execute",
                latency_ms=latency_ms,
                driver_result=asdict(exec_result),
            ),
        )

        state = None
        try:
            state = driver.read_state(device)
        except Exception:
            state = None

        ver = self.verifier.verify(
            req2,
            exec_result,
            requires_verification=decision.requires_verification,
            state=state,
        )
        self._audit_verify(req2, ver.__dict__)
        self._emit(
            "action.verified",
            self._base_payload(
                req=req2,
                target=target,
                device=device,
                stage="verify",
                latency_ms=latency_ms,
                driver_result=asdict(exec_result),
                verification=ver.__dict__,
            ),
        )

        if decision.requires_verification and not ver.verified:
            self._emit(
                "action.failed",
                self._base_payload(
                    req=req2,
                    target=target,
                    device=device,
                    stage="verify",
                    code="VERIFY_FAILED",
                    details=(
                        f"Verification required by policy "
                        f"(auth={decision.required_auth.name}) but did not verify"
                    ),
                    latency_ms=latency_ms,
                    driver_result=asdict(exec_result),
                    verification=ver.__dict__,
                    decision=asdict(decision),
                ),
            )
            return ActionOutcome(
                request=req2,
                policy=decision,
                execution_result=asdict(exec_result),
                verification_result=ver.__dict__,
            )

        return ActionOutcome(
            request=req2,
            policy=decision,
            execution_result=asdict(exec_result),
            verification_result=ver.__dict__,
        )

    def _base_payload(
        self,
        *,
        req: ActionRequest,
        target: DeviceTarget,
        stage: str,
        device: DeviceRecord | None = None,
        **extra: Any,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "request_id": req.request_id,
            "stage": stage,
            "request": asdict(req),
            "target": asdict(target),
            "intent_name": req.intent_name,
            "source": req.source,
        }

        request_device_id = req.device_id or ""
        request_room_id = req.room_id or ""
        target_device_id = target.device_id or ""
        target_room_id = target.room_id or ""

        device_id = ""
        room_id = ""
        device_name = ""
        driver_kind = ""

        if device is not None:
            device_id = device.device_id
            room_id = device.room_id
            device_name = device.name
            driver_kind = device.driver_kind
        else:
            device_id = request_device_id or target_device_id
            room_id = request_room_id or target_room_id

        if device_id:
            payload["device_id"] = device_id
        if room_id:
            payload["room_id"] = room_id
        if device_name:
            payload["device_name"] = device_name
        if driver_kind:
            payload["driver_kind"] = driver_kind

        payload.update(extra)
        return payload

    def _emit(self, topic: str, payload: Dict[str, Any]) -> None:
        try:
            self.bus.publish(topic, **payload)
        except Exception:
            pass

    def _capability_ok(self, req: ActionRequest, caps: Dict[str, Any]) -> bool:
        if req.intent_name in ("device.set_power", "device.toggle"):
            return bool(caps.get("power", False))
        if req.intent_name == "device.set_level":
            return bool(caps.get("level", False))
        return True

    def _slots_ok(self, req: ActionRequest) -> bool:
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

    def _audit_exec(
        self,
        req: ActionRequest,
        device_id: str,
        exec_result: DriverResult,
        latency_ms: int | None = None,
    ) -> None:
        summary = f"{exec_result.driver_code} ok={exec_result.ok} device={device_id}"
        if latency_ms is not None:
            summary += f" latency_ms={latency_ms}"

        record = {
            "request": asdict(req),
            "device_id": device_id,
            "driver_result": asdict(exec_result),
        }
        if latency_ms is not None:
            record["latency_ms"] = latency_ms

        self.audit.write(
            event_type="action.executed",
            request_id=req.request_id,
            summary=summary,
            record=record,
        )

    def _audit_verify(self, req: ActionRequest, verification: Dict[str, Any]) -> None:
        self.audit.write(
            event_type="action.verified",
            request_id=req.request_id,
            summary=f"verified={verification.get('verified')} method={verification.get('method')}",
            record={"request": asdict(req), "verification": verification},
        )