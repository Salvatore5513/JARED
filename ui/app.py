from __future__ import annotations

import sys
import signal
import traceback

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from ui.components.event_bridge import EventBridge
from ui.main_window import MainWindow


def launch_ui(runtime) -> int:
    app = QApplication(sys.argv)

    # Make Ctrl+C work on Windows:
    # - handle SIGINT by quitting Qt
    # - run a small timer so Python gets a chance to process signals
    signal.signal(signal.SIGINT, lambda *_: app.quit())

    sig_timer = QTimer()
    sig_timer.timeout.connect(lambda: None)
    sig_timer.start(100)

    bridge = EventBridge(runtime.bus)
    win = MainWindow(bridge)
    win.show()

    def shutdown() -> None:
        try:
            if hasattr(runtime, "stop"):
                runtime.stop()
        except Exception:
            print("[ui] error during runtime.stop()")
            traceback.print_exc()

    app.aboutToQuit.connect(shutdown)

    return app.exec()