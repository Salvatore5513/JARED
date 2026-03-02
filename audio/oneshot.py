from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import sounddevice as sd


def _decode_pcm(raw: bytes, channels: int, sampwidth: int) -> np.ndarray:
    # Same decoding logic as audio.wav_player.WavPlayer
    if sampwidth == 2:
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        x = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif sampwidth == 3:
        b = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3)
        v = (b[:, 0].astype(np.int32) |
             (b[:, 1].astype(np.int32) << 8) |
             (b[:, 2].astype(np.int32) << 16))
        v = (v << 8) >> 8  # sign extend 24->32
        x = v.astype(np.float32) / 8388608.0
    else:
        raise ValueError(f"Unsupported WAV sampwidth: {sampwidth} bytes")

    return x.reshape(-1, channels)


def load_wav_float32(path: str | Path) -> tuple[np.ndarray, int]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))

    with wave.open(str(p), "rb") as wf:
        channels = wf.getnchannels()
        sr = wf.getframerate()
        sampwidth = wf.getsampwidth()
        frames = wf.getnframes()
        raw = wf.readframes(frames)

    data = _decode_pcm(raw, channels, sampwidth)  # (frames, ch)
    return data, sr


@dataclass
class OneShotPlayer:
    output_device_index: int | None = None

    def play_wav(self, wav_path: str) -> None:
        data, sr = load_wav_float32(wav_path)

        # Ensure stereo output (your system assumes 2ch a lot)
        if data.shape[1] == 1:
            data = np.repeat(data, 2, axis=1)

        sd.play(data, sr, device=self.output_device_index)
        sd.wait()