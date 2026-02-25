from __future__ import annotations

from dataclasses import dataclass
import time

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
    post_wake_delay_s: float = 0.0

    def start(self) -> None:
        self.wake.start()
        self.stt.start()
        self.bus.publish(
            "voice.pipeline",
            state="started",
            wake=self.wake.name,
            stt=self.stt.name,
        )

    def stop(self) -> None:
        # Stop both even if one throws
        try:
            self.wake.stop()
        finally:
            self.stt.stop()
        self.bus.publish("voice.pipeline", state="stopped")

    def run_forever(self) -> None:
        self.start()
        try:
            while True:
                wr = self.wake.poll()
                if not wr.triggered:
                    continue

                # ---- GATE WAKE WHILE STT RUNS (pause FIRST so we can't double-trigger) ----
                if hasattr(self.wake, "pause"):
                    self.wake.pause()   # type: ignore[attr-defined]
                else:
                    self.wake.stop()

                self.bus.publish("voice.wake", confidence=wr.confidence, reason=wr.reason)

                try:
                    tr = self.stt.transcribe_once(audio=wr.audio)
                finally:
                    # Optional: clear wake state so the same "hey jared" can't re-trigger
                    if hasattr(self.wake, "reset"):
                        self.wake.reset()  # type: ignore[attr-defined]

                    if hasattr(self.wake, "resume"):
                        self.wake.resume()  # type: ignore[attr-defined]
                    else:
                        self.wake.start()



                self.bus.publish(
                    "voice.transcript",
                    text=tr.text,
                    confidence=tr.confidence,
                    final=tr.is_final,
                )
        except KeyboardInterrupt:
            self.stop()
            raise

