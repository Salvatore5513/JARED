from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np
import sounddevice as sd

from audio.capture import start_level_meter, LevelReading
from audio.ducking import DuckingParams, DuckingState


@dataclass
class DuckingTestConfig:
    input_device_index: int | None
    output_device_index: int | None
    samplerate: int = 48000
    channels_out: int = 2


class DuckingTestRunner:
    def __init__(self, cfg: DuckingTestConfig, params: DuckingParams):
        self.cfg = cfg
        self.duck = DuckingState(params)

        self._out: sd.OutputStream | None = None
        self._in: sd.InputStream | None = None

        self._phase = 0.0
        self._last_t = time.time()
        self._last_level_print = 0.0
        self._latest_rms_db = -120.0

    def _music_block(self, frames: int) -> np.ndarray:
        """
        Simple 'music' placeholder: two sines.
        Replace later with real music buffer.
        """
        sr = self.cfg.samplerate
        t = (np.arange(frames, dtype=np.float32) + self._phase) / sr

        # Two-tone "music" so you can hear ducking clearly
        a = np.sin(2.0 * math.pi * 220.0 * t)
        b = 0.6 * np.sin(2.0 * math.pi * 330.0 * t)
        mono = (a + b) * 0.6  # base level

        self._phase += frames

        stereo = np.column_stack([mono, mono]).astype(np.float32)
        return stereo

    def _out_callback(self, outdata, frames, time_info, status):  # noqa: ANN001
        now = time.time()
        dt = max(1e-3, now - self._last_t)
        self._last_t = now

        gain = self.duck.step(dt)
        block = self._music_block(frames)
        outdata[:] = block * gain

        # occasional console status (not too spammy)
        if now - self._last_level_print > 0.25:
            self._last_level_print = now
            speech = "YES" if self.duck.speech else "no"
            print(
                f"\rRMS {self._latest_rms_db:6.1f} dB | speech {speech:>3} | gain {gain:0.2f}      ",
                end="",
                flush=True,
            )

    def _on_level(self, reading: LevelReading) -> None:
        self._latest_rms_db = reading.rms_db
        self.duck.update_speech_from_rms_db(reading.rms_db)

    def start(self) -> None:
        self._last_t = time.time()

        self._out = sd.OutputStream(
            device=self.cfg.output_device_index,
            channels=self.cfg.channels_out,
            samplerate=self.cfg.samplerate,
            dtype="float32",
            callback=self._out_callback,
            blocksize=1024,
        )
        self._out.start()

        self._in = start_level_meter(
            device_index=self.cfg.input_device_index,
            samplerate=self.cfg.samplerate,
            channels=1,
            blocksize=1024,
            on_level=self._on_level,
        )

    def stop(self) -> None:
        for s in (self._in, self._out):
            if s:
                try:
                    s.stop()
                    s.close()
                except Exception:
                    pass
