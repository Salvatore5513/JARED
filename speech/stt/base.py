from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol, Optional
import numpy as np


@dataclass(frozen=True)
class Transcript:
    text: str
    confidence: float = 1.0
    is_final: bool = True


class SpeechToTextEngine(Protocol):
    name: str

    def start(self) -> None: ...
    def stop(self) -> None: ...

    def transcribe_once(self, audio: Optional[np.ndarray] = None) -> Transcript:
        """Blocking one-shot transcription (after wake)."""
        ...
