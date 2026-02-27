from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.config.manager import load_config
from core.net.policy import NetPolicy
from core.security.policy_engine import PolicyEngine, PolicyConfig


@dataclass(frozen=True)
class Policies:
    """
    Single source of truth for all policy gates.
    Construct once at boot; inject everywhere else.
    """
    net: NetPolicy
    device: PolicyEngine

    @classmethod
    def from_env(cls) -> "Policies":
        cfg = load_config()

        # Put audits under data_dir if your config provides it; otherwise fallback.
        audit_dir = getattr(cfg, "data_dir", None)
        audit_file = Path(audit_dir) / "audit" / "netpolicy_audit.log" if audit_dir else None

        net = NetPolicy(audit_file=audit_file, config=cfg)
        device = PolicyEngine(PolicyConfig())  # keep yours intact
        return cls(net=net, device=device)