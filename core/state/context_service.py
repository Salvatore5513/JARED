from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional
import time


class ContextMode(str, Enum):
    IDLE = "IDLE"
    LISTENING = "LISTENING"   # wake detected / STT active
    WORKING = "WORKING"       # executing an action (device/media/timer/etc)
    SPEAKING = "SPEAKING"     # TTS speaking


@dataclass
class ContextState:
    mode: ContextMode = ContextMode.IDLE
    room_id: Optional[str] = None

    # What just happened
    last_event_type: Optional[str] = None
    last_intent_name: Optional[str] = None
    last_device_id: Optional[str] = None
    last_action: Optional[str] = None

    # Timing
    updated_at: float = field(default_factory=lambda: time.time())
    last_audio_activity_at: Optional[float] = None
    last_wake_at: Optional[float] = None
    last_stt_start_at: Optional[float] = None
    last_stt_end_at: Optional[float] = None
    last_action_start_at: Optional[float] = None
    last_action_end_at: Optional[float] = None
    last_tts_start_at: Optional[float] = None
    last_tts_end_at: Optional[float] = None

    # Simple anti-annoyance / “busy” signal
    busy: bool = False


class ContextService:
    """
    Lightweight context/state machine for JARED.

    - Subscribe this service to your EventBus.
    - Feed it events (type + payload + optional room_id).
    - Query it anywhere to decide “is it appropriate to speak/suggest/interrupt?”
    """

    def __init__(self) -> None:
        self._state = ContextState()
        self._listeners: list[Callable[[ContextState], None]] = []

        # Simple mapping from event types to handlers
        self._handlers: Dict[str, Callable[[Dict[str, Any]], None]] = {
            # Your real STT topics
            "stt.listening": self._on_stt_started,
            "stt.skipped": self._on_stt_cancelled,

            # Your real NLP topic
            "nlp.intent": self._on_intent_recognized,

            # Action events (we will wire these next)
            "action.started": self._on_action_started,
            "action.verified": self._on_action_finished,
            "action.failed": self._on_action_finished,

            # Future TTS support
            "tts.started": self._on_tts_started,
            "tts.completed": self._on_tts_completed,
            "tts.cancelled": self._on_tts_cancelled,
        }

    # -----------------------------
    # Public API
    # -----------------------------

    def get_state(self) -> ContextState:
        return self._state

    def add_listener(self, fn: Callable[[ContextState], None]) -> None:
        """Called whenever state changes."""
        self._listeners.append(fn)

    def on_event(self, event_type: str, payload: Dict[str, Any] | None = None) -> None:
        """
        Call this from your EventBus subscription.
        payload may include: room_id, intent_name, device_id, action, etc.
        """
        payload = payload or {}

        # Normalize room_id if present
        room_id = payload.get("room_id")
        if room_id:
            self._state.room_id = str(room_id)

        self._state.last_event_type = event_type
        self._touch()

        handler = self._handlers.get(event_type)
        if handler:
            handler(payload)
        else:
            # Track generic activity without changing mode
            # (useful for presence/noise/media events later)
            pass

        self._emit_state()

    def handle_bus_event(self, evt) -> None:
        """
        Direct hook for EventBus subscription.
        """
        self.on_event(evt.topic, evt.data)

    def is_busy(self) -> bool:
        """Simple “should I avoid interrupting?” signal."""
        return bool(self._state.busy)

    # -----------------------------
    # Internal helpers
    # -----------------------------

    def _touch(self) -> None:
        self._state.updated_at = time.time()

    def _emit_state(self) -> None:
        for fn in self._listeners:
            try:
                fn(self._state)
            except Exception:
                # Context should never crash the app; keep it resilient.
                continue

    def _set_mode(self, mode: ContextMode) -> None:
        self._state.mode = mode
        self._touch()

    def _set_busy(self, busy: bool) -> None:
        self._state.busy = busy
        self._touch()

    # -----------------------------
    # Event handlers
    # -----------------------------

    def _on_wake_detected(self, payload: Dict[str, Any]) -> None:
        self._state.last_wake_at = time.time()
        self._state.last_audio_activity_at = time.time()
        self._set_mode(ContextMode.LISTENING)
        # Not necessarily “busy”, but we are actively engaging
        self._set_busy(True)

    def _on_stt_started(self, payload: Dict[str, Any]) -> None:
        self._state.last_stt_start_at = time.time()
        self._state.last_audio_activity_at = time.time()
        self._set_mode(ContextMode.LISTENING)
        self._set_busy(True)
        self._state.last_intent_name = None

    def _on_stt_completed(self, payload: Dict[str, Any]) -> None:
        self._state.last_stt_end_at = time.time()
        self._state.last_audio_activity_at = time.time()
        # Do NOT force IDLE here.
        # Wait for intent or cancellation to decide next state.

    def _on_stt_cancelled(self, payload: Dict[str, Any]) -> None:
        self._state.last_stt_end_at = time.time()
        self._set_busy(False)
        self._set_mode(ContextMode.IDLE)

    def _on_intent_recognized(self, payload: Dict[str, Any]) -> None:
        name = payload.get("name") or payload.get("intent_name")
        if name:
            self._state.last_intent_name = str(name)
        # We’re about to do something (execute or respond)
        self._set_mode(ContextMode.WORKING)
        self._set_busy(True)

    def _on_intent_unknown(self, payload: Dict[str, Any]) -> None:
        # Unknown intent: we should stop being “busy” unless something else kicks off
        self._set_busy(False)
        self._set_mode(ContextMode.IDLE)

    def _on_action_started(self, payload: Dict[str, Any]) -> None:
        self._state.last_action_start_at = time.time()
        device_id = payload.get("device_id")
        action = payload.get("action")
        if device_id:
            self._state.last_device_id = str(device_id)
        if action:
            self._state.last_action = str(action)
        self._set_mode(ContextMode.WORKING)
        self._set_busy(True)

    def _on_action_finished(self, payload: Dict[str, Any]) -> None:
        self._state.last_action_end_at = time.time()
        # After action completes, we’re usually about to speak confirmation OR return to idle.
        # Don’t force SPEAKING here; let tts.started do that.
        self._set_busy(False)
        self._set_mode(ContextMode.IDLE)

    def _on_tts_started(self, payload: Dict[str, Any]) -> None:
        self._state.last_tts_start_at = time.time()
        self._set_mode(ContextMode.SPEAKING)
        self._set_busy(True)

    def _on_tts_completed(self, payload: Dict[str, Any]) -> None:
        self._state.last_tts_end_at = time.time()
        self._set_busy(False)
        self._set_mode(ContextMode.IDLE)

    def _on_tts_cancelled(self, payload: Dict[str, Any]) -> None:
        self._state.last_tts_end_at = time.time()
        self._set_busy(False)
        self._set_mode(ContextMode.IDLE)
