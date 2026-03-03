from __future__ import annotations

import threading
from dataclasses import dataclass, field

from core.event_bus import EventBus
from speech.pipeline import VoicePipeline
from speech.tts.voice_output_service import VoiceOutputService


@dataclass
class Runtime:
    """
    Minimal lifecycle controller.
    ONLY object exposed to UI / CLI.
    """
    bus: EventBus
    voice: VoicePipeline
    voice_output: VoiceOutputService | None = None

    _voice_thread: threading.Thread | None = field(default=None, init=False, repr=False)

    def start(self) -> None:
        # If already running, do nothing
        if self._voice_thread and self._voice_thread.is_alive():
            return

        # Announce startup (UI/logs can show this immediately)
        try:
            self.bus.publish("system.startup", state="starting")
        except Exception:
            pass

        self._voice_thread = threading.Thread(
            target=self.voice.run_forever,
            name="VoicePipeline",
            daemon=True,
        )
        self._voice_thread.start()

        # Confirm started
        try:
            self.bus.publish("system.startup", state="started")
        except Exception:
            pass

    def stop(self) -> None:
        # Notify system that shutdown is starting
        try:
            self.bus.publish("system.shutdown", reason="runtime_stop")
        except Exception:
            pass

        # Stop voice pipeline
        try:
            self.voice.stop()
        except Exception:
            pass

        # Stop TTS service if present
        if self.voice_output is not None:
            try:
                self.voice_output.stop()
            except Exception:
                pass