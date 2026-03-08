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

        self.dashboard = DashboardPanel(bridge.bus)
        self.devices = DevicesPanel(bridge.bus)
        self.logs = LogsPanel()
        self.settings = SettingsPanel()
        self.review_queue = ReviewQueuePanel(bridge.bus)
        self._event_targets = [
            self.dashboard,
            self.devices,
            self.logs,
            self.settings,
            self.review_queue,
        ]
        

        tabs.addTab(self.dashboard, "Dashboard")
        tabs.addTab(self.devices, "Devices")
        tabs.addTab(self.logs, "Logs")
        tabs.addTab(self.settings, "Settings")
        tabs.addTab(self.review_queue, "Review Queue")

        self.setCentralWidget(tabs)

        bridge.event_received.connect(self._route_event)

    def _route_event(self, topic: str, data: dict) -> None:
        for target in self._event_targets:
            handler = getattr(target, "handle_event", None)
            if callable(handler):
                handler(topic, data)