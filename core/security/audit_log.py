from __future__ import annotations

import json
import os
import sqlite3
import time
import dataclasses
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional, List, Tuple


def _now_ms() -> int:
    return int(time.time() * 1000)


import dataclasses
from typing import Any

def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None

    if dataclasses.is_dataclass(value):
        # Pylance: is_dataclass() can be true for dataclass *types* too
        if isinstance(value, type):
            return str(value)  # or value.__name__
        return _to_jsonable(dataclasses.asdict(value))

    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    return str(value)


class AuditLog:
    """
    Local, append-only audit log stored in SQLite.

    Milestone 3 goals:
      - never fail silently
      - never block core pipeline if logging fails (best-effort)
      - keep schema simple and queryable
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True) if os.path.dirname(db_path) else None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts_ms INTEGER NOT NULL,
                    request_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    json TEXT NOT NULL
                );
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON audit_log(ts_ms);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_req ON audit_log(request_id);")

    def write(
        self,
        *,
        event_type: str,
        request_id: str,
        summary: str,
        record: Dict[str, Any],
        ts_ms: Optional[int] = None,
    ) -> None:
        """
        Best-effort append. Should never crash the app.
        """
        try:
            payload = _to_jsonable(record)
            blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            t = _now_ms() if ts_ms is None else int(ts_ms)
            with self._connect() as conn:
                conn.execute(
                    "INSERT INTO audit_log (ts_ms, request_id, event_type, summary, json) VALUES (?, ?, ?, ?, ?)",
                    (t, str(request_id), str(event_type), str(summary), blob),
                )
        except Exception:
            # Intentionally swallow; logging must not bring down the pipeline.
            # You can later route this to core logger if you want.
            pass

    def tail(self, limit: int = 50) -> List[Tuple[int, int, str, str, str]]:
        """
        Returns rows: (id, ts_ms, request_id, event_type, summary)
        """
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT id, ts_ms, request_id, event_type, summary FROM audit_log ORDER BY id DESC LIMIT ?",
                (int(limit),),
            )
            return list(cur.fetchall())

    def read_json(self, audit_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cur = conn.execute("SELECT json FROM audit_log WHERE id = ?", (int(audit_id),))
            row = cur.fetchone()
            if not row:
                return None
            try:
                return json.loads(row[0])
            except Exception:
                return None