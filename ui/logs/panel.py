from __future__ import annotations

import json
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QLineEdit,
    QCheckBox,
    QComboBox,
    QSpinBox,
)


class LogsPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._entries: list[dict] = []
        self._paused = False

        title = QLabel("Logs")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.topic_filter = QLineEdit()
        self.topic_filter.setPlaceholderText("Filter topic (example: action. or ui.)")
        self.topic_filter.textChanged.connect(self._render)

        self.text_filter = QLineEdit()
        self.text_filter.setPlaceholderText("Filter payload text")
        self.text_filter.textChanged.connect(self._render)

        self.domain_filter = QComboBox()
        self.domain_filter.addItems(["All domains", "action", "assistant", "nlp", "stt", "system", "tts", "ui", "voice"])
        self.domain_filter.currentIndexChanged.connect(self._render)

        self.autoscroll = QCheckBox("Auto-scroll")
        self.autoscroll.setChecked(True)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.toggled.connect(self._toggle_pause)

        self.max_entries = QSpinBox()
        self.max_entries.setRange(50, 5000)
        self.max_entries.setSingleStep(50)
        self.max_entries.setValue(500)
        self.max_entries.valueChanged.connect(self._trim_and_render)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear)

        top = QHBoxLayout()
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(QLabel("Topic:"))
        top.addWidget(self.topic_filter, 2)
        top.addWidget(QLabel("Text:"))
        top.addWidget(self.text_filter, 2)
        top.addWidget(QLabel("Domain:"))
        top.addWidget(self.domain_filter)
        top.addWidget(QLabel("Keep:"))
        top.addWidget(self.max_entries)
        top.addWidget(self.autoscroll)
        top.addWidget(self.pause_btn)
        top.addWidget(clear_btn)

        self.status = QLabel("Entries: 0")

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(self.status)
        root.addWidget(self.output)

    def clear(self) -> None:
        self._entries.clear()
        self.output.clear()
        self.status.setText("Entries: 0")

    def handle_event(self, topic: str, data: dict) -> None:
        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "topic": str(topic),
            "data": data if data is not None else {},
        }
        self._entries.append(entry)
        self._trim_entries()

        if not self._paused:
            self._render()
        else:
            self.status.setText(f"Entries: {len(self._entries)} (paused)")

    def _toggle_pause(self, paused: bool) -> None:
        self._paused = paused
        self.pause_btn.setText("Resume" if paused else "Pause")
        if not paused:
            self._render()
        else:
            self.status.setText(f"Entries: {len(self._entries)} (paused)")

    def _trim_entries(self) -> None:
        keep = int(self.max_entries.value())
        if len(self._entries) > keep:
            self._entries = self._entries[-keep:]

    def _trim_and_render(self) -> None:
        self._trim_entries()
        self._render()

    def _render(self) -> None:
        topic_text = self.topic_filter.text().strip().lower()
        payload_text = self.text_filter.text().strip().lower()
        selected_domain = self.domain_filter.currentText()

        rendered_blocks: list[str] = []
        shown = 0

        for entry in self._entries:
            topic = entry["topic"]
            payload = entry["data"]
            domain = topic.split(".", 1)[0] if "." in topic else topic

            if selected_domain != "All domains" and domain != selected_domain:
                continue

            if topic_text and topic_text not in topic.lower():
                continue

            try:
                payload_json = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False)
            except TypeError:
                payload_json = repr(payload)

            if payload_text and payload_text not in payload_json.lower() and payload_text not in topic.lower():
                continue

            rendered_blocks.append(
                f"[{entry['timestamp']}] {topic}\n{payload_json}\n" + ("-" * 60)
            )
            shown += 1

        self.output.setPlainText("\n".join(rendered_blocks))
        self.status.setText(f"Entries: {shown} shown / {len(self._entries)} total")

        if self.autoscroll.isChecked():
            cursor = self.output.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.output.setTextCursor(cursor)
            self.output.ensureCursorVisible()
