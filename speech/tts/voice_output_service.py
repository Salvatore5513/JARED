from __future__ import annotations

import queue
import threading
from dataclasses import dataclass

from core.event_bus import Event, EventBus

from audio.oneshot import OneShotPlayer
from speech.tts.base import TTSRequest
from speech.tts.engines.xtts_sidecar_client import XTTSSidecarClient
from speech.tts.renderer import TTSRenderer


@dataclass
class VoiceOutputService:
    bus: EventBus
    output_device_index: int | None = None

    def __post_init__(self) -> None:
        self._q: "queue.Queue[dict]" = queue.Queue()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, name="VoiceOutputService", daemon=True)

        self._engine = XTTSSidecarClient()
        self._renderer = TTSRenderer(self._engine)
        self._player = OneShotPlayer(output_device_index=self.output_device_index)

    def start(self) -> None:
        # warmup = simple health check
        self._renderer.warmup()
        self.bus.subscribe("assistant.say", self._on_tts_say)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._q.put({"text": ""})
        self._thread.join(timeout=2)

    def _on_tts_say(self, evt: Event) -> None:
        text = (evt.data or {}).get("text")
        if not text:
            return
        self._q.put({"text": str(text), "language": str(evt.data.get("language", "en"))})

    def _run(self) -> None:
        while not self._stop.is_set():
            item = self._q.get()
            if self._stop.is_set():
                break

            text = item.get("text", "")
            if not text:
                continue

            print(f"[say] {text}")
            self.bus.publish("tts.started", text=text)

            try:
                res = self._renderer.render(TTSRequest(text=text, language=item.get("language", "en")))
                self._player.play_wav(res.wav_path)
                self.bus.publish("tts.completed", text=text)
            except Exception as e:
                self.bus.publish("tts.failed", text=text, reason=repr(e))
                print("[VoiceOutputService] error:", repr(e))