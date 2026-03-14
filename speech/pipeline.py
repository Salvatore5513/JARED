from __future__ import annotations

from dataclasses import dataclass, field
import time
import numpy as np

from core.event_bus import EventBus
from speech.wake.base import WakeWordEngine
from speech.stt.base import SpeechToTextEngine


@dataclass
class VoicePipeline:
    bus: EventBus
    wake: WakeWordEngine
    stt: SpeechToTextEngine

    # Prevent CPU spin when wake.poll() is non-blocking
    idle_sleep_s: float = 0.02  # 20ms

    # Optional tiny delay after wake before STT grabs audio
    post_wake_delay_s: float = 0.3
    post_wake_grace_s: float = 0.8
    min_stt_rms: float = 800.0
    skip_blank_audio: bool = True

    _running: bool = field(default=False, init=False, repr=False)
    _started: bool = field(default=False, init=False, repr=False)

    def start(self) -> None:
        if self._started:
            return

        self.wake.start()
        self.stt.start()
        self._started = True

        self.bus.publish(
            "voice.pipeline",
            state="started",
            wake=self.wake.name,
            stt=self.stt.name,
        )

    def stop(self) -> None:
        self._running = False

        try:
            self.wake.stop()
        finally:
            self.stt.stop()

        if self._started:
            self.bus.publish("voice.pipeline", state="stopped")

        self._started = False

    def run_forever(self) -> None:
        self.start()
        self._running = True

        try:
            while self._running:
                wr = self.wake.poll()

                if not self._running:
                    break

                if not wr.triggered:
                    time.sleep(self.idle_sleep_s)
                    continue

                # Gate wake while STT runs: pause FIRST so we can't double-trigger
                if hasattr(self.wake, "pause"):
                    self.wake.pause()  # type: ignore[attr-defined]
                else:
                    self.wake.stop()

                self.bus.publish(
                    "voice.wake",
                    confidence=wr.confidence,
                    reason=wr.reason,
                )

                if self.post_wake_delay_s > 0:
                    time.sleep(self.post_wake_delay_s)

                try:
                    if not self._running:
                        break

                    self.bus.publish("stt.listening", phase="wake_stt")

                    tr = None
                    if self.skip_blank_audio:
                        audio_i16 = wr.audio
                        if audio_i16 is None or len(audio_i16) == 0:
                            skip_reason = "no-audio"
                            self.bus.publish("stt.skipped", reason=skip_reason)
                            tr = None
                        else:
                            # RMS in int16 units
                            rms = float(np.sqrt(np.mean(np.square(audio_i16.astype(np.float32)))))
                            if rms < self.min_stt_rms:
                                skip_reason = "too-quiet"
                                self.bus.publish("stt.skipped", reason=skip_reason, rms=rms)
                                tr = None
                            else:
                                tr = self.stt.transcribe_once(audio=wr.audio)
                    else:
                        tr = self.stt.transcribe_once(audio=wr.audio)

                finally:
                    # Only try to restore wake engine if we're still running
                    if self._running:
                        if hasattr(self.wake, "reset"):
                            self.wake.reset()  # type: ignore[attr-defined]

                        if hasattr(self.wake, "resume"):
                            self.wake.resume()  # type: ignore[attr-defined]
                        else:
                            self.wake.start()

                if not self._running:
                    break

                if tr is None:
                    continue

                self.bus.publish(
                    "voice.transcript",
                    text=tr.text,
                    confidence=tr.confidence,
                    final=tr.is_final,
                )

        except KeyboardInterrupt:
            self.stop()
            raise
        except Exception as e:
            try:
                self.bus.publish(
                    "voice.pipeline",
                    state="error",
                    error=repr(e),
                )
            except Exception:
                pass
            self.stop()
            raise
        finally:
            self._running = False