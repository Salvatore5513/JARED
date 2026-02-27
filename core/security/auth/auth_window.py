from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import time

from devices.execution.action_request import AuthLevel


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class AuthState:
    auth_level: AuthLevel = AuthLevel.NONE
    valid_until_ms: int = 0
    method: Optional[str] = None  # "ptt" or "pin" or None
    last_granted_ts_ms: int = 0

    def is_valid(self, now_ms: Optional[int] = None) -> bool:
        now = now_ms if now_ms is not None else _now_ms()
        return now < self.valid_until_ms and self.auth_level != AuthLevel.NONE


class AuthWindow:
    """
    Manages short-lived authorization grants.
    - PTT grants are typically very short (while pressed)
    - PIN grants create a time window (e.g., 60 seconds)
    """

    def __init__(self, *, default_window_ms: int = 60_000):
        self.default_window_ms = int(default_window_ms)
        self._state = AuthState()

    def get_state(self) -> AuthState:
        # Return a copy so callers can't mutate internal state accidentally
        s = self._state
        return AuthState(
            auth_level=s.auth_level,
            valid_until_ms=s.valid_until_ms,
            method=s.method,
            last_granted_ts_ms=s.last_granted_ts_ms,
        )

    def clear(self) -> None:
        self._state = AuthState()

    def grant_ptt(self, *, window_ms: int = 1_500, now_ms: Optional[int] = None) -> AuthState:
        """
        PTT is a short rolling window. You can call this repeatedly while pressed.
        """
        now = now_ms if now_ms is not None else _now_ms()
        self._state = AuthState(
            auth_level=AuthLevel.PTT,
            valid_until_ms=now + int(window_ms),
            method="ptt",
            last_granted_ts_ms=now,
        )
        return self.get_state()

    def grant_pin(self, *, window_ms: Optional[int] = None, now_ms: Optional[int] = None) -> AuthState:
        """
        PIN opens a longer window (default_window_ms unless overridden).
        """
        now = now_ms if now_ms is not None else _now_ms()
        dur = self.default_window_ms if window_ms is None else int(window_ms)
        self._state = AuthState(
            auth_level=AuthLevel.PIN,
            valid_until_ms=now + dur,
            method="pin",
            last_granted_ts_ms=now,
        )
        return self.get_state()

    def is_granted(self, required: AuthLevel, *, now_ms: Optional[int] = None) -> bool:
        """
        Returns True if current state meets required auth level within valid window.
        """
        state = self._state
        if not state.is_valid(now_ms=now_ms):
            return False

        if required == AuthLevel.NONE:
            return True
        if required == AuthLevel.PTT:
            return state.auth_level in (AuthLevel.PTT, AuthLevel.PIN)
        if required == AuthLevel.PIN:
            return state.auth_level == AuthLevel.PIN

        return False