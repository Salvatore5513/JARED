from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class WavInfo:
    channels: int
    samplerate: int
    sampwidth: int
    frames: int


class WavPlayer:
    """
    Loads a PCM WAV file and serves looping float32 blocks in [-1, 1].
    Supported: 16-bit, 24-bit packed, 32-bit PCM.
    """
    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(self.path)

        with wave.open(str(self.path), "rb") as wf:
            self.channels = wf.getnchannels()
            self.samplerate = wf.getframerate()
            self.sampwidth = wf.getsampwidth()
            self.frames = wf.getnframes()
            raw = wf.readframes(self.frames)

        self._data = self._decode_pcm(raw, self.channels, self.sampwidth)  # (frames, ch)
        self._pos = 0

    def info(self) -> WavInfo:
        return WavInfo(
            channels=self.channels,
            samplerate=self.samplerate,
            sampwidth=self.sampwidth,
            frames=self.frames,
        )

    def get_block(self, frames: int, out_channels: int = 2) -> np.ndarray:
        data = self._data
        n = data.shape[0]
        idx = (np.arange(frames) + self._pos) % n
        block = data[idx, :]
        self._pos = (self._pos + frames) % n

        # Mix/upmix to out_channels
        if block.shape[1] == out_channels:
            return block.astype(np.float32)

        if out_channels == 1:
            mono = np.mean(block, axis=1, keepdims=True)
            return mono.astype(np.float32)

        if block.shape[1] == 1 and out_channels == 2:
            stereo = np.repeat(block, 2, axis=1)
            return stereo.astype(np.float32)

        if block.shape[1] > out_channels:
            return block[:, :out_channels].astype(np.float32)

        reps = int(np.ceil(out_channels / block.shape[1]))
        expanded = np.tile(block, (1, reps))[:, :out_channels]
        return expanded.astype(np.float32)

    @staticmethod
    def _decode_pcm(raw: bytes, channels: int, sampwidth: int) -> np.ndarray:
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
