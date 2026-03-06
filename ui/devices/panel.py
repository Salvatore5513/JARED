from __future__ import annotations

from PySide6.QtCore import Qt
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
)


class DevicesPanel(QWidget):
    def __init__(self, bus, parent=None) -> None:
        super().__init__(parent)
        self.bus = bus
        self._devices: list[dict] = []

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

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["device_id", "name", "room_id", "driver_kind", "enabled", "capabilities", "template_id"]
        )
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)

        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(self.status)
        root.addWidget(self.table)

    def refresh(self) -> None:
        self.bus.publish("ui.devices.refresh")

    def handle_event(self, topic: str, data: dict) -> None:
        if topic != "ui.devices.snapshot":
            return

        devices = (data or {}).get("devices", []) or []
        self._devices = devices if isinstance(devices, list) else []
        self._render()

    def _render(self) -> None:
        filtered: list[dict] = []
        query = self.search.text().strip().lower()
        enabled_mode = self.enabled_filter.currentText()

        for d in self._devices:
            if not isinstance(d, dict):
                d = {"raw": repr(d)}

            enabled = bool(d.get("enabled", False))
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
                    caps_s,
                ]
            ).lower()

            if query and query not in haystack:
                continue

            item = dict(d)
            item["__caps_s"] = caps_s
            filtered.append(item)

        self.status.setText(f"Devices: {len(filtered)} shown / {len(self._devices)} total")

        was_sorting = self.table.isSortingEnabled()
        self.table.setSortingEnabled(False)
        self.table.clearContents()
        self.table.setRowCount(len(filtered))

        for r, d in enumerate(filtered):
            row_values = [
                str(d.get("device_id", "")),
                str(d.get("name", "")),
                str(d.get("room_id", "")),
                str(d.get("driver_kind", "")),
                "Yes" if d.get("enabled", False) else "No",
                str(d.get("__caps_s", "")),
                str(d.get("template_id", "")),
            ]

            for c, text in enumerate(row_values):
                item = QTableWidgetItem(text)
                item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c, item)

        self.table.setSortingEnabled(was_sorting)
        self.table.resizeRowsToContents()
