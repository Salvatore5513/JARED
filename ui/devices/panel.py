from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QComboBox,
    QAbstractItemView,
    QHeaderView,
    QSplitter,
    QTextEdit,
)


class DevicesPanel(QWidget):
    def __init__(self, bus, parent=None) -> None:
        super().__init__(parent)
        self.bus = bus
        self._devices: list[dict] = []
        self._pending_by_device_id: dict[str, bool] = {}
        self._request_to_device_id: dict[str, str] = {}
        self._visible_device_rows: list[dict] = []

        title = QLabel("Devices")
        title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.search = QLineEdit()
        self.search.setPlaceholderText("Search device, room, driver, capability, template...")
        self.search.textChanged.connect(self._render)

        self.enabled_filter = QComboBox()
        self.enabled_filter.addItems(["All", "Enabled only", "Disabled only"])
        self.enabled_filter.currentIndexChanged.connect(self._render)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh)

        top = QHBoxLayout()
        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(QLabel("Search:"))
        top.addWidget(self.search, 2)
        top.addWidget(QLabel("Show:"))
        top.addWidget(self.enabled_filter)
        top.addWidget(refresh_btn)

        self.status = QLabel("Devices: (unknown)")

        self.table = QTableWidget(0, 10)
        self.table.setHorizontalHeaderLabels(
        [
            "device_id",
            "name",
            "room_id",
            "driver_kind",
            "enabled",
            "availability",
            "state",
            "capabilities",
            "template_id",
            "actions",
        ]
        )
        self.table.setSortingEnabled(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)

        for col in range(self.table.columnCount()):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)

        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # name

        self.table.setColumnHidden(0, True)  # device_id
        self.table.setColumnHidden(3, True)  # driver_kind
        self.table.setColumnHidden(7, True)  # capabilities
        self.table.setColumnHidden(8, True)  # template_id

        self.table.currentCellChanged.connect(self._show_selected_details)

        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setPlaceholderText("Select a device to view details...")

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.table)
        splitter.addWidget(self.details)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setChildrenCollapsible(False)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(self.status)
        root.addWidget(splitter, 1)

    def refresh(self) -> None:
        self.bus.publish("ui.devices.refresh")

    def handle_event(self, topic: str, data: dict) -> None:
        data = data or {}

        if topic == "ui.devices.snapshot":
            devices = data.get("devices", []) or []
            self._devices = devices if isinstance(devices, list) else []
            self._render()
            return

        if topic == "action.requested":
            request = data.get("request", {}) or {}
            device_id = str(request.get("device_id", "")).strip()
            request_id = str(request.get("request_id", "")).strip()

            if device_id:
                self._pending_by_device_id[device_id] = True
            if request_id and device_id:
                self._request_to_device_id[request_id] = device_id

            if device_id:
                self._render()
            return

        if topic in {"action.executed", "action.failed", "action.verified"}:
            request_id = str(data.get("request_id", "")).strip()
            device_id = self._request_to_device_id.pop(request_id, "")

            if device_id:
                self._pending_by_device_id[device_id] = False
                self._render()
            return

    def _display_group_for(self, d: dict) -> str:
        room_id = str(d.get("room_id", "")).strip().lower()

        # Milestone 4 UI grouping:
        # treat bench as part of the garage command-center view
        if room_id in {"garage", "bench"}:
            return "Garage"

        if not room_id:
            return "Unassigned"

        return room_id.replace("_", " ").title()
    
    def _display_name_for(self, d: dict) -> str:
        name = str(d.get("name", "")).strip()
        room_id = str(d.get("room_id", "")).strip().lower()
        device_id = str(d.get("device_id", "")).strip().lower()

        if device_id == "dev.garage.lights":
            return "Main Lights"

        if "door" in name.lower() or "door" in device_id:
            return "Door Motor"

        return name or "Unnamed Device"

    def _render(self) -> None:
        filtered: list[dict] = []
        query = self.search.text().strip().lower()
        enabled_mode = self.enabled_filter.currentText()
        self._visible_device_rows = []

        for d in self._devices:
            if not isinstance(d, dict):
                d = {"raw": repr(d)}

            enabled = bool(d.get("enabled", False))
            power_state = str(d.get("last_known_power_state", "unknown")).strip().lower()
            if power_state not in {"on", "off"}:
                power_state = "unknown"

            if enabled_mode == "Enabled only" and not enabled:
                continue
            if enabled_mode == "Disabled only" and enabled:
                continue

            caps = d.get("capabilities", {})
            if isinstance(caps, dict):
                caps_s = ", ".join(f"{k}={v}" for k, v in sorted(caps.items()))
            else:
                caps_s = str(caps)

            haystack = " | ".join(
                [
                    str(d.get("device_id", "")),
                    str(d.get("name", "")),
                    str(d.get("room_id", "")),
                    str(d.get("driver_kind", "")),
                    str(d.get("template_id", "")),
                    "enabled" if enabled else "disabled",
                    power_state,
                    caps_s,
                ]
            ).lower()

            if query and query not in haystack:
                continue

            item = dict(d)
            item["__caps_s"] = caps_s
            item["__power_state"] = power_state
            item["__display_group"] = self._display_group_for(d)
            item["__display_name"] = self._display_name_for(d)
            filtered.append(item)

        filtered.sort(key=lambda d: (str(d.get("__display_group", "")), str(d.get("__display_name", ""))))
            
        self.status.setText(f"Devices: {len(filtered)} shown / {len(self._devices)} total")

        self.table.setSortingEnabled(False)
        self.table.clearContents()
        self.table.setRowCount(0)

        current_room = None
        r = 0

        for d in filtered:
            room = str(d.get("__display_group", "")).strip()

            # Insert room header
            if room != current_room:
                self.table.insertRow(r)

                header = QTableWidgetItem(f"ROOM: {room.upper()}")
                header.setFlags(Qt.ItemFlag.ItemIsEnabled)
                header.setTextAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

                header.setBackground(QColor(28, 28, 28))
                header.setForeground(QColor(220, 220, 220))

                self.table.setSpan(r, 0, 1, self.table.columnCount())
                self.table.setItem(r,0,header)
                self.table.setRowHeight(r, 28)

                current_room = room
                r += 1

            self.table.insertRow(r)

            device_id = str(d.get("device_id", ""))
            is_pending = bool(self._pending_by_device_id.get(device_id, False))

            row_values = [
                str(d.get("device_id", "")),
                str(d.get("__display_name", "")),
                str(d.get("__display_group", "")),
                str(d.get("driver_kind", "")),
                "Yes" if d.get("enabled", False) else "No",
                str(d.get("last_known_availability", "unknown")).title(),
                str(d.get("__power_state", "unknown")).title(),
                str(d.get("__caps_s", "")),
                str(d.get("template_id", "")),
            ]

            for c, text in enumerate(row_values):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

                if is_pending:
                    item.setBackground(QColor(70, 55, 20))

                # Enabled badge
                if c == 4:
                    enabled = bool(d.get("enabled", False))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    if enabled:
                        item.setForeground(QColor(255,255,255))
                        item.setBackground(QColor(0,120,200))   # blue
                    else:
                        item.setForeground(QColor(255,255,255))
                        item.setBackground(QColor(80,80,80))    # dark gray

                if c == 5:
                    availability = str(d.get("last_known_availability", "unknown")).lower()
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    if availability == "online":
                        item.setForeground(QColor(255,255,255))
                        item.setBackground(QColor(0,140,0))
                    elif availability == "offline":
                        item.setForeground(QColor(255,255,255))
                        item.setBackground(QColor(170,0,0))
                    else:
                        item.setForeground(QColor(255,255,255))
                        item.setBackground(QColor(110,110,110))

                # State badge
                if c == 6:
                    state = str(d.get("__power_state", "unknown")).lower()

                    display_state = state.title()
                    if is_pending:
                        display_state += " (pending)"

                    item.setText(display_state)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    if is_pending:
                        item.setForeground(QColor(255,255,255))
                        item.setBackground(QColor(180,120,0))
                    elif state == "on":
                        item.setForeground(QColor(255,255,255))
                        item.setBackground(QColor(0,140,0))
                    elif state == "off":
                        item.setForeground(QColor(255,255,255))
                        item.setBackground(QColor(170,0,0))
                    else:
                        item.setForeground(QColor(255,255,255))
                        item.setBackground(QColor(110,110,110))

                self.table.setItem(r, c, item)

            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 0, 4, 0)
            actions_layout.setSpacing(4)

            power_state = str(d.get("__power_state", "unknown")).lower()
            enabled = bool(d.get("enabled", False))

            action_btn = QPushButton()

            if power_state == "on":
                normal_text = "Turn Off"
                target_state = "off"
            elif power_state == "off":
                normal_text = "Turn On"
                target_state = "on"
            else:
                normal_text = "Turn On"
                target_state = "on"

            action_btn.setText("Sending..." if is_pending else normal_text)
            action_btn.setEnabled(enabled and not is_pending)

            def _set_power(checked=False, dev=device_id, state=target_state):
                self.bus.publish("ui.device.set_power_request", device_id=dev, state=state)

            action_btn.clicked.connect(_set_power)

            actions_layout.addWidget(action_btn)
            self.table.setCellWidget(r, 9, actions_widget)
            self._visible_device_rows.append(d)
            r += 1

        self.table.resizeRowsToContents()

    def _show_selected_details(
        self,
        current_row: int,
        _current_col: int,
        _prev_row: int,
        _prev_col: int,
    ) -> None:
        if current_row < 0:
            self.details.clear()
            return

        device_rows_seen = -1

        for row in range(self.table.rowCount()):
            # room header rows are spanned across all columns
            if self.table.columnSpan(row, 0) == self.table.columnCount():
                continue

            device_rows_seen += 1

            if row == current_row:
                if 0 <= device_rows_seen < len(self._visible_device_rows):
                    d = self._visible_device_rows[device_rows_seen]
                    import json
                    self.details.setPlainText(
                        json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False)
                    )
                    return

        self.details.clear()
