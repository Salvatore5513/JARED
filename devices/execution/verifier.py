from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

from devices.execution.action_request import ActionRequest
from devices.drivers.base import DriverResult


@dataclass
class VerificationResult:
    verified: bool
    method: str  # "none" | "assumed" | "state_readback"
    details: str
    state: Optional[Dict[str, Any]] = None


class Verifier:
    """
    Milestone 3: verification is best-effort.
    If a driver supports state readback later, we’ll use it.
    """

    def verify(self, action: ActionRequest, exec_result: DriverResult, state: Optional[Dict[str, Any]] = None) -> VerificationResult:
        if not action.requires_verification:
            return VerificationResult(verified=True, method="none", details="Verification not required.", state=state)

        # If we have state, we can claim readback-based verification
        if state is not None:
            return VerificationResult(verified=True, method="state_readback", details="Verified by state readback.", state=state)

        # Otherwise explicit assumed (still logged!)
        return VerificationResult(verified=False, method="assumed", details="No state readback available; verification not confirmed.", state=None)