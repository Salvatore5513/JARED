from __future__ import annotations

from typing import Optional
import requests

from core.net.policy import NetPolicy

# Policy is injected at boot; fallback preserves old behavior.
_policy: Optional[NetPolicy] = None


def configure(policy: NetPolicy) -> None:
    """
    Inject the single NetPolicy instance created during boot.
    This prevents hidden second instances of policy.
    """
    global _policy
    _policy = policy


def _get_policy() -> NetPolicy:
    global _policy
    if _policy is None:
        raise RuntimeError(
            "http_client not configured. Call http_client.configure(net_policy) during boot."
        )
    return _policy


def get(url: str, **kwargs):
    _get_policy().check_outbound(url)
    return requests.get(url, **kwargs)


def post(url: str, **kwargs):
    _get_policy().check_outbound(url)
    return requests.post(url, **kwargs)