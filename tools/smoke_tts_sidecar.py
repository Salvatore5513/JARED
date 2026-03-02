from __future__ import annotations

from speech.tts.base import TTSRequest
from speech.tts.engines.xtts_sidecar_client import XTTSSidecarClient
from speech.tts.renderer import TTSRenderer

import sounddevice as sd
import soundfile as sf


def main() -> None:
    engine = XTTSSidecarClient()
    renderer = TTSRenderer(engine)
    renderer.warmup()

    res = renderer.render(TTSRequest(text="JARED voice online."))
    data, sr = sf.read(res.wav_path, dtype="float32", always_2d=True)

    # Ensure stereo output
    if data.shape[1] == 1:
        data = data.repeat(2, axis=1)

    sd.play(data, sr)
    sd.wait()

    print("Spoke from:", res.wav_path)


if __name__ == "__main__":
    main()