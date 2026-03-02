from __future__ import annotations

from dataclasses import dataclass
from speech.tts.base import TTSEngine, TTSRequest, TTSResult


@dataclass
class TTSRenderer:
    engine: TTSEngine

    def warmup(self) -> None:
        self.engine.warmup()

    def render(self, req: TTSRequest) -> TTSResult:
        # out_wav_path not used by sidecar (it returns its own file path)
        return self.engine.synthesize_to_wav(req, out_wav_path="")