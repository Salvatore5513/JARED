import numpy as np
import wave

sr = 48000
duration = 20  # seconds
t = np.linspace(0, duration, sr * duration, False)

a = 0.4 * np.sin(2 * np.pi * 220 * t)
b = 0.3 * np.sin(2 * np.pi * 330 * t)
c = 0.2 * np.sin(2 * np.pi * 440 * t)

mono = a + b + c
stereo = np.column_stack([mono, mono])

out_path = "music_48k.wav"
with wave.open(out_path, "wb") as wf:
    wf.setnchannels(2)
    wf.setsampwidth(2)
    wf.setframerate(sr)
    wf.writeframes((stereo * 32767).astype("int16").tobytes())

print(f"Generated {out_path} (48kHz, 16-bit, stereo, {duration}s)")
