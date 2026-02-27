# app/runtime.py
from __future__ import annotations

from dataclasses import dataclass
from speech.pipeline import VoicePipeline

@dataclass
class Runtime:
    voice: VoicePipeline

    def run_forever(self) -> None:
        self.voice.run_forever()