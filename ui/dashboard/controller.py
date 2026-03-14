from __future__ import annotations

from typing import Any


class DashboardController:
    def __init__(self, bus, *, offline_only: bool) -> None:
        self.bus = bus
        self.state: dict[str, Any] = {
            "runtime_ready": False,
            "wake_ready": False,
            "stt_ready": False,
            "tts_ready": False,
            "offline_only": bool(offline_only),
            "context_mode": "unknown",
            "busy": False,
            "intent": None,
            "device": None,
            "last_transcript": "",
            "last_action_summary": "",
            "last_action_status": "unknown",
            "voice_pipeline_state": "unknown",
            "stt_engine": "",
            "wake_engine": "",
            "assistant_text": "",
            "tts_status": "idle",
            "recent_activity": [],
            "boot_total_ms": 0,
            "boot_stages": [],
        }
        self.recent_activity: list[str] = []

        self.bus.subscribe("ui.dashboard.refresh", self._on_ui_dashboard_refresh)
        self.bus.subscribe("ui.context.state", self._on_ui_context_state)
        self.bus.subscribe("voice.pipeline", self._on_voice_pipeline)
        self.bus.subscribe("voice.transcript", self._on_voice_transcript)
        self.bus.subscribe("action.requested", self._on_action_requested)
        self.bus.subscribe("action.policy_decided", self._on_action_policy_decided)
        self.bus.subscribe("action.executed", self._on_action_executed)
        self.bus.subscribe("action.failed", self._on_action_failed)
        self.bus.subscribe("assistant.say", self._on_assistant_say)
        self.bus.subscribe("tts.started", self._on_tts_started)
        self.bus.subscribe("tts.completed", self._on_tts_completed)
        self.bus.subscribe("tts.unavailable", self._on_tts_unavailable)
        self.bus.subscribe("tts.failed", self._on_tts_failed)
        self.bus.subscribe("system.runtime_ready", self._on_system_runtime_ready)
        self.bus.subscribe("system.stt_ready", self._on_system_stt_ready)
        self.bus.subscribe("system.wake_ready", self._on_system_wake_ready)
        self.bus.subscribe("system.tts_ready", self._on_system_tts_ready)
        self.bus.subscribe("system.boot.stage", self._on_system_boot_stage)

    def publish_snapshot(self) -> None:
        self.bus.publish("ui.dashboard.snapshot", **self.state)

    def _on_ui_dashboard_refresh(self, _evt) -> None:
        self.publish_snapshot()

    def _on_ui_context_state(self, evt) -> None:
        self.state["context_mode"] = str(evt.data.get("mode", "unknown"))
        self.state["busy"] = bool(evt.data.get("busy", False))
        self.state["intent"] = evt.data.get("intent")
        self.state["device"] = evt.data.get("device")
        self.publish_snapshot()

    def _add_activity(self, text: str) -> None:
        from datetime import datetime

        ts = datetime.now().strftime("%H:%M:%S")
        line = f"{ts}  {text}"

        self.recent_activity.append(line)

        if len(self.recent_activity) > 200:
            self.recent_activity.pop(0)

        self.state["recent_activity"] = list(self.recent_activity)

    def _on_voice_pipeline(self, evt) -> None:
        self.state["voice_pipeline_state"] = str(evt.data.get("state", "unknown"))
        self.state["stt_engine"] = str(evt.data.get("stt", ""))
        self.state["wake_engine"] = str(evt.data.get("wake", ""))
        self.publish_snapshot()

    def _on_voice_transcript(self, evt) -> None:
        text = str(evt.data.get("text", "")).strip()
        self.state["last_transcript"] = text

        if text:
            self._add_activity(f'Voice: "{text}"')

        self.publish_snapshot()

    def _on_action_requested(self, evt) -> None:
        request = evt.data.get("request", {}) or {}
        if not isinstance(request, dict):
            return

        intent_name = str(request.get("intent_name", "")).strip()
        device_id = str(request.get("device_id", "")).strip()
        slots = request.get("slots", {}) or {}

        summary = intent_name or "unknown action"
        state = str(slots.get("state", "")).strip().lower()
        if state:
            summary += f" {state}"
        if device_id:
            summary += f" -> {device_id}"

        self.state["last_action_summary"] = summary
        self.state["last_action_status"] = "requested"
        self._add_activity(f"Action Requested: {summary}")
        self.publish_snapshot()

    def _on_action_policy_decided(self, evt) -> None:
        decision = evt.data.get("decision", {}) or {}
        if not isinstance(decision, dict):
            return

        allowed = bool(decision.get("allowed"))
        self.state["last_action_status"] = "allowed" if allowed else "denied"

        if not allowed:
            reason = str(decision.get("reason", "denied")).strip()
            self._add_activity(f"Policy Denied: {reason}")

        self.publish_snapshot()

    def _on_action_executed(self, evt) -> None:
        driver_result = evt.data.get("driver_result", {}) or {}
        if not isinstance(driver_result, dict):
            return

        ok = bool(driver_result.get("ok", False))
        self.state["last_action_status"] = "executed" if ok else "failed"
        self._add_activity("Action Executed" if ok else "Action Failed")
        self.publish_snapshot()

    def _on_action_failed(self, evt) -> None:
        self.state["last_action_status"] = "failed"

        reason = str(evt.data.get("reason", "")).strip()
        code = str(evt.data.get("code", "")).strip()

        if reason and code:
            self._add_activity(f"Action Failed: {code} | {reason}")
        elif reason:
            self._add_activity(f"Action Failed: {reason}")
        elif code:
            self._add_activity(f"Action Failed: {code}")
        else:
            self._add_activity("Action Failed")

        self.publish_snapshot()

    def _on_assistant_say(self, evt) -> None:
        text = str(evt.data.get("text", "")).strip()
        self.state["assistant_text"] = text

        if text:
            self._add_activity(f"Assistant: {text}")

        self.publish_snapshot()

    def _on_tts_started(self, _evt) -> None:
        self.state["tts_status"] = "speaking"
        self.publish_snapshot()

    def _on_tts_completed(self, _evt) -> None:
        self.state["tts_status"] = "idle"
        self.publish_snapshot()

    def _on_tts_unavailable(self, evt) -> None:
        reason = str(evt.data.get("reason", "unavailable")).strip()
        self.state["tts_status"] = f"unavailable | {reason}"
        self.publish_snapshot()

    def _on_tts_failed(self, evt) -> None:
        reason = str(evt.data.get("reason", "failed")).strip()
        self.state["tts_status"] = f"failed | {reason}"
        self.publish_snapshot()

    def _on_system_runtime_ready(self, evt) -> None:
        self.state["runtime_ready"] = bool(evt.data.get("ready", False))
        self.publish_snapshot()

    def _on_system_stt_ready(self, evt) -> None:
        self.state["stt_ready"] = bool(evt.data.get("ready", False))
        self.publish_snapshot()

    def _on_system_wake_ready(self, evt) -> None:
        self.state["wake_ready"] = bool(evt.data.get("ready", False))
        self.publish_snapshot()

    def _on_system_tts_ready(self, evt) -> None:
        self.state["tts_ready"] = bool(evt.data.get("ready", False))
        self.publish_snapshot()

    def _on_system_boot_stage(self, evt) -> None:
        stage = str(evt.data.get("stage", "")).strip()
        elapsed_ms = int(evt.data.get("elapsed_ms", 0) or 0)
        total_ms = int(evt.data.get("total_ms", 0) or 0)

        stages = list(self.state.get("boot_stages", []))

        stages = [s for s in stages if s.get("stage") != stage]
        stages.append({"stage": stage, "elapsed_ms": elapsed_ms})

        order = {"Runtime": 10, "Devices": 20, "Voice": 30, "UI": 40}
        stages.sort(key=lambda s: order.get(s.get("stage", ""), 999))

        self.state["boot_stages"] = stages
        self.state["boot_total_ms"] = total_ms

        self.publish_snapshot()