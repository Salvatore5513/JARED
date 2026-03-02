from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

_TTS = None
_TTS_MODEL_NAME = None
_TTS_DEVICE = None

DEFAULT_MODEL = "tts_models/multilingual/multi-dataset/xtts_v2"
DEFAULT_SPEAKER_WAV = os.environ.get("JARED_TTS_SPEAKER_WAV", "data/voices/jared.wav")


def _load_tts(device: str, model_name: str):
    global _TTS, _TTS_MODEL_NAME, _TTS_DEVICE
    if _TTS is None or _TTS_MODEL_NAME != model_name or _TTS_DEVICE != device:
        from TTS.api import TTS
        _TTS = TTS(model_name).to(device)
        _TTS_MODEL_NAME = model_name
        _TTS_DEVICE = device
    return _TTS


class SpeakRequest(BaseModel):
    text: str
    language: str = "en"
    device: str = "cuda"
    model_name: str = DEFAULT_MODEL
    speaker_wav_path: Optional[str] = None  # optional override


class SpeakResponse(BaseModel):
    wav_path: str


app = FastAPI()

OUT_DIR = Path(os.environ.get("JARED_TTS_OUT_DIR", "data/tts_sidecar_out"))
OUT_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health():
    return {"ok": True, "model": _TTS_MODEL_NAME, "device": _TTS_DEVICE, "default_speaker": DEFAULT_SPEAKER_WAV}


@app.post("/speak", response_model=SpeakResponse)
def speak(req: SpeakRequest):
    tts = _load_tts(req.device, req.model_name)
    out_wav = OUT_DIR / f"tts_{uuid.uuid4().hex}.wav"

    # XTTS needs a reference speaker wav. Use override if provided, else default.
    speaker_wav = req.speaker_wav_path or DEFAULT_SPEAKER_WAV
    if not Path(speaker_wav).exists():
        raise HTTPException(
            status_code=400,
            detail=f"speaker_wav not found. Provide speaker_wav_path or create default at: {speaker_wav}",
        )

    tts.tts_to_file(
        text=req.text,
        file_path=str(out_wav),
        language=req.language,
        speaker_wav=speaker_wav,
    )
    return SpeakResponse(wav_path=str(out_wav))


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8755)