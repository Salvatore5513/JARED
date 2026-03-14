from __future__ import annotations

import json
from datetime import datetime
from html import escape

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
    QSpinBox,
    QButtonGroup,
)


class LogsPanel(QWidget):
    CATEGORY_ALL = "ALL"
    CATEGORY_VOICE = "VOICE"
    CATEGORY_DEVICE = "DEVICE"
    CATEGORY_ACTION = "ACTION"
    CATEGORY_SYSTEM = "SYSTEM"
    CATEGORY_ERROR = "ERROR"

    SEVERITY_INFO = "INFO"
    SEVERITY_SUCCESS = "SUCCESS"
    SEVERITY_WARNING = "WARNING"
    SEVERITY_ERROR = "ERROR"

    SEVERITY_COLORS = {
        SEVERITY_INFO: "#9aa0a6",
        SEVERITY_SUCCESS: "#34a853",
        SEVERITY_WARNING: "#f29900",
        SEVERITY_ERROR: "#ea4335",
    }

    CATEGORY_COLORS = {
        CATEGORY_ALL: "#9aa0a6",
        CATEGORY_VOICE: "#8ab4f8",
        CATEGORY_DEVICE: "#81c995",
        CATEGORY_ACTION: "#fdd663",
        CATEGORY_SYSTEM: "#c58af9",
        CATEGORY_ERROR: "#ea4335",
    }

    HIDDEN_BY_DEFAULT_TOPICS = {
        "ui.dashboard.snapshot",
        "ui.devices.snapshot",
        "ui.dashboard.refresh",
        "ui.devices.refresh",
        "ui.context.state",
        "voice.pipeline",
        "action.policy_decided",
        "action.verified",
        "device.availability.changed.confirmed",
    }

    TOPIC_PRIORITY = {
        "voice.pipeline": 5,
        "voice.wake": 10,
        "stt.listening": 20,
        "voice.transcript": 30,
        "nlp.intent": 40,
        "action.requested": 50,
        "action.policy_decided": 55,
        "action.executed": 60,
        "action.failed": 60,
        "assistant.say": 70,
        "tts.started": 80,
        "tts.completed": 90,
        "tts.failed": 90,
        "tts.unavailable": 90,
    }

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._entries: list[dict] = []
        self._paused = False
        self._selected_category = self.CATEGORY_ALL

        title = QLabel("Logs")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.topic_filter = QLineEdit()
        self.topic_filter.setPlaceholderText("Filter topic (example: action. or voice.)")
        self.topic_filter.textChanged.connect(self._render)

        self.text_filter = QLineEdit()
        self.text_filter.setPlaceholderText("Filter text")
        self.text_filter.textChanged.connect(self._render)

        self.show_payloads = QCheckBox("Show raw payloads")
        self.show_payloads.setChecked(False)
        self.show_payloads.toggled.connect(self._render)

        self.autoscroll = QCheckBox("Auto-scroll")
        self.autoscroll.setChecked(True)

        self.pause_btn = QPushButton("Pause")
        self.pause_btn.setCheckable(True)
        self.pause_btn.toggled.connect(self._toggle_pause)

        self.max_entries = QSpinBox()
        self.max_entries.setRange(100, 5000)
        self.max_entries.setSingleStep(100)
        self.max_entries.setValue(1000)
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
        top.addWidget(QLabel("Keep:"))
        top.addWidget(self.max_entries)
        top.addWidget(self.show_payloads)
        top.addWidget(self.autoscroll)
        top.addWidget(self.pause_btn)
        top.addWidget(clear_btn)

        self.category_buttons: dict[str, QPushButton] = {}
        self.category_group = QButtonGroup(self)
        self.category_group.setExclusive(True)

        category_bar = QHBoxLayout()
        category_bar.addWidget(QLabel("Category:"))

        for name in (
            self.CATEGORY_ALL,
            self.CATEGORY_VOICE,
            self.CATEGORY_DEVICE,
            self.CATEGORY_ACTION,
            self.CATEGORY_SYSTEM,
            self.CATEGORY_ERROR,
        ):
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, category=name: self._set_category(category))
            self.category_group.addButton(btn)
            self.category_buttons[name] = btn
            category_bar.addWidget(btn)

        self.category_buttons[self.CATEGORY_ALL].setChecked(True)
        category_bar.addStretch(1)

        self.status = QLabel("Entries: 0")

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addLayout(category_bar)
        root.addWidget(self.status)
        root.addWidget(self.output)

        self._apply_button_styles()
        self._render()

    def clear(self) -> None:
        self._entries.clear()
        self.output.clear()
        self.status.setText("Entries: 0")

    def handle_event(self, topic: str, data: dict) -> None:

        # sequence counter for ordering events
        if not hasattr(self, "_seq"):
            self._seq = 0
        self._seq += 1

        payload = data if data is not None else {}
        payload_json = self._safe_json(payload)
        category = self._classify_category(str(topic), payload)
        severity = self._classify_severity(str(topic), payload)
        summary = self._build_summary(str(topic), payload)

        entry = {
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "seq": self._seq,
            "topic": str(topic),
            "data": payload,
            "payload_json": payload_json,
            "category": category,
            "severity": severity,
            "summary": summary,
        }

        self._entries.append(entry)
        self._trim_entries()

        if not self._paused:
            self._render()
        else:
            self.status.setText(f"Entries: {len(self._entries)} total (paused)")

    def _toggle_pause(self, paused: bool) -> None:
        self._paused = paused
        self.pause_btn.setText("Resume" if paused else "Pause")
        if not paused:
            self._render()
        else:
            self.status.setText(f"Entries: {len(self._entries)} total (paused)")

    def _set_category(self, category: str) -> None:
        self._selected_category = category
        self._apply_button_styles()
        self._render()

    def _apply_button_styles(self) -> None:
        for name, btn in self.category_buttons.items():
            color = self.CATEGORY_COLORS.get(name, "#9aa0a6")
            checked = name == self._selected_category

            if checked:
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: {color};
                        color: #111111;
                        font-weight: 700;
                        border: 1px solid {color};
                        border-radius: 4px;
                        padding: 4px 10px;
                    }}
                    """
                )
            else:
                btn.setStyleSheet(
                    f"""
                    QPushButton {{
                        background-color: #202124;
                        color: {color};
                        border: 1px solid #3c4043;
                        border-radius: 4px;
                        padding: 4px 10px;
                    }}
                    QPushButton:hover {{
                        border: 1px solid {color};
                    }}
                    """
                )

    def _trim_entries(self) -> None:
        keep = int(self.max_entries.value())
        if len(self._entries) > keep:
            self._entries = self._entries[-keep:]

    def _trim_and_render(self) -> None:
        self._trim_entries()
        self._render()

    def _should_hide_by_default(self, topic: str, topic_filter_text: str) -> bool:
        topic_l = topic.lower().strip()

        if topic_l not in self.HIDDEN_BY_DEFAULT_TOPICS:
            return False

        if topic_filter_text and topic_filter_text in topic_l:
            return False

        return True

    def _render(self) -> None:
        topic_text = self.topic_filter.text().strip().lower()
        payload_text = self.text_filter.text().strip().lower()

        rendered_blocks: list[str] = []
        shown = 0

        sorted_entries = sorted(
            self._entries,
            key=lambda e: (
                e["timestamp"],
                self.TOPIC_PRIORITY.get(e["topic"], 500),
                e.get("seq", 0),
            ),
        )

        for entry in sorted_entries:
            topic = entry["topic"]
            payload_json = entry["payload_json"]
            summary = entry["summary"]
            category = entry["category"]

            if self._should_hide_by_default(topic, topic_text):
                continue

            if self._selected_category != self.CATEGORY_ALL and category != self._selected_category:
                continue

            searchable = f"{topic} {summary} {payload_json}".lower()

            if topic_text and topic_text not in topic.lower():
                continue

            if payload_text and payload_text not in searchable:
                continue

            rendered_blocks.append(self._render_entry_html(entry))
            shown += 1

        if rendered_blocks:
            html = (
                "<html><body style='background:#111111; color:#e8eaed; "
                "font-family:Consolas, Menlo, monospace; font-size:12px;'>"
                + "".join(rendered_blocks)
                + "</body></html>"
            )
        else:
            html = (
                "<html><body style='background:#111111; color:#9aa0a6; "
                "font-family:Consolas, Menlo, monospace; font-size:12px;'>"
                "<div style='padding:8px;'>No log entries match current filters.</div>"
                "</body></html>"
            )

        self.output.setHtml(html)

        paused_suffix = " (paused)" if self._paused else ""
        self.status.setText(
            f"Entries: {shown} shown / {len(self._entries)} total | "
            f"Category: {self._selected_category} | Keep: {self.max_entries.value()}{paused_suffix}"
        )

        if self.autoscroll.isChecked():
            cursor = self.output.textCursor()
            cursor.movePosition(cursor.MoveOperation.End)
            self.output.setTextCursor(cursor)
            self.output.ensureCursorVisible()

    def _render_entry_html(self, entry: dict) -> str:
        ts = escape(str(entry["timestamp"]))
        topic = escape(str(entry["topic"]))
        category = escape(str(entry["category"]))
        severity = str(entry["severity"])
        summary = escape(str(entry["summary"]))
        payload_json = escape(str(entry["payload_json"]))

        sev_color = self.SEVERITY_COLORS.get(severity, "#9aa0a6")
        show_payload = self.show_payloads.isChecked()

        payload_block = ""
        if show_payload:
            payload_block = (
                "<pre style='margin:6px 0 0 0; white-space:pre-wrap; color:#b8c1cc; "
                "background:#101010; border:1px solid #222; border-radius:4px; padding:6px;'>"
                f"{payload_json}</pre>"
            )

        return (
            "<div style='margin:0 0 6px 0; padding:8px; border:1px solid #2a2a2a; "
            "border-radius:6px; background:#171717;'>"
            f"<div style='margin-bottom:4px;'>"
            f"<span style='color:#9aa0a6;'>[{ts}]</span> "
            f"<span style='color:#8ab4f8; font-weight:600;'>{topic}</span> "
            f"<span style='color:#7f8c8d;'>|</span> "
            f"<span style='color:#c58af9;'>{category}</span> "
            f"<span style='color:#7f8c8d;'>|</span> "
            f"<span style='color:{sev_color}; font-weight:700;'>{severity}</span>"
            f"</div>"
            f"<div style='color:#e8eaed; font-size:13px; line-height:1.35;'>{summary}</div>"
            f"{payload_block}"
            "</div>"
        )

    def _safe_json(self, payload: object) -> str:
        try:
            return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False, default=str)
        except TypeError:
            return repr(payload)

    def _build_summary(self, topic: str, payload: dict) -> str:
        t = topic.lower()

        if t == "stt.listening":
            phase = str(payload.get("phase", "")).strip()
            return f"Listening{f' ({phase})' if phase else ''}"
        
        if t == "stt.skipped":
            reason = str(payload.get("reason", "")).strip()
            return f"STT skipped: {reason}" if reason else "STT skipped"

        if t == "voice.transcript":
            text = str(payload.get("text", "")).strip()
            conf = payload.get("confidence")
            if text and conf is not None:
                return f'Transcript: "{text}" ({self._fmt_conf(conf)})'
            if text:
                return f'Transcript: "{text}"'
            return "Transcript received"

        if t == "nlp.intent":
            name = str(payload.get("name", "")).strip() or "unknown"
            conf = payload.get("confidence")
            slots = payload.get("slots", {}) or {}
            slot_text = self._summarize_slots(slots)
            if conf is not None and slot_text:
                return f"Intent: {name} ({self._fmt_conf(conf)}) | {slot_text}"
            if conf is not None:
                return f"Intent: {name} ({self._fmt_conf(conf)})"
            if slot_text:
                return f"Intent: {name} | {slot_text}"
            return f"Intent: {name}"

        if t == "action.requested":
            request = payload.get("request", {}) or {}
            target = payload.get("target", {}) or {}

            intent_name = str(request.get("intent_name", "")).strip() or "unknown"
            slots = request.get("slots", {}) or {}
            state = str(slots.get("state", "")).strip()
            device_name = str(target.get("device_name", "")).strip()
            device_id = str(request.get("device_id", "")).strip()

            parts = [f"Requested: {intent_name}"]
            if state:
                parts.append(state)
            if device_name:
                parts.append(f"target={device_name}")
            elif device_id:
                parts.append(f"device={device_id}")

            return " | ".join(parts)
        
        if t == "action.clarification_required":
            kind = str(payload.get("kind", "")).strip()
            original_target = str(payload.get("original_target", "")).strip()
            candidates = payload.get("candidates", []) or []

            names = []
            for item in candidates:
                if isinstance(item, dict):
                    name = str(item.get("name", "")).strip()
                    if name:
                        names.append(name)
                elif item:
                    names.append(str(item))

            if names and original_target:
                return f'Clarification needed for "{original_target}": ' + ", ".join(names[:4])

            if names:
                return "Clarification needed: " + ", ".join(names[:4])

            if kind:
                return f"Clarification needed: {kind}"

            return "Clarification required"
        
        if t == "action.policy_decided":
            decision = payload.get("decision", {}) or {}
            allowed = decision.get("allowed")

            if allowed is True:
                return "Policy check passed"
            if allowed is False:
                reason = str(decision.get("reason", "")).strip()
                return f"Policy denied: {reason}" if reason else "Policy denied"

            return "Policy decision recorded"
        
        if t == "action.verified":
            verification = payload.get("verification", {}) or {}
            verified = verification.get("verified")

            if verified is True:
                return "Action verified"
            if verified is False:
                return "Action verification failed"

            return "Verification recorded"

        if t == "action.executed":
            driver_result = payload.get("driver_result", {}) or {}
            ok = bool(driver_result.get("ok", False))
            latency_ms = payload.get("latency_ms", None)

            text = "Action executed successfully" if ok else "Action execution returned failure"
            if latency_ms is not None:
                text += f" | latency={latency_ms} ms"
            return text

        if t == "action.failed":
            code = str(payload.get("code", "")).strip()
            details = str(payload.get("details", "")).strip() or str(payload.get("reason", "")).strip()

            if details and code:
                return f"Action failed: {details} [{code}]"
            if details:
                return f"Action failed: {details}"
            if code:
                return f"Action failed: [{code}]"
            return "Action failed"

        if t == "assistant.say":
            text = str(payload.get("text", "")).strip()
            return f'Assistant: "{text}"' if text else "Assistant response"

        if t == "voice.wake":
            return "Wake word detected"

        if t.startswith("tts."):
            return self._summarize_tts(topic, payload)
        
        if t == "device.state.changed.confirmed":
            device_id = str(payload.get("device_id", "")).strip()
            device_name = str(payload.get("device_name", "")).strip()
            state = str(payload.get("state", "")).strip()

            label = device_name or device_id or "device"
            if state:
                return f"{label} state confirmed: {state}"
            return f"{label} state change confirmed"

        if t == "device.availability.changed.confirmed":
            device_id = str(payload.get("device_id", "")).strip()
            device_name = str(payload.get("device_name", "")).strip()
            available = payload.get("available", None)

            label = device_name or device_id or "device"
            if available is True:
                return f"{label} availability confirmed: online"
            if available is False:
                return f"{label} availability confirmed: offline"
            return f"{label} availability updated"

        if t.startswith("device."):
            return self._summarize_device(topic, payload)

        if t.startswith("system."):
            ready = payload.get("ready")
            if ready is True:
                return f"{topic} ready"
            if ready is False:
                return f"{topic} not ready"

        if "confidence" in payload and "reason" in payload and len(payload) <= 3:
            conf = payload.get("confidence")
            reason = str(payload.get("reason", "")).strip()
            if conf is not None and reason:
                return f"{reason} ({self._fmt_conf(conf)})"

        return self._generic_summary(topic, payload)

    def _summarize_slots(self, slots: dict) -> str:
        if not isinstance(slots, dict) or not slots:
            return ""

        parts: list[str] = []
        for key in ("state", "target", "level", "room", "room_name"):
            value = slots.get(key)
            if value not in (None, "", []):
                parts.append(f"{key}={value}")

        if not parts:
            return ""

        return ", ".join(parts)

    def _summarize_tts(self, topic: str, payload: dict) -> str:
        t = topic.lower()
        if t == "tts.started":
            return "TTS started"
        if t == "tts.completed":
            return "TTS completed"
        if t == "tts.unavailable":
            reason = str(payload.get("reason", "unavailable")).strip()
            return f"TTS unavailable: {reason}"
        if t == "tts.failed":
            reason = str(payload.get("reason", "failed")).strip()
            return f"TTS failed: {reason}"
        return "TTS event"

    def _summarize_device(self, topic: str, payload: dict) -> str:
        name = str(payload.get("device_name", "")).strip()
        device_id = str(payload.get("device_id", "")).strip()
        state = str(payload.get("state", "")).strip()

        parts = [topic]
        if name:
            parts.append(f"name={name}")
        elif device_id:
            parts.append(f"id={device_id}")
        if state:
            parts.append(f"state={state}")
        return " | ".join(parts)

    def _generic_summary(self, topic: str, payload: dict) -> str:
        if not payload:
            return topic

        preferred_keys = [
            "text",
            "message",
            "details",
            "reason",
            "code",
            "name",
            "state",
            "status",
            "phase",
        ]

        parts: list[str] = []
        for key in preferred_keys:
            value = payload.get(key)
            if value not in (None, "", [], {}):
                parts.append(f"{key}={value}")

        if parts:
            return " | ".join(parts[:4])

        keys = list(payload.keys())[:4]
        return f"{topic} | keys={', '.join(str(k) for k in keys)}"

    def _fmt_conf(self, value) -> str:
        try:
            return f"{float(value) * 100:.0f}%"
        except Exception:
            return str(value)

    def _classify_category(self, topic: str, payload: dict) -> str:
        t = topic.lower()

        if self._looks_like_error(topic, payload):
            return self.CATEGORY_ERROR

        if t.startswith(("voice.", "stt.", "tts.", "nlp.", "assistant.")):
            return self.CATEGORY_VOICE

        if t.startswith(("device.", "devices.")):
            return self.CATEGORY_DEVICE

        if t.startswith(("action.", "review.")):
            return self.CATEGORY_ACTION

        if t.startswith(("system.", "ui.", "app.", "boot.", "ctx.")):
            return self.CATEGORY_SYSTEM

        return self.CATEGORY_SYSTEM

    def _classify_severity(self, topic: str, payload: dict) -> str:
        t = topic.lower()

        if self._looks_like_error(topic, payload):
            return self.SEVERITY_ERROR

        if any(word in t for word in ("warning", "warn", "retry", "expired")):
            return self.SEVERITY_WARNING

        if payload.get("ok") is True:
            return self.SEVERITY_SUCCESS

        driver_result = payload.get("driver_result")
        if isinstance(driver_result, dict) and driver_result.get("ok") is True:
            return self.SEVERITY_SUCCESS

        verification = payload.get("verification")
        if isinstance(verification, dict) and verification.get("verified") is True:
            return self.SEVERITY_SUCCESS

        if any(word in t for word in ("executed", "verified", "approved", "completed", "online", "connected")):
            return self.SEVERITY_SUCCESS

        return self.SEVERITY_INFO

    def _looks_like_error(self, topic: str, payload: dict) -> bool:
        t = topic.lower()

        if any(word in t for word in ("error", "failed", "denied", "exception", "critical")):
            return True

        if payload.get("ok") is False:
            return True

        if payload.get("success") is False:
            return True

        if payload.get("error"):
            return True

        if payload.get("exception"):
            return True

        if payload.get("code") in {"ERROR", "FAILED", "VERIFY_FAILED", "NO_DRIVER", "DENY_UNKNOWN_DEVICE"}:
            return True

        driver_result = payload.get("driver_result")
        if isinstance(driver_result, dict):
            if driver_result.get("ok") is False:
                return True
            if driver_result.get("driver_code") in {"NO_DRIVER", "ERROR", "FAILED"}:
                return True

        return False