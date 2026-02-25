from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import sounddevice as sd


@dataclass(frozen=True)
class LevelReading:
    rms: float          # linear 0..1-ish (depends on input gain)
    peak: float         # linear
    rms_db: float       # dBFS-ish (relative)
    peak_db: float      # dBFS-ish (relative)


def _lin_to_db(x: float, floor_db: float = -120.0) -> float:
    # Avoid -inf
    if x <= 1e-12:
        return floor_db
    return float(20.0 * np.log10(x))


def start_level_meter(
    *,
    device_index: int | None,
    samplerate: int = 48000,
    channels: int = 1,
    blocksize: int = 1024,
    on_level: Callable[[LevelReading], None],
) -> sd.InputStream:
    """
    Starts a non-blocking level meter. Caller must keep the stream alive.
    """

    def callback(indata, frames, time, status):  # noqa: ANN001
        if status:
            # Don't print here; caller decides what to do
            pass

        # indata shape: (frames, channels)
        x = np.asarray(indata, dtype=np.float32)

        # Mixdown to mono for level
        if x.ndim == 2 and x.shape[1] > 1:
            x_mono = np.mean(x, axis=1)
        else:
            x_mono = x.reshape(-1)

        rms = float(np.sqrt(np.mean(np.square(x_mono))) + 1e-12)
        peak = float(np.max(np.abs(x_mono)) + 1e-12)

        reading = LevelReading(
            rms=rms,
            peak=peak,
            rms_db=_lin_to_db(rms),
            peak_db=_lin_to_db(peak),
        )
        on_level(reading)

    stream = sd.InputStream(
        device=device_index,
        channels=channels,
        samplerate=samplerate,
        blocksize=blocksize,
        dtype="float32",
        callback=callback,
    )
    stream.start()
    return stream
