from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
from typing import Optional

from core.config.manager import load_config


class NetPolicy:
    def __init__(self, *, config=None, audit_file: Optional[Path] = None):
        # Backward compatible: same behavior as before if config not provided.
        if config is None:
            config = load_config()

        # If offline_only = True → allow_internet = False
        self.allow_internet = not getattr(config, "offline_only", True)

        # Prefer config.data_dir/audit if available, otherwise fallback to repo root
        if audit_file is not None:
            self._audit_file = audit_file
        else:
            data_dir = getattr(config, "data_dir", None)
            if data_dir:
                self._audit_file = Path(data_dir) / "audit" / "netpolicy_audit.log"
            else:
                self._audit_file = Path("netpolicy_audit.log")

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
        try:
            self._audit_file.parent.mkdir(parents=True, exist_ok=True)
            with self._audit_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            # Never crash JARED because audit logging failed.
            pass