from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

from ui.dashboard.panel import DashboardPanel
from ui.logs.panel import LogsPanel
from ui.devices.panel import DevicesPanel
from ui.settings.panel import SettingsPanel
from ui.review_queue.panel import ReviewQueuePanel


class MainWindow(QMainWindow):
    def __init__(self, bridge):
        super().__init__()
        self.setWindowTitle("JARED Command Center")
        self.resize(1200, 800)

        tabs = QTabWidget()

        self.dashboard = DashboardPanel()
        self.devices = DevicesPanel(bridge.bus)
        self.logs = LogsPanel()
        self.settings = SettingsPanel()
        self.review_queue = ReviewQueuePanel()

        tabs.addTab(self.dashboard, "Dashboard")
        tabs.addTab(self.devices, "Devices")
        tabs.addTab(self.logs, "Logs")
        tabs.addTab(self.settings, "Settings")
        tabs.addTab(self.review_queue, "Review Queue")

        self.setCentralWidget(tabs)

        bridge.event_received.connect(self._route_event)

    def _route_event(self, topic: str, data: dict):
        if hasattr(self.dashboard, "handle_event"):
            self.dashboard.handle_event(topic, data)

        if hasattr(self.devices, "handle_event"):
            self.devices.handle_event(topic, data)

        if hasattr(self.logs, "handle_event"):
            self.logs.handle_event(topic, data)

        if hasattr(self.settings, "handle_event"):
            self.settings.handle_event(topic, data)

        if hasattr(self.review_queue, "handle_event"):
            self.review_queue.handle_event(topic, data)