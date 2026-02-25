from __future__ import annotations
from datetime import datetime
from pathlib import Path
import json

from core.config.manager import load_config


AUDIT_FILE = Path("netpolicy_audit.log")


class NetPolicy:
    def __init__(self):
        config = load_config()
        # If offline_only = True → allow_internet = False
        self.allow_internet = not config.offline_only

    def check_outbound(self, url: str) -> None:
        if not self.allow_internet:
            self._log_block(url)
            raise RuntimeError(
                f"Outbound network blocked by NetPolicy (offline mode): {url}"
            )

    def _log_block(self, url: str) -> None:
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "blocked_url": url,
        }
        with AUDIT_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
