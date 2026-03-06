from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QGridLayout,
    QVBoxLayout,
    QGroupBox,
)

class DashboardPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        title = QLabel("<b>System Dashboard</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.pipeline_value = QLabel("—")
        self.stt_engine_value = QLabel("—")
        self.wake_engine_value = QLabel("—")
        self.devices_value = QLabel("—")
        self.wake_value = QLabel("—")
        self.listening_value = QLabel("—")
        self.transcript_value = QLabel("—")
        self.intent_value = QLabel("—")
        self.action_value = QLabel("—")
        self.assistant_value = QLabel("—")
        self.tts_value = QLabel("—")
        self.runtime_value = QLabel("—")
        self.stt_ready_value = QLabel("—")
        self.wake_ready_value = QLabel("—")
        self.tts_ready_status_value = QLabel("—")

        system_box = QGroupBox("System Status")
        system_grid = QGridLayout()
        system_grid.setColumnStretch(0, 0)
        system_grid.setColumnStretch(1, 1)

        system_grid.addWidget(QLabel("Runtime:"), 0, 0)
        system_grid.addWidget(self.runtime_value, 0, 1)

        system_grid.addWidget(QLabel("STT Ready:"), 1, 0)
        system_grid.addWidget(self.stt_ready_value, 1, 1)

        system_grid.addWidget(QLabel("Wake Ready:"), 2, 0)
        system_grid.addWidget(self.wake_ready_value, 2, 1)

        system_grid.addWidget(QLabel("TTS Ready:"), 3, 0)
        system_grid.addWidget(self.tts_ready_status_value, 3, 1)

        system_grid.addWidget(QLabel("Devices Loaded:"), 4, 0)
        system_grid.addWidget(self.devices_value, 4, 1)

        system_box.setLayout(system_grid)

        voice_box = QGroupBox("Voice Activity")
        voice_grid = QGridLayout()
        voice_grid.setColumnStretch(0, 0)
        voice_grid.setColumnStretch(1, 1)

        voice_grid.addWidget(QLabel("Voice Pipeline:"), 0, 0)
        voice_grid.addWidget(self.pipeline_value, 0, 1)

        voice_grid.addWidget(QLabel("STT Engine:"), 1, 0)
        voice_grid.addWidget(self.stt_engine_value, 1, 1)

        voice_grid.addWidget(QLabel("Wake Engine:"), 2, 0)
        voice_grid.addWidget(self.wake_engine_value, 2, 1)

        voice_grid.addWidget(QLabel("Wake:"), 3, 0)
        voice_grid.addWidget(self.wake_value, 3, 1)

        voice_grid.addWidget(QLabel("Listening:"), 4, 0)
        voice_grid.addWidget(self.listening_value, 4, 1)

        voice_box.setLayout(voice_grid)

        command_box = QGroupBox("Command / Response")
        command_grid = QGridLayout()
        command_grid.setColumnStretch(0, 0)
        command_grid.setColumnStretch(1, 1)

        command_grid.addWidget(QLabel("Last Transcript:"), 0, 0)
        command_grid.addWidget(self.transcript_value, 0, 1)

        command_grid.addWidget(QLabel("Last Intent:"), 1, 0)
        command_grid.addWidget(self.intent_value, 1, 1)

        command_grid.addWidget(QLabel("Last Action:"), 2, 0)
        command_grid.addWidget(self.action_value, 2, 1)

        command_grid.addWidget(QLabel("Assistant Said:"), 3, 0)
        command_grid.addWidget(self.assistant_value, 3, 1)

        command_grid.addWidget(QLabel("TTS:"), 4, 0)
        command_grid.addWidget(self.tts_value, 4, 1)

        command_box.setLayout(command_grid)

        root = QVBoxLayout(self)
        root.addWidget(title)
        root.addWidget(system_box)
        root.addWidget(voice_box)
        root.addWidget(command_box)
        root.addStretch(1)

    def handle_event(self, topic: str, data: dict) -> None:
        data = data or {}

        if topic == "system.runtime_ready":
            ready = bool(data.get("ready", False))
            self.runtime_value.setText("ready" if ready else "not ready")
            return

        if topic == "system.stt_ready":
            ready = bool(data.get("ready", False))
            self.stt_ready_value.setText("ready" if ready else "not ready")
            return

        if topic == "system.wake_ready":
            ready = bool(data.get("ready", False))
            self.wake_ready_value.setText("ready" if ready else "not ready")
            return

        if topic == "system.tts_ready":
            ready = bool(data.get("ready", False))
            self.tts_ready_status_value.setText("ready" if ready else "not ready")
            return
        
        if topic == "ui.context.state":
            mode = str(data.get("mode", "")).upper()
            busy = bool(data.get("busy", False))

            if mode.endswith("IDLE"):
                self.wake_value.setText("waiting")
                self.listening_value.setText("idle")
                return

            if mode.endswith("LISTENING"):
                self.wake_value.setText("detected")
                self.listening_value.setText("listening")
                return

            if mode.endswith("WORKING"):
                self.wake_value.setText("waiting")
                self.listening_value.setText("processing")
                return

            if mode.endswith("SPEAKING"):
                self.wake_value.setText("waiting")
                self.listening_value.setText("idle")
                return

            if not busy:
                self.wake_value.setText("waiting")
                self.listening_value.setText("idle")
                return
        
        if topic == "ui.dashboard.refresh":
            self.runtime_value.setText("ready")
            self.stt_ready_value.setText("ready")
            self.wake_ready_value.setText("ready")
            self.tts_ready_status_value.setText("ready")
            return

        if topic == "voice.pipeline":
            state = str(data.get("state", "—"))
            stt = str(data.get("stt", "—"))
            wake = str(data.get("wake", "—"))

            self.pipeline_value.setText(state)
            self.stt_engine_value.setText(stt)
            self.wake_engine_value.setText(wake)

            state_l = state.strip().lower()
            if state_l in {"started", "idle", "ready", "waiting", "wake"}:
                self.wake_value.setText("waiting")
                self.listening_value.setText("idle")
            return
        
        if topic == "ui.devices.snapshot":
            devices = data.get("devices", [])
            count = len(devices) if isinstance(devices, list) else 0
            self.devices_value.setText(str(count))
            return

        if topic == "voice.wake":
            self.wake_value.setText("detected")
            return

        if topic == "stt.listening":
            phase = str(data.get("phase", "listening"))

            if phase == "wake_stt":
                self.listening_value.setText("listening")
            else:
                self.listening_value.setText(phase)
            return

        if topic == "voice.transcript":
            text = str(data.get("text", ""))
            conf = data.get("confidence")
            final = bool(data.get("final", False))

            suffix = []
            suffix.append("final" if final else "partial")
            if conf is not None:
                suffix.append(f"conf={conf:.2f}")

            if text:
                self.transcript_value.setText(f"{text} ({', '.join(suffix)})")
            else:
                self.transcript_value.setText(f"— ({', '.join(suffix)})")
            return

        if topic == "nlp.intent":
            name = str(data.get("name", "—"))
            conf = data.get("confidence")
            slots = data.get("slots", {})

            if conf is None:
                self.intent_value.setText(f"{name} | slots={slots}")
            else:
                self.intent_value.setText(f"{name} | conf={conf:.2f} | slots={slots}")
            return

        if topic == "action.requested":
            action = str(data.get("action", data.get("kind", "requested")))
            self.action_value.setText(f"requested | {action}")
            return

        if topic == "action.policy_decided":
            decision = data.get("decision", {})
            allowed = decision.get("allowed", None)

            if allowed is True:
                self.action_value.setText("policy: allowed")
            elif allowed is False:
                reason = str(decision.get("reason_code", "denied"))
                self.action_value.setText(f"policy: denied | {reason}")
            else:
                self.action_value.setText(f"policy: {decision}")
            return

        if topic == "action.executed":
            self.action_value.setText("executed")
            return

        if topic == "action.verified":
            verification = data.get("verification", {}) or {}
            verified = verification.get("verified", None)
            method = str(verification.get("method", ""))
            self.action_value.setText(f"verified={verified} | method={method}")
            self.wake_value.setText("waiting")
            self.listening_value.setText("idle")
            return

        if topic == "action.failed":
            stage = str(data.get("stage", "unknown"))
            code = str(data.get("code", "unknown"))
            self.action_value.setText(f"failed | stage={stage} | code={code}")
            self.wake_value.setText("waiting")
            self.listening_value.setText("idle")
            return
        
        if topic == "action.clarification_required":
            candidates = data.get("candidates", []) or []
            labels = [str(c.get("label", c.get("name", "?"))) for c in candidates if isinstance(c, dict)]

            if labels:
                self.action_value.setText("waiting for clarification | " + ", ".join(labels))
            else:
                self.action_value.setText("waiting for clarification")

            self.wake_value.setText("waiting")
            self.listening_value.setText("idle")
            return
        
        if topic == "assistant.say":
            text = str(data.get("text", "")).strip()
            self.assistant_value.setText(text or "—")
            self.wake_value.setText("waiting")
            self.listening_value.setText("idle")
            return

        if topic == "tts.started":
            self.tts_value.setText("speaking")
            return

        if topic == "tts.completed":
            self.tts_value.setText("idle")
            self.wake_value.setText("waiting")
            self.listening_value.setText("idle")
            return

        if topic == "tts.unavailable":
            reason = str(data.get("reason", "unavailable"))
            self.tts_value.setText(f"unavailable | {reason}")
            return
        
        if topic == "tts.failed":
            reason = str(data.get("reason", "failed"))
            self.tts_value.setText(f"failed | {reason}")
            self.wake_value.setText("waiting")
            self.listening_value.setText("idle")
            return