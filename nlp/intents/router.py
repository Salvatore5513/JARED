from __future__ import annotations

from typing import Optional, Tuple

from core.observability.logger import get_logger
from core.event_bus import EventBus
from core.contracts.action_request import ActionRequest
from devices.registry.models import DeviceTarget
from devices.execution.device_manager import DeviceManager

log = get_logger("JARED")


class IntentRouter:
    def __init__(self, *, device_manager: DeviceManager, bus: EventBus):
        self.device_manager = device_manager
        self.bus = bus

    def handle(self, name: str, confidence: float, slots: dict, raw_text: str) -> None:
        # Basic guardrail
        if confidence < 0.5:
            log.info(f"[router] low confidence, ignoring: {name} ({confidence:.2f}) '{raw_text}'")
            return

        # Route intents
        if name == "media.play":
            self._media_play()
            return

        if name == "media.pause":
            self._media_pause()
            return

        if name == "media.set_volume":
            vol = int(slots.get("volume", 50))
            self._media_set_volume(vol)
            return

        if name == "system.status":
            self._system_status()
            return

        if name == "system.help":
            self._system_help()
            return

        if name == "garage.note":
            self._garage_note(str(slots.get("text", "")).strip())
            return

        # --- Milestone 3: real device execution path ---
        if name in {"device.toggle", "device.set_power"}:
            outcome = self._device_command(name=name, slots=slots, confidence=confidence)

            log.info(f"[action] {name} -> outcome.policy={outcome.policy.reason_code} allowed={outcome.policy.allowed}")
            if outcome.execution_result:
                log.info(f"[action] exec -> {outcome.execution_result}")

            if not outcome.policy.allowed:
                self._say(outcome.policy.message)
                return

            if outcome.execution_result and not outcome.execution_result.get("ok", False):
                self._say(outcome.execution_result.get('details', 'Execution failed.'))
                return

            # ✅ NEW: verify gate
            if outcome.policy.requires_verification:
                vr = outcome.verification_result or {}
                if not vr.get("verified", False):
                    self._say("I couldn't verify that it worked. Please check the device.")
                    return

            self._say("Done.")
            return

        log.info(f"[router] unhandled intent: {name} ({confidence:.2f}) '{raw_text}'")

    def _say(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        # Semantic event: “assistant intends to say this”
        self.bus.publish("assistant.say", text=text)

    # -------------------------
    # Milestone 3 device path
    # -------------------------

    def _device_command(self, *, name: str, slots: dict, confidence: float):
        # Normalize to a single intent name for DeviceManager
        # (You can expand later for set_level, etc.)
        state = str(slots.get("state", slots.get("power", "on"))).strip()
        target_text = str(slots.get("target", slots.get("device", ""))).strip()

        room_name, device_name = self._parse_target(target_text)

        slots = {}
        # Keep state only when it exists (toggle may not have one)
        if state is not None:
            slots["state"] = state

        req = ActionRequest(
            intent_name=name,   # ✅ keep original intent (device.toggle, device.set_power, etc.)
            slots=slots,
            source="voice",
            confidence=confidence,
        )

        target = DeviceTarget(
            room_name=room_name,
            device_name=device_name,
            device_id=slots.get("device_id"),
            room_id=slots.get("room_id"),
        )

        return self.device_manager.handle(req, target=target)

    @staticmethod
    def _parse_target(target: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Heuristic mapping:
          "garage lights" -> ("garage", "lights")
          "garage/lights" -> ("garage", "lights")
          "garage:lights" -> ("garage", "lights")

        If only one token is provided, treat it as device_name.
        """
        if not target:
            return None, None

        t = target.strip().replace("\\", "/")
        for sep in ("/", ":", "|"):
            if sep in t:
                parts = [p.strip() for p in t.split(sep) if p.strip()]
                if len(parts) >= 2:
                    return parts[0], " ".join(parts[1:])

        # space-based fallback: last token(s) as device name, rest as room
        parts = [p for p in t.split() if p and p.lower() not in {"the", "a", "an", "my"}]

        if len(parts) == 1:
            return None, parts[0]

        if len(parts) == 2:
            return parts[0], parts[1]

        # 3+ words: first token is room, rest is the device name
        return parts[0], " ".join(parts[1:])

    # -------------------------
    # Existing handlers (stubs)
    # -------------------------

    def _media_play(self) -> None:
        log.info("[action] media.play (stub)")

    def _media_pause(self) -> None:
        log.info("[action] media.pause (stub)")

    def _media_set_volume(self, volume: int) -> None:
        log.info(f"[action] media.set_volume -> {volume} (stub)")

    def _system_status(self) -> None:
        log.info("[action] system.status (stub)")

    def _system_help(self) -> None:
        log.info("[action] system.help (stub)")

    def _garage_note(self, text: str) -> None:
        log.info(f"[action] garage.note -> '{text}' (stub)")