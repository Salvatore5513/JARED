from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel


class DashboardPanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.mode = QLabel("Mode: (unknown)")
        self.wake = QLabel("Wake: (none)")
        self.transcript = QLabel("Transcript: (none)")
        self.intent = QLabel("Intent: (none)")
        self.action = QLabel("Last Action: (none)")

        layout.addWidget(self.mode)
        layout.addWidget(self.wake)
        layout.addWidget(self.transcript)
        layout.addWidget(self.intent)
        layout.addWidget(self.action)

    def handle_event(self, topic: str, data: dict):
        # Wake indicators
        if topic.startswith("voice.wake"):
            self.wake.setText(f"Wake: {topic} {data}")
            return

        # Transcript
        if topic == "voice.transcript":
            txt = data.get("text") or data.get("transcript") or str(data)
            self.transcript.setText(f"Transcript: {txt}")
            return

        # Intent (depends on your NLP event naming)
        if topic.startswith("nlp.intent"):
            self.intent.setText(f"Intent: {data}")
            return

        # Action lifecycle
        if topic.startswith("action."):
            self.action.setText(f"Last Action: {topic} {data}")
            return

        # Context/mode if you emit it (optional)
        if topic.startswith("ctx."):
            self.mode.setText(f"Mode: {topic} {data}")
            return