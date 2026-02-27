from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PinConfig:
    pin: str = "1234"  # CHANGE THIS in your local config later


class PinVerifier:
    """
    Milestone 3: simple local PIN check.
    Later milestones: hash + rate limit + lockout.
    """

    def __init__(self, config: PinConfig):
        self.config = config

    def verify(self, pin_input: str) -> bool:
        if pin_input is None:
            return False
        return str(pin_input).strip() == str(self.config.pin).strip()