from core.observability.logger import get_logger

log = get_logger("JARED")


class IntentRouter:
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

        if name == "device.toggle":
            state = str(slots.get("state", "off"))
            target = str(slots.get("target", ""))
            self._device_toggle(state, target)
            return

        log.info(f"[router] unhandled intent: {name} ({confidence:.2f}) '{raw_text}'")

    # --- handlers (stubs for now) ---
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

    def _device_toggle(self, state: str, target: str) -> None:
        log.info(f"[action] device.toggle -> {state} '{target}' (stub)")
