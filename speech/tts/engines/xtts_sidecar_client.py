from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from speech.tts.base import TTSEngine, TTSRequest, TTSResult


@dataclass
class XTTSSidecarClient(TTSEngine):
    """
    JARED-side TTSEngine adapter.
    Calls the local XTTS sidecar service and returns the WAV path it generated.
    """
    base_url: str = "http://127.0.0.1:8755"
    device: str = "cuda"
    model_name: str = "tts_models/multilingual/multi-dataset/xtts_v2"

    def __post_init__(self) -> None:
        self.name = "xtts_sidecar"

    def warmup(self) -> None:
        _ = self._get("/health")

    def synthesize_to_wav(self, req: TTSRequest, out_wav_path: str) -> TTSResult:
        payload = {
            "text": req.text,
            "language": req.language,
            "device": self.device,
            "model_name": self.model_name,
            "speaker_wav_path": req.speaker_wav_path,
        }
        resp = self._post("/speak", payload)
        return TTSResult(wav_path=resp["wav_path"], samplerate=0)

    def _get(self, path: str) -> dict:
        with urllib.request.urlopen(self.base_url + path, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))

    def _post(self, path: str, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.base_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # First XTTS call can take a while (model load). Keep generous timeout.
        with urllib.request.urlopen(req, timeout=300) as r:
            return json.loads(r.read().decode("utf-8"))