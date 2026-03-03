from __future__ import annotations

from PySide6.QtWidgets import QMainWindow, QTabWidget

from ui.dashboard.panel import DashboardPanel
from ui.logs.panel import LogsPanel


class MainWindow(QMainWindow):
    def __init__(self, bridge):
        super().__init__()
        self.setWindowTitle("JARED Command Center")
        self.resize(1200, 800)

        self._tabs = QTabWidget()
        self._dashboard = DashboardPanel()
        self._logs = LogsPanel()

        self._tabs.addTab(self._dashboard, "Dashboard")
        self._tabs.addTab(self._logs, "Logs")
        self.setCentralWidget(self._tabs)

        bridge.event_received.connect(self._route_event)

    def _route_event(self, topic: str, data: dict):
        # Fanout to panels
        self._dashboard.handle_event(topic, data)
        self._logs.handle_event(topic, data)