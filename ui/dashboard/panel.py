from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QGridLayout,
    QVBoxLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
)

class DashboardPanel(QWidget):
    def __init__(self, bus, parent=None) -> None:
        super().__init__(parent)
        self.bus = bus
        self._snapshot: dict = {}
        self._activity: list[str] = []

        title = QLabel("<b>System Dashboard</b>")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)

        title_row = QHBoxLayout()
        title_row.addWidget(title)
        title_row.addStretch(1)
        title_row.addWidget(refresh_btn)

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
        self.boot_total_value = QLabel("—")
        self.boot_stages_value = QLabel("—")
        self.activity = QTextEdit()
        self.activity.setReadOnly(True)

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

        system_grid.addWidget(QLabel("Boot Total:"), 5, 0)
        system_grid.addWidget(self.boot_total_value, 5, 1)

        system_grid.addWidget(QLabel("Boot Stages:"), 6, 0)
        system_grid.addWidget(self.boot_stages_value, 6, 1)

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

        activity_box = QGroupBox("Recent Activity")
        activity_layout = QVBoxLayout()
        activity_layout.addWidget(self.activity)
        activity_box.setLayout(activity_layout)

        root = QVBoxLayout(self)
        root.addLayout(title_row)
        root.addWidget(system_box)
        root.addWidget(voice_box)
        root.addWidget(command_box)
        root.addWidget(activity_box, 1)

    def _format_ms(self, ms: int) -> str:
        if ms >= 1000:
            return f"{ms / 1000.0:.1f}s"
        return f"{ms} ms"

    def refresh(self) -> None:
        self.bus.publish("ui.dashboard.refresh")

    def handle_event(self, topic: str, data: dict) -> None:
        data = data or {}

        if topic == "ui.dashboard.snapshot":
            self._snapshot = data

            runtime_ready = bool(data.get("runtime_ready", False))
            stt_ready = bool(data.get("stt_ready", False))
            wake_ready = bool(data.get("wake_ready", False))
            tts_ready = bool(data.get("tts_ready", False))

            self.runtime_value.setText("ready" if runtime_ready else "not ready")
            self.stt_ready_value.setText("ready" if stt_ready else "not ready")
            self.wake_ready_value.setText("ready" if wake_ready else "not ready")
            self.tts_ready_status_value.setText("ready" if tts_ready else "not ready")
            self.pipeline_value.setText(str(data.get("voice_pipeline_state", "—")))
            self.stt_engine_value.setText(str(data.get("stt_engine", "—")))
            self.wake_engine_value.setText(str(data.get("wake_engine", "—")))

            boot_total_ms = int(data.get("boot_total_ms", 0) or 0)
            boot_stages = data.get("boot_stages", []) or []

            if boot_total_ms > 0:
                self.boot_total_value.setText(self._format_ms(boot_total_ms))
            else:
                self.boot_total_value.setText("—")

            stage_parts = []
            for item in boot_stages:
                stage = str(item.get("stage", "")).strip()
                elapsed_ms = int(item.get("elapsed_ms", 0) or 0)
                if stage:
                    stage_parts.append(f"{stage}: {self._format_ms(elapsed_ms)}")

            self.boot_stages_value.setText(" | ".join(stage_parts) if stage_parts else "—")

            mode = str(data.get("context_mode", "")).upper()
            busy = bool(data.get("busy", False))

            if mode.endswith("LISTENING"):
                self.wake_value.setText("detected")
                self.listening_value.setText("listening")
            elif mode.endswith("WORKING"):
                self.wake_value.setText("waiting")
                self.listening_value.setText("processing")
            elif mode.endswith("SPEAKING"):
                self.wake_value.setText("waiting")
                self.listening_value.setText("idle")
            else:
                self.wake_value.setText("waiting")
                self.listening_value.setText("idle" if not busy else "busy")

            transcript = str(data.get("last_transcript", "")).strip()
            self.transcript_value.setText(transcript or "—")

            intent = data.get("intent")
            self.intent_value.setText(str(intent) if intent not in (None, "") else "—")

            action_summary = str(data.get("last_action_summary", "")).strip()
            action_status = str(data.get("last_action_status", "unknown")).strip()
            if action_summary:
                self.action_value.setText(f"{action_status} | {action_summary}")
            else:
                self.action_value.setText(action_status or "—")
            recent_activity = data.get("recent_activity", []) or []
            if isinstance(recent_activity, list):
                self.activity.setPlainText("\n".join(str(x) for x in recent_activity))
            else:
                self.activity.clear()

            self.activity.verticalScrollBar().setValue(
                self.activity.verticalScrollBar().maximum()
            )
            return
        
        if topic == "ui.devices.snapshot":
            devices = data.get("devices", [])
            count = len(devices) if isinstance(devices, list) else 0
            self.devices_value.setText(str(count))
            return
