from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from collections import deque
import os
import threading
import queue
import time
import numpy as np
from speech.wake.base import WakeResult


# -----------------------------
# DEV engine (unchanged)
# -----------------------------
@dataclass
class KeywordWakeEngine:
    name: str = "keyword-dev-wake"

    def __post_init__(self) -> None:
        self._running = False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def poll(self) -> WakeResult:
        if not self._running:
            return WakeResult(False, 0.0, "not-running")

        try:
            line = input("[wake] Enter=trigger, /wake=trigger, q=quit: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            raise

        if line in {"q", "quit", "exit"}:
            raise KeyboardInterrupt

        if line == "" or line == "/wake":
            return WakeResult(True, 1.0, "dev-trigger")

        return WakeResult(False, 0.0, "no-trigger")


# -----------------------------
# openWakeWord embedding-feature engine for your custom model
# -----------------------------
def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@dataclass
class OpenWakeWordConfig:
    threshold: float = 0.65
    cooldown_s: float = 2.0
    # Capture @ 48k, downsample to 16k for openwakeword features
    input_rate: int = 48000
    sr: int = 16000
    chunk_ms: int = 80  # 80ms @ 16k => 1280 samples (standard oww streaming chunk)
    pre_roll_ms: int = 700

    # Feature window your wake model expects: [1,96,16]
    n_feature_frames: int = 16

    wake_model_path: Optional[Path] = None
    input_device: Optional[int] = None

    debug_every_s: float = 1.0
    debug_audio: bool = False
    debug_scores: bool = False
    debug_shapes: bool = False


@dataclass
class OpenWakeWordEngine:
    """
    Correct pipeline for your hey_jared_float32.tflite:

      audio -> openwakeword AudioFeatures (ring buffer)
           -> get_features(n_feature_frames=16) -> [96,16]
           -> wake tflite expects input [1,96,16] float32
           -> output [1,1] float32 score
    """
    name: str = "openwakeword-hey-jared"
    cfg: OpenWakeWordConfig = field(default_factory=OpenWakeWordConfig)

    def __post_init__(self) -> None:
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None

        self._events: "queue.Queue[WakeResult]" = queue.Queue(maxsize=8)
        self._chunk_q: "queue.Queue[np.ndarray]" = queue.Queue(maxsize=128)

        self._sd = None
        self._pre = None
        self._wake_itp = None
        self._wake_in_idx: Optional[int] = None
        self._wake_out_idx: Optional[int] = None

        self._last_fire = 0.0
        self._pre_roll = deque(maxlen=int(self.cfg.sr * (self.cfg.pre_roll_ms / 1000.0)))


        self._rms_lock = threading.Lock()
        self._last_rms: float = 0.0
        self._last_audio_ts: float = 0.0

    def start(self) -> None:
        if self._running:
            return

        wake_path = self.cfg.wake_model_path
        if wake_path is None:
            wake_path = _project_root() / "third_party" / "openwakeword_models" / "hey_jared_float32.tflite"
        if not wake_path.exists():
            raise FileNotFoundError(f"Wake model not found: {wake_path}")

        env_dev = os.getenv("JARED_MIC_DEVICE", "").strip()
        if env_dev:
            try:
                self.cfg.input_device = int(env_dev)
            except ValueError:
                pass

        if self.cfg.input_device is None:
            self.cfg.input_device = 7  # your working DirectSound mic index

        print(f"[wake] init: device={self.cfg.input_device}")
        print(f"[wake] init: wake_model={wake_path.name}")

        import sounddevice as sd  # type: ignore
        import tensorflow as tf  # type: ignore
        from openwakeword.model import Model  # type: ignore

        self._sd = sd

        # Create a Model without wakeword models: we only want its AudioFeatures preprocessor
        m = Model(wakeword_models=[])
        self._pre = m.preprocessor  # openwakeword.utils.AudioFeatures

        # Load your custom wake model
        self._wake_itp = tf.lite.Interpreter(model_path=str(wake_path))
        self._wake_itp.allocate_tensors()

        in_det = self._wake_itp.get_input_details()[0]
        out_det = self._wake_itp.get_output_details()[0]
        self._wake_in_idx = int(in_det["index"])
        self._wake_out_idx = int(out_det["index"])

        if self.cfg.debug_shapes:
            print(f"[wake] wake_input shape={in_det['shape']} dtype={in_det['dtype']}")
            print(f"[wake] wake_output shape={out_det['shape']} dtype={out_det['dtype']}")

        self._running = True
        self._thread = threading.Thread(target=self._run, name="OpenWakeWordEngine", daemon=True)
        self._thread.start()
        print("[wake] audio thread started")

    def stop(self) -> None:
        self._running = False

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    def reset(self) -> None:
        # Flush queued audio chunks so we don't immediately re-trigger
        try:
            while True:
                self._chunk_q.get_nowait()
        except queue.Empty:
            pass

        # Reset cooldown timer
        self._last_fire = time.time()



    def poll(self) -> WakeResult:
        if not self._running:
            return WakeResult(False, 0.0, "not-running")
        try:
            return self._events.get_nowait()
        except queue.Empty:
            return WakeResult(False, 0.0, "no-trigger")

    def _run(self) -> None:
        assert self._sd is not None
        assert self._pre is not None
        assert self._wake_itp is not None
        assert self._wake_in_idx is not None
        assert self._wake_out_idx is not None

        sd = self._sd
        pre = self._pre

        if self.cfg.input_rate % self.cfg.sr != 0:
            raise RuntimeError("input_rate must be an integer multiple of sr (e.g., 48000 -> 16000).")
        decim = self.cfg.input_rate // self.cfg.sr  # 3

        chunk_len_16k = int(self.cfg.sr * (self.cfg.chunk_ms / 1000.0))  # 1280
        chunk_len_in = chunk_len_16k * decim  # 3840 @48k

        in_buf = np.zeros((0,), dtype=np.float32)

        def audio_callback(indata, frames, time_info, status) -> None:
            nonlocal in_buf
            if not self._running:
                return

            mono = indata.reshape(-1).astype(np.float32, copy=False)

            if self.cfg.debug_audio:
                rms = float(np.sqrt(np.mean(np.square(mono)))) if mono.size else 0.0
                with self._rms_lock:
                    self._last_rms = rms
                    self._last_audio_ts = time.time()

            in_buf = np.concatenate((in_buf, mono), dtype=np.float32)

            while in_buf.size >= chunk_len_in:
                block48 = in_buf[:chunk_len_in]
                in_buf = in_buf[chunk_len_in:]

                block16 = block48[::decim]  # 1280 samples float32

                pcm16 = np.clip(block16 * 32767.0, -32768, 32767).astype(np.int16)
                if pcm16.shape[0] != chunk_len_16k:
                    continue

                try:
                    self._chunk_q.put_nowait(pcm16)
                except queue.Full:
                    pass

        try:
            with sd.InputStream(
                samplerate=self.cfg.input_rate,
                channels=1,
                dtype="float32",
                callback=audio_callback,
                device=self.cfg.input_device,
            ):
                print(
                    f"[wake] listening: device={self.cfg.input_device} "
                    f"in_rate={self.cfg.input_rate} -> sr={self.cfg.sr} "
                    f"chunk_ms={self.cfg.chunk_ms} thr={self.cfg.threshold}"
                )

                last_audio_dbg = 0.0
                last_score_dbg = 0.0

                # warm-up: need enough audio in preprocessor ring buffer
                warmed = False

                while self._running:
                    now = time.time()

                    if (not self._paused) and self.cfg.debug_audio and (now - last_audio_dbg) >= self.cfg.debug_every_s:
                        last_audio_dbg = now
                        with self._rms_lock:
                            rms = self._last_rms
                            ats = self._last_audio_ts
                        age = (now - ats) if ats else 999.0
                        print(f"[wake] audio_rms={rms:.6f} audio_age={age:.2f}s")

                    try:
                        pcm16 = self._chunk_q.get(timeout=0.35)
                    except queue.Empty:
                        continue

                    if self._paused:
                        # keep latency low after resume
                        while not self._chunk_q.empty():
                            try:
                                self._chunk_q.get_nowait()
                            except queue.Empty:
                                break
                        continue



                    # Feed audio into openwakeword feature ring buffer
                    # AudioFeatures.__call__ returns an int (we don't care); it updates internal state
                    try:
                        _ = pre(pcm16)
                    except Exception as e:
                        print(f"[wake] preprocessor ERROR: {e!r}")
                        continue

                    # Fetch features and build x for wake model
                    try:
                        feats = pre.get_features(n_feature_frames=self.cfg.n_feature_frames, start_ndx=-1)
                        feats = np.asarray(feats, dtype=np.float32)

                        # openWakeWord returns (1,16,96) on your install:
                        #   batch=1, frames=16, dims=96
                        # Your wake model expects (1,96,16):
                        #   batch=1, dims=96, frames=16
                        if feats.shape == (1, self.cfg.n_feature_frames, 96):
                            x = np.transpose(feats, (0, 2, 1)).astype(np.float32, copy=False)  # (1,96,16)
                        elif feats.shape == (96, self.cfg.n_feature_frames):
                            x = feats.reshape(1, 96, self.cfg.n_feature_frames).astype(np.float32, copy=False)  # (1,96,16)
                        else:
                            if self.cfg.debug_shapes and not warmed:
                                print(f"[wake] warming... got feats shape={feats.shape} (need (1,16,96) or (96,16))")
                            continue

                        warmed = True

                    except Exception as e:
                        print(f"[wake] get_features ERROR: {e!r}")
                        continue


                    # ---- RUN WAKE MODEL INFERENCE ----
                    try:
                        self._wake_itp.set_tensor(self._wake_in_idx, x)
                        self._wake_itp.invoke()
                        y = self._wake_itp.get_tensor(self._wake_out_idx)
                        score = float(np.squeeze(y))
                    except Exception as e:
                        print(f"[wake] wake_infer ERROR: {e!r}")
                        continue

                    # ---- DEBUG SCORE ----
                    if self.cfg.debug_scores and (now - last_score_dbg) >= self.cfg.debug_every_s:
                        last_score_dbg = now
                        print(f"[wake] score={score:.3f}")

                    # ---- THRESHOLD CHECK ----
                    if score >= self.cfg.threshold and (now - self._last_fire) >= self.cfg.cooldown_s:
                        self._last_fire = now
                        print(f"[wake] TRIGGER score={score:.3f} thr={self.cfg.threshold}")
                        try:
                            audio = np.array(self._pre_roll, dtype=np.int16)
                            self._events.put_nowait(WakeResult(True, score, "embedding-threshold", audio=audio))
                        except queue.Full:
                            pass



        except Exception as e:
            print(f"[wake] stream FAILED: {e!r}")
            self._running = False
            try:
                self._events.put_nowait(WakeResult(False, 0.0, f"engine-error:{e}"))
            except queue.Full:
                pass
