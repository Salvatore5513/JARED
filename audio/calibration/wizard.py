from __future__ import annotations

import time
from dataclasses import dataclass

from audio.capture import start_level_meter, LevelReading


@dataclass
class CalibrationResult:
    noise_rms_db: float
    speech_rms_db: float
    recommended_threshold_db: float
    recommended_hysteresis_db: float


def _sample_rms_db(device_index: int | None, seconds: float, samplerate: int = 48000) -> list[float]:
    readings: list[float] = []

    def on_level(r: LevelReading) -> None:
        readings.append(r.rms_db)

    stream = start_level_meter(
        device_index=device_index,
        samplerate=samplerate,
        channels=1,
        blocksize=1024,
        on_level=on_level,
    )

    t0 = time.time()
    try:
        while time.time() - t0 < seconds:
            time.sleep(0.05)
    finally:
        try:
            stream.stop()
            stream.close()
        except Exception:
            pass

    return readings


def _robust_mean(values: list[float]) -> float:
    if not values:
        return -120.0
    s = sorted(values)
    # Trim 10% on each side to reduce spikes
    k = max(1, int(0.1 * len(s)))
    core = s[k:-k] if len(s) > 2 * k else s
    return sum(core) / len(core)


def run_basic_calibration(device_index: int | None, samplerate: int = 48000) -> CalibrationResult:
    print("\nCALIBRATION STEP 1/2: Stay quiet (measuring noise floor) ...")
    noise_vals = _sample_rms_db(device_index, seconds=4.0, samplerate=samplerate)
    noise_db = _robust_mean(noise_vals)
    print(f"  Noise RMS ~ {noise_db:.1f} dB")

    print("\nCALIBRATION STEP 2/2: Speak normally for 5 seconds ...")
    speech_vals = _sample_rms_db(device_index, seconds=5.0, samplerate=samplerate)
    speech_db = _robust_mean(speech_vals)
    print(f"  Speech RMS ~ {speech_db:.1f} dB")

    # Recommend threshold between noise and speech.
    # If noise is unusually high (AGC), still make threshold a bit above noise.
    gap = speech_db - noise_db  # (less negative) - (more negative) => positive-ish if speech louder
    if gap < 6.0:
        # not much separation; be conservative
        thr = noise_db + 3.0
    else:
        thr = noise_db + max(4.0, min(10.0, gap * 0.35))

    # Hysteresis: 4-8 dB typical
    hyst = 5.0 if gap >= 10.0 else 4.0

    return CalibrationResult(
        noise_rms_db=noise_db,
        speech_rms_db=speech_db,
        recommended_threshold_db=float(thr),
        recommended_hysteresis_db=float(hyst),
    )
