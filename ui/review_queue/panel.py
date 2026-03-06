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
    QListWidget,
    QListWidgetItem,
    QTextEdit,
    QComboBox,
    QLineEdit,
)


class ReviewQueuePanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self._requests_by_id: dict[str, dict] = {}
        self._items: list[dict] = []
        self._pending_by_request_id: dict[str, set[str]] = {}

        title = QLabel("Review Queue")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.kind_filter = QComboBox()
        self.kind_filter.addItems([
            "All",
            "Action Failure",
            "Clarification Required",
            "Policy Denial",
        ])
        self.kind_filter.currentIndexChanged.connect(self._render)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Filter summary or details")
        self.search.textChanged.connect(self._render)

        clear_selected_btn = QPushButton("Clear Selected")
        clear_selected_btn.clicked.connect(self.clear_selected)

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear)

        top = QHBoxLayout()
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(QLabel("Type:"))
        top.addWidget(self.kind_filter)
        top.addWidget(QLabel("Search:"))
        top.addWidget(self.search, 2)
        top.addWidget(clear_selected_btn)
        top.addWidget(clear_btn)

        self.status = QLabel("Queued items: 0")

        self.listing = QListWidget()
        self.listing.currentRowChanged.connect(self._show_selected)

        self.details = QTextEdit()
        self.details.setReadOnly(True)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(self.status)
        root.addWidget(self.listing)
        root.addWidget(self.details)

    def clear(self) -> None:
        self._items.clear()
        self._pending_by_request_id.clear()
        self.listing.clear()
        self.details.clear()
        self.status.setText("Queued items: 0")

    def clear_selected(self) -> None:
        row = self.listing.currentRow()
        visible = self._visible_items()
        if row < 0 or row >= len(visible):
            return

        target_id = visible[row]["entry_id"]
        self._items = [item for item in self._items if item["entry_id"] != target_id]
        self._rebuild_pending_index()
        self._render()

    def _request_summary(self, request_id: str) -> str:
        item = self._requests_by_id.get(request_id, {}) or {}
        request = item.get("request", {}) or {}
        target = item.get("target", {}) or {}

        intent = str(request.get("intent_name", "unknown")).strip()
        slots = request.get("slots", {}) or {}
        state = str(slots.get("state", slots.get("power", slots.get("enabled", "")))).strip()

        room_name = "" if target.get("room_name") is None else str(target.get("room_name", "")).strip()
        device_name = "" if target.get("device_name") is None else str(target.get("device_name", "")).strip()
        device_id = "" if target.get("device_id") is None else str(target.get("device_id", "")).strip()

        target_parts = []
        if room_name:
            target_parts.append(room_name)
        if device_name:
            target_parts.append(device_name)
        elif device_id:
            target_parts.append(device_id)

        target_text = " ".join(target_parts).strip()

        parts = [intent]
        if state:
            parts.append(state)
        if target_text:
            parts.append(f"-> {target_text}")

        summary = " ".join(parts).strip()
        return summary or request_id or "unknown request"

    def handle_event(self, topic: str, data: dict) -> None:
        data = data or {}

        if topic == "action.requested":
            request = data.get("request", {}) or {}
            target = data.get("target", {}) or {}
            request_id = str(request.get("request_id", "")).strip()
            if request_id:
                self._requests_by_id[request_id] = {
                    "request": request,
                    "target": target,
                }
            return

        if topic == "action.verified":
            self._remove_request_items(str(data.get("request_id", "")).strip())
            return

        if topic == "action.failed":
            request_id = str(data.get("request_id", "")).strip()
            command = self._request_summary(request_id)
            stage = str(data.get("stage", "unknown"))
            code = str(data.get("code", "unknown"))
            details = str(data.get("details", "")).strip()

            summary = f"{command} | {stage} | {code}"
            if details:
                summary += f" | {details}"

            self._add_item(
                entry_id=f"action.failed:{request_id}:{stage}:{code}",
                request_id=request_id,
                kind="Action Failure",
                summary=summary,
                payload={"topic": topic, "command": command, **data},
            )
            return

        if topic == "action.policy_decided":
            decision = data.get("decision", {}) or {}
            if decision.get("allowed") is False:
                request_id = str(data.get("request_id", "")).strip()
                command = self._request_summary(request_id)
                reason = str(decision.get("reason_code", "DENIED"))

                self._add_item(
                    entry_id=f"action.policy_decided:{request_id}:{reason}",
                    request_id=request_id,
                    kind="Policy Denial",
                    summary=f"{command} | {reason}",
                    payload={"topic": topic, "command": command, **data},
                )
            return

        if topic == "action.clarification_required":
            candidates = data.get("candidates", []) or []
            labels = [str(c.get("label", c.get("name", "?"))) for c in candidates if isinstance(c, dict)]
            original_target = str(data.get("original_target", "")).strip()
            reply = str(data.get("reply", "")).strip()

            summary = f"target={original_target}" if original_target else "Clarification needed"
            if labels:
                summary += " | " + ", ".join(labels)
            if reply:
                summary += f" | reply={reply}"

            self._add_item(
                entry_id=f"action.clarification_required:{original_target}:{','.join(labels)}",
                request_id="",
                kind="Clarification Required",
                summary=summary,
                payload={"topic": topic, **data},
            )
            return

    def _add_item(self, *, entry_id: str, request_id: str, kind: str, summary: str, payload: dict) -> None:
        if any(item["entry_id"] == entry_id for item in self._items):
            return

        entry = {
            "entry_id": entry_id,
            "request_id": request_id,
            "kind": kind,
            "summary": summary,
            "payload": payload,
            "created_at": datetime.now().strftime("%H:%M:%S"),
        }
        self._items.append(entry)

        if request_id:
            self._pending_by_request_id.setdefault(request_id, set()).add(entry_id)

        self._render(select_entry_id=entry_id)

    def _remove_request_items(self, request_id: str) -> None:
        if not request_id:
            return
        ids = self._pending_by_request_id.pop(request_id, set())
        if not ids:
            return

        self._items = [item for item in self._items if item["entry_id"] not in ids]
        self._render()

    def _rebuild_pending_index(self) -> None:
        self._pending_by_request_id.clear()
        for item in self._items:
            request_id = item.get("request_id", "")
            entry_id = item.get("entry_id", "")
            if request_id and entry_id:
                self._pending_by_request_id.setdefault(request_id, set()).add(entry_id)

    def _visible_items(self) -> list[dict]:
        kind_filter = self.kind_filter.currentText()
        query = self.search.text().strip().lower()
        visible: list[dict] = []

        for item in self._items:
            if kind_filter != "All" and item["kind"] != kind_filter:
                continue

            haystack = json.dumps(item["payload"], sort_keys=True, ensure_ascii=False).lower()
            if query and query not in item["summary"].lower() and query not in haystack:
                continue

            visible.append(item)

        return visible

    def _render(self, *_args, select_entry_id: str | None = None) -> None:
        visible = self._visible_items()
        self.listing.clear()

        for item in visible:
            label = f"[{item['created_at']}] {item['kind']} — {item['summary']}"
            lw_item = QListWidgetItem(label)
            lw_item.setData(Qt.ItemDataRole.UserRole, item["entry_id"])
            self.listing.addItem(lw_item)

        self.status.setText(f"Queued items: {len(visible)} shown / {len(self._items)} total")

        if not visible:
            self.details.clear()
            return

        select_row = 0
        if select_entry_id:
            for idx, item in enumerate(visible):
                if item["entry_id"] == select_entry_id:
                    select_row = idx
                    break

        self.listing.setCurrentRow(select_row)

    def _show_selected(self, row: int) -> None:
        visible = self._visible_items()
        if row < 0 or row >= len(visible):
            self.details.clear()
            return

        entry = visible[row]
        self.details.setPlainText(
            json.dumps(entry["payload"], indent=2, sort_keys=True, ensure_ascii=False)
        )