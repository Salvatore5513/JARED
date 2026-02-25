from __future__ import annotations

import time
from dataclasses import dataclass

import sounddevice as sd

from audio.capture import start_level_meter, LevelReading
from audio.ducking import DuckingParams, DuckingState
from audio.wav_player import WavPlayer


@dataclass
class PlaybackConfig:
    input_device_index: int | None
    output_device_index: int | None
    samplerate: int = 48000
    out_channels: int = 2
    music_volume: float = 1.0


class MusicPlayback:
    """
    Plays a WAV file (looping) and applies ducking based on mic RMS.
    """
    def __init__(self, cfg: PlaybackConfig, duck_params: DuckingParams, wav_path: str):
        self.cfg = cfg
        self.duck = DuckingState(duck_params)
        self.wav = WavPlayer(wav_path)

        self._out: sd.OutputStream | None = None
        self._in: sd.InputStream | None = None

        self._last_t = time.time()
        self._latest_rms_db = -120.0
        self._last_print = 0.0

    def _on_level(self, reading: LevelReading) -> None:
        self._latest_rms_db = reading.rms_db
        self.duck.update_speech_from_rms_db(reading.rms_db)

    def _out_callback(self, outdata, frames, time_info, status):  # noqa: ANN001
        now = time.time()
        dt = max(1e-3, now - self._last_t)
        self._last_t = now

        gain = self.duck.step(dt)
        block = self.wav.get_block(frames, out_channels=self.cfg.out_channels)

        outdata[:] = block * float(self.cfg.music_volume) * gain

        if now - self._last_print > 0.25:
            self._last_print = now
            speech = "YES" if self.duck.speech else "no"
            print(
                f"\rRMS {self._latest_rms_db:6.1f} dB | speech {speech:>3} | gain {gain:0.2f} | music {self.cfg.music_volume:0.2f}   ",
                end="",
                flush=True,
            )

    def start(self) -> None:
        info = self.wav.info()
        if info.samplerate != self.cfg.samplerate:
            raise RuntimeError(
                f"WAV samplerate {info.samplerate} != configured {self.cfg.samplerate}. "
                f"Use a {self.cfg.samplerate} Hz PCM WAV (recommended 48000)."
            )

        self._last_t = time.time()

        self._out = sd.OutputStream(
            device=self.cfg.output_device_index,
            channels=self.cfg.out_channels,
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
