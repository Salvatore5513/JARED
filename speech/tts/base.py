from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol


@dataclass(frozen=True)
class TTSRequest:
    text: str
    voice_id: str = "default"
    language: str = "en"
    speaker_wav_path: Optional[str] = None


@dataclass(frozen=True)
class TTSResult:
    wav_path: str
    samplerate: int


class TTSEngine(Protocol):
    name: str
    def warmup(self) -> None: ...
    def synthesize_to_wav(self, req: TTSRequest, out_wav_path: str) -> TTSResult: ...