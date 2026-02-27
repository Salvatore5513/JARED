from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class PTTState:
    pressed: bool = False


class PTTManager:
    """
    Milestone 3: just track whether PTT is pressed.
    Your real PTT input (keyboard GPIO, stream deck, etc.) can update this.
    """

    def __init__(self):
        self._state = PTTState(pressed=False)

    def set_pressed(self, pressed: bool) -> None:
        self._state.pressed = bool(pressed)

    def is_pressed(self) -> bool:
        return self._state.pressed