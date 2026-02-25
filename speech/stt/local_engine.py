import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import numpy as np
import sounddevice as sd
from scipy.io import wavfile
from speech.stt.base import Transcript


def _repo_root() -> Path:
    # .../speech/stt/whispercpp_engine.py -> repo root is 3 parents up
    return Path(__file__).resolve().parents[2]


def _rms(x: np.ndarray) -> float:
    # x is float32 mono audio
    return float(np.sqrt(np.mean(np.square(x)))) if x.size else 0.0


@dataclass
class WhisperCppSTTEngine:
    """
    Records mic audio until it detects end-of-speech (silence),
    then calls whisper-cli.exe (CUDA build) and returns the transcript.
    """
    name: str = "whispercpp-cuda-stt"

    sample_rate: int = 16000
    block_ms: int = 50  # smaller = snappier VAD loop
    max_record_seconds: float = 10.0

    # Silence-stop behavior
    silence_rms_threshold: float = 0.010   # tune if needed
    silence_stop_ms: int = 900             # stop after this much silence post-speech
    min_speech_ms: int = 250               # require speech at least this long to accept

    language: str = "en"

    def __post_init__(self) -> None:
        self._running = False

        root = _repo_root()

        self._exe = root / "third_party" / "whispercpp_cuda" / "whisper-cli.exe"
        if not self._exe.exists():
            raise FileNotFoundError(f"whisper-cli.exe not found: {self._exe}")

        self._model = root / "third_party" / "whisper_models" / "ggml-small.en.bin"
        if not self._model.exists():
            raise FileNotFoundError(f"Whisper model not found: {self._model}")

        self._block = int(self.sample_rate * (self.block_ms / 1000.0))
        self._silence_blocks_needed = max(1, int(self.silence_stop_ms / self.block_ms))
        self._min_speech_blocks = max(1, int(self.min_speech_ms / self.block_ms))
        self._max_blocks = max(1, int((self.max_record_seconds * 1000) / self.block_ms))

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def transcribe_once(self, audio: Optional[np.ndarray] = None) -> Transcript:
        if not self._running:
            return Transcript(text="", confidence=0.0, is_final=True)

        import tempfile
        import wave

        def _read_wav_int16_mono(path: str) -> tuple[int, np.ndarray]:
            """Return (sample_rate, samples int16 mono)"""
            with wave.open(path, "rb") as wf:
                ch = wf.getnchannels()
                sr = wf.getframerate()
                sampwidth = wf.getsampwidth()
                nframes = wf.getnframes()
                frames = wf.readframes(nframes)

            if sampwidth != 2:
                raise ValueError(f"Expected 16-bit PCM wav, got sampwidth={sampwidth}")
            data = np.frombuffer(frames, dtype=np.int16)

            if ch == 1:
                return sr, data
            # downmix: take left channel
            return sr, data[0::ch]

        def _write_wav_int16_mono(path: str, sr: int, samples: np.ndarray) -> None:
            samples = np.asarray(samples, dtype=np.int16)
            with wave.open(path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # int16
                wf.setframerate(sr)
                wf.writeframes(samples.tobytes())

        wav_path = self._record_until_silence()
        combined_path: Optional[str] = None

        try:
            # If we got pre-roll audio from the wake engine, prepend it.
            if audio is not None and isinstance(audio, np.ndarray) and audio.size > 0:
                try:
                    rec_sr, rec = _read_wav_int16_mono(wav_path)

                    # Only prepend if sample rate matches what wake uses (16000).
                    # If your recorder uses a different sr, we skip pre-roll safely.
                    if rec_sr == 16000:
                        pre = np.asarray(audio, dtype=np.int16).reshape(-1)
                        merged = np.concatenate([pre, rec])

                        fd, combined_path = tempfile.mkstemp(suffix=".wav", prefix="jared_preroll_")
                        # close fd; wave will open by path
                        os.close(fd)

                        _write_wav_int16_mono(combined_path, rec_sr, merged)
                        wav_to_transcribe = combined_path
                    else:
                        wav_to_transcribe = wav_path
                except Exception:
                    # If anything goes weird, fall back to normal behavior
                    wav_to_transcribe = wav_path
            else:
                wav_to_transcribe = wav_path

            text = self._run_whisper(wav_to_transcribe).strip()
            text = " ".join(text.split())
            return Transcript(text=text, confidence=0.85 if text else 0.0, is_final=True)

        finally:
            try:
                os.remove(wav_path)
            except OSError:
                pass
            if combined_path:
                try:
                    os.remove(combined_path)
                except OSError:
                    pass


    def _record_until_silence(self) -> str:
        """
        Record until:
        - we detect speech, then
        - we detect continuous silence for silence_stop_ms,
        - OR we hit max_record_seconds
        """
        print("[stt] listening...")

        frames: List[np.ndarray] = []
        heard_speech = False
        speech_blocks = 0
        silence_blocks = 0

        with sd.InputStream(samplerate=self.sample_rate, channels=1, dtype="float32") as stream:
            for _ in range(self._max_blocks):
                data, _ = stream.read(self._block)   # shape: (block, 1)
                x = data[:, 0].copy()
                frames.append(x)

                level = _rms(x)

                if level >= self.silence_rms_threshold:
                    heard_speech = True
                    speech_blocks += 1
                    silence_blocks = 0
                else:
                    if heard_speech:
                        silence_blocks += 1
                        if silence_blocks >= self._silence_blocks_needed:
                            break

        if not frames:
            # nothing recorded
            return self._write_temp_wav(np.zeros((0,), dtype=np.float32))

        audio = np.concatenate(frames)

        # If we never got enough speech, treat as empty
        if not heard_speech or speech_blocks < self._min_speech_blocks:
            return self._write_temp_wav(np.zeros((0,), dtype=np.float32))

        return self._write_temp_wav(audio)

    def _write_temp_wav(self, audio_f32: np.ndarray) -> str:
        # Convert float32 [-1, 1] to int16
        audio_i16 = np.clip(audio_f32, -1.0, 1.0)
        audio_i16 = (audio_i16 * 32767.0).astype(np.int16)

        fd, path = tempfile.mkstemp(prefix="jared_stt_", suffix=".wav")
        os.close(fd)
        wavfile.write(path, self.sample_rate, audio_i16)
        return path

    def _run_whisper(self, wav_path: str) -> str:
        """
        Use the CLI in the way your build supports:
        whisper-cli.exe [options] file0 file1 ...
        Keep output clean with -np and -nt.
        """
        cmd = [
            str(self._exe),
            "-m", str(self._model),
            "-l", self.language,
            "-nt",   # no timestamps
            "-np",   # no prints except results
            wav_path,
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=str(self._exe.parent),
        )

        if proc.returncode != 0:
            raise RuntimeError(
                "whisper-cli failed\n"
                f"code: {proc.returncode}\n"
                f"stdout:\n{proc.stdout}\n"
                f"stderr:\n{proc.stderr}\n"
            )

        # With -np, transcript should be in stdout. Grab last non-empty line.
        lines = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
        return lines[-1] if lines else ""
