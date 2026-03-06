from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Optional, Tuple

from core.observability.logger import get_logger
from core.event_bus import EventBus
from core.contracts.action_request import ActionRequest, ActionOutcome
from devices.registry.models import DeviceTarget, DeviceRecord
from devices.execution.device_manager import DeviceManager

log = get_logger("JARED")


@dataclass
class PendingDeviceClarification:
    intent_name: str
    state: str
    confidence: float
    original_target: str
    candidates: list[DeviceRecord]


class IntentRouter:
    def __init__(self, *, device_manager: DeviceManager, bus: EventBus):
        self.device_manager = device_manager
        self.bus = bus
        self.pending_device_clarification: PendingDeviceClarification | None = None

    def has_pending_clarification(self) -> bool:
        return self.pending_device_clarification is not None

    def handle_clarification_reply(self, raw_text: str) -> bool:
        pending = self.pending_device_clarification
        if pending is None:
            return False

        match = self._match_clarification_candidate(raw_text, pending.candidates)
        if match is None:
            prompt = self._build_clarification_prompt(pending.candidates)
            self.bus.publish(
                "action.clarification_required",
                kind="device",
                original_target=pending.original_target,
                reply=raw_text,
                candidates=self._serialize_candidates(pending.candidates),
            )
            self._say(f"I still need which device you meant. {prompt}")
            return True

        self.pending_device_clarification = None

        outcome = self._execute_device_request(
            name=pending.intent_name,
            state=pending.state,
            confidence=pending.confidence,
            target=DeviceTarget(
                device_id=match.device_id,
                device_name=match.name,
                room_id=match.room_id,
            ),
        )
        self._finish_device_outcome(outcome)
        return True

    def handle(self, name: str, confidence: float, slots: dict, raw_text: str) -> None:
        if confidence < 0.5:
            log.info(f"[router] low confidence, ignoring: {name} ({confidence:.2f}) '{raw_text}'")
            return

        if name in {"device.toggle", "device.set_power"}:
            self.pending_device_clarification = None

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

        if name in {"device.toggle", "device.set_power"}:
            outcome = self._device_command(name=name, slots=slots, confidence=confidence)
            if outcome is None:
                return
            self._finish_device_outcome(outcome)
            return

        log.info(f"[router] unhandled intent: {name} ({confidence:.2f}) '{raw_text}'")

    def _finish_device_outcome(self, outcome: ActionOutcome) -> None:
        log.info(
            f"[action] {outcome.request.intent_name} -> "
            f"outcome.policy={outcome.policy.reason_code} allowed={outcome.policy.allowed}"
        )
        if outcome.execution_result:
            log.info(f"[action] exec -> {outcome.execution_result}")

        if not outcome.policy.allowed:
            self._say(outcome.policy.message)
            return

        if outcome.execution_result and not outcome.execution_result.get("ok", False):
            self._say(outcome.execution_result.get("details", "Execution failed."))
            return

        if outcome.policy.requires_verification:
            vr = outcome.verification_result or {}
            if not vr.get("verified", False):
                self._say("I couldn't verify that it worked. Please check the device.")
                return

        self._say("Done.")

    def _say(self, text: str) -> None:
        text = (text or "").strip()
        if not text:
            return
        self.bus.publish("assistant.say", text=text)

    def _device_command(self, *, name: str, slots: dict, confidence: float) -> ActionOutcome | None:
        state = str(slots.get("state", slots.get("power", "on"))).strip()
        target_text = str(slots.get("target", slots.get("device", ""))).strip()

        room_name, device_name = self._parse_target(target_text)
        initial_target = DeviceTarget(
            room_name=room_name,
            device_name=device_name,
            device_id=slots.get("device_id"),
            room_id=slots.get("room_id"),
        )

        candidates = self.device_manager.registry.resolve_candidates(initial_target)

        if len(candidates) > 1:
            self.pending_device_clarification = PendingDeviceClarification(
                intent_name=name,
                state=state,
                confidence=confidence,
                original_target=target_text,
                candidates=candidates,
            )
            self.bus.publish(
                "action.clarification_required",
                kind="device",
                original_target=target_text,
                candidates=self._serialize_candidates(candidates),
            )
            self._say(self._build_clarification_prompt(candidates))
            return None

        if len(candidates) == 1:
            only = candidates[0]
            target = DeviceTarget(
                device_id=only.device_id,
                device_name=only.name,
                room_id=only.room_id,
            )
        else:
            target = initial_target

        return self._execute_device_request(
            name=name,
            state=state,
            confidence=confidence,
            target=target,
        )

    def _execute_device_request(
        self,
        *,
        name: str,
        state: str,
        confidence: float,
        target: DeviceTarget,
    ) -> ActionOutcome:
        req_slots: dict[str, str] = {}
        if state:
            req_slots["state"] = state

        req = ActionRequest(
            intent_name=name,
            slots=req_slots,
            source="voice",
            confidence=confidence,
        )
        return self.device_manager.handle(req, target=target)

    @staticmethod
    def _parse_target(target: str) -> Tuple[Optional[str], Optional[str]]:
        if not target:
            return None, None

        t = target.strip().replace("\\", "/")
        for sep in ("/", ":", "|"):
            if sep in t:
                parts = [p.strip() for p in t.split(sep) if p.strip()]
                if len(parts) >= 2:
                    return parts[0], " ".join(parts[1:])

        parts = [p for p in t.split() if p and p.lower() not in {"the", "a", "an", "my"}]

        if len(parts) == 1:
            return None, parts[0]

        if len(parts) == 2:
            return parts[0], parts[1]

        return parts[0], " ".join(parts[1:])

    def _build_clarification_prompt(self, candidates: list[DeviceRecord]) -> str:
        labels = [self._candidate_label(c) for c in candidates]
        if not labels:
            return "Which device did you mean?"
        if len(labels) == 1:
            return f"Did you mean {labels[0]}?"
        if len(labels) == 2:
            return f"Which device did you mean: {labels[0]} or {labels[1]}?"
        return f"Which device did you mean: {', '.join(labels[:-1])}, or {labels[-1]}?"

    def _serialize_candidates(self, candidates: list[DeviceRecord]) -> list[dict]:
        out: list[dict] = []
        for c in candidates:
            out.append(
                {
                    "device_id": c.device_id,
                    "name": c.name,
                    "room_id": c.room_id,
                    "label": self._candidate_label(c),
                }
            )
        return out

    def _candidate_label(self, candidate: DeviceRecord) -> str:
        room_name = self._room_name(candidate.room_id)
        name = candidate.name.strip()
        room_l = room_name.lower().strip()
        name_l = name.lower().strip()

        if room_name and room_l not in name_l:
            return f"{room_name} {name}"
        return name

    def _room_name(self, room_id: str) -> str:
        room = self.device_manager.registry.get_room_by_id(room_id)
        return room.name.strip() if room else room_id

    def _match_clarification_candidate(
        self,
        raw_text: str,
        candidates: list[DeviceRecord],
    ) -> DeviceRecord | None:
        reply = self._normalize_clarification_text(raw_text)
        if not reply:
            return None

        reply_tokens = set(reply.split())
        matches: list[DeviceRecord] = []

        for candidate in candidates:
            alias_values = {
                self._normalize_clarification_text(candidate.name),
                self._normalize_clarification_text(self._candidate_label(candidate)),
                self._normalize_clarification_text(self._room_name(candidate.room_id)),
            }
            alias_values = {a for a in alias_values if a}

            matched = False
            for alias in alias_values:
                alias_tokens = set(alias.split())
                if reply == alias:
                    matched = True
                    break
                if alias in reply or reply in alias:
                    matched = True
                    break
                if reply_tokens and reply_tokens.issubset(alias_tokens):
                    matched = True
                    break

            if matched:
                matches.append(candidate)

        if len(matches) == 1:
            return matches[0]
        return None

    @staticmethod
    def _normalize_clarification_text(text: str) -> str:
        t = (text or "").strip().lower()
        t = re.sub(r"[^\w\s]", " ", t)
        t = re.sub(r"\b(the|a|an|one|ones|please|device|lights|light)\b", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

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