from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QGridLayout, QLabel, QVBoxLayout


class SettingsPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        title = QLabel("Settings")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.offline_value = QLabel("—")
        self.stt_value = QLabel("—")
        self.wake_value = QLabel("—")
        self.tts_value = QLabel("—")
        self.pipeline_value = QLabel("—")

        grid = QGridLayout()
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)

        grid.addWidget(QLabel("Offline Only:"), 0, 0)
        grid.addWidget(self.offline_value, 0, 1)

        grid.addWidget(QLabel("STT Engine:"), 1, 0)
        grid.addWidget(self.stt_value, 1, 1)

        grid.addWidget(QLabel("Wake Engine:"), 2, 0)
        grid.addWidget(self.wake_value, 2, 1)

        grid.addWidget(QLabel("TTS State:"), 3, 0)
        grid.addWidget(self.tts_value, 3, 1)

        grid.addWidget(QLabel("Pipeline State:"), 4, 0)
        grid.addWidget(self.pipeline_value, 4, 1)

        root = QVBoxLayout(self)
        root.addWidget(title)
        root.addLayout(grid)
        root.addStretch(1)

    def handle_event(self, topic: str, data: dict) -> None:
        data = data or {}

        if topic == "voice.pipeline":
            self.pipeline_value.setText(str(data.get("state", "—")))
            self.stt_value.setText(str(data.get("stt", "—")))
            self.wake_value.setText(str(data.get("wake", "—")))
            return

        if topic == "tts.started":
            self.tts_value.setText("speaking")
            return

        if topic == "tts.completed":
            self.tts_value.setText("idle")
            return

        if topic == "tts.unavailable":
            reason = str(data.get("reason", "unavailable"))
            self.tts_value.setText(f"unavailable | {reason}")
            return

        if topic == "system.config":
            self.offline_value.setText(str(data.get("offline_only", "—")))
            return