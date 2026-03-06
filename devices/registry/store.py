from __future__ import annotations

import json
import os
import sqlite3
from typing import Any, Dict, Optional, List

from devices.registry.models import Room, DeviceTemplate, DeviceRecord, DeviceTarget


class RegistryStore:
    """
    SQLite-backed device registry.

    Milestone 3 focus:
      - schema + resolve_device()
      - basic CRUD helpers
      - keep it simple and reliable
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True) if os.path.dirname(db_path) else None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rooms (
                    room_id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS device_templates (
                    template_id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    driver_kind TEXT NOT NULL,
                    capabilities_json TEXT NOT NULL
                );
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS devices (
                    device_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    room_id TEXT NOT NULL,
                    template_id TEXT NOT NULL,
                    driver_config_json TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    FOREIGN KEY(room_id) REFERENCES rooms(room_id),
                    FOREIGN KEY(template_id) REFERENCES device_templates(template_id)
                );
                """
            )
            conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_devices_room_name ON devices(room_id, name);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_devices_enabled ON devices(enabled);")

    # -----------------------------
    # Helpers
    # -----------------------------

    @staticmethod
    def _dumps(obj: Dict[str, Any]) -> str:
        return json.dumps(obj or {}, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _loads(text: str) -> Dict[str, Any]:
        if not text:
            return {}
        try:
            v = json.loads(text)
            return v if isinstance(v, dict) else {}
        except Exception:
            return {}

    # -----------------------------
    # Rooms
    # -----------------------------

    def upsert_room(self, room: Room) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO rooms (room_id, name)
                VALUES (?, ?)
                ON CONFLICT(room_id) DO UPDATE SET name=excluded.name
                """,
                (room.room_id, room.name),
            )

    def get_room_by_id(self, room_id: str) -> Optional[Room]:
        with self._connect() as conn:
            row = conn.execute("SELECT room_id, name FROM rooms WHERE room_id=?", (room_id,)).fetchone()
            if not row:
                return None
            return Room(room_id=row["room_id"], name=row["name"])

    def get_room_by_name(self, room_name: str) -> Optional[Room]:
        with self._connect() as conn:
            row = conn.execute("SELECT room_id, name FROM rooms WHERE lower(name)=lower(?)", (room_name,)).fetchone()
            if not row:
                return None
            return Room(room_id=row["room_id"], name=row["name"])
        
    def get_template_by_name(self, template_name: str) -> Optional[DeviceTemplate]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT template_id, name, driver_kind, capabilities_json FROM device_templates WHERE lower(name)=lower(?)",
                (template_name,),
            ).fetchone()
            if not row:
                return None
            return DeviceTemplate(
                template_id=row["template_id"],
                name=row["name"],
                driver_kind=row["driver_kind"],
                capabilities=self._loads(row["capabilities_json"]),
            )

    # -----------------------------
    # Templates
    # -----------------------------

    def upsert_template(self, tpl: DeviceTemplate) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO device_templates (template_id, name, driver_kind, capabilities_json)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(template_id) DO UPDATE SET
                    name=excluded.name,
                    driver_kind=excluded.driver_kind,
                    capabilities_json=excluded.capabilities_json
                """,
                (tpl.template_id, tpl.name, tpl.driver_kind, self._dumps(tpl.capabilities)),
            )

    def get_template(self, template_id: str) -> Optional[DeviceTemplate]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT template_id, name, driver_kind, capabilities_json FROM device_templates WHERE template_id=?",
                (template_id,),
            ).fetchone()
            if not row:
                return None
            return DeviceTemplate(
                template_id=row["template_id"],
                name=row["name"],
                driver_kind=row["driver_kind"],
                capabilities=self._loads(row["capabilities_json"]),
            )

    # -----------------------------
    # Devices
    # -----------------------------

    def upsert_device(
        self,
        *,
        device_id: str,
        name: str,
        room_id: str,
        template_id: str,
        driver_config: Dict[str, Any],
        enabled: bool = True,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO devices (device_id, name, room_id, template_id, driver_config_json, enabled)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(device_id) DO UPDATE SET
                    name=excluded.name,
                    room_id=excluded.room_id,
                    template_id=excluded.template_id,
                    driver_config_json=excluded.driver_config_json,
                    enabled=excluded.enabled
                """,
                (device_id, name, room_id, template_id, self._dumps(driver_config), 1 if enabled else 0),
            )

    def set_device_enabled(self, device_id: str, enabled: bool) -> None:
        with self._connect() as conn:
            conn.execute("UPDATE devices SET enabled=? WHERE device_id=?", (1 if enabled else 0, device_id))

    def get_device(self, device_id: str) -> Optional[DeviceRecord]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT d.device_id, d.name, d.room_id, d.template_id, d.driver_config_json, d.enabled,
                       t.driver_kind, t.capabilities_json
                FROM devices d
                JOIN device_templates t ON t.template_id = d.template_id
                WHERE d.device_id = ?
                """,
                (device_id,),
            ).fetchone()
            if not row:
                return None
            return DeviceRecord(
                device_id=row["device_id"],
                name=row["name"],
                room_id=row["room_id"],
                template_id=row["template_id"],
                driver_kind=row["driver_kind"],
                capabilities=self._loads(row["capabilities_json"]),
                driver_config=self._loads(row["driver_config_json"]),
                enabled=bool(row["enabled"]),
            )
        
    def list_devices(self, *, enabled_only: bool = False) -> List[DeviceRecord]:
        with self._connect() as conn:
            if enabled_only:
                rows = conn.execute(
                    """
                    SELECT d.device_id, d.name, d.room_id, d.template_id, d.driver_config_json, d.enabled,
                        t.driver_kind, t.capabilities_json
                    FROM devices d
                    JOIN device_templates t ON t.template_id = d.template_id
                    WHERE d.enabled=1
                    ORDER BY d.room_id, d.name
                    """
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT d.device_id, d.name, d.room_id, d.template_id, d.driver_config_json, d.enabled,
                        t.driver_kind, t.capabilities_json
                    FROM devices d
                    JOIN device_templates t ON t.template_id = d.template_id
                    ORDER BY d.room_id, d.name
                    """
                ).fetchall()

            out: List[DeviceRecord] = []
            for row in rows:
                out.append(
                    DeviceRecord(
                        device_id=row["device_id"],
                        name=row["name"],
                        room_id=row["room_id"],
                        template_id=row["template_id"],
                        driver_kind=row["driver_kind"],
                        capabilities=self._loads(row["capabilities_json"]),
                        driver_config=self._loads(row["driver_config_json"]),
                        enabled=bool(row["enabled"]),
                    )
                )
            return out
        
    def resolve_candidates(self, target: DeviceTarget) -> List[DeviceRecord]:
        """
        Return all enabled devices matching the target.
        Used so DeviceManager can detect ambiguity instead of silently picking one.
        """
        out: List[DeviceRecord] = []

        # 1) Direct by device_id
        if target.device_id:
            rec = self.get_device(target.device_id)
            if rec and rec.enabled:
                out.append(rec)
            return out

        if not target.device_name:
            return out

        wanted = str(target.device_name or "").strip().lower()

        # Resolve room (optional)
        room_id = target.room_id
        if not room_id and target.room_name:
            room = self.get_room_by_name(target.room_name)
            room_id = room.room_id if room else None

        with self._connect() as conn:
            if room_id:
                rows = conn.execute(
                    """
                    SELECT d.device_id, d.name, d.room_id, d.template_id, d.driver_config_json, d.enabled,
                           t.driver_kind, t.capabilities_json
                    FROM devices d
                    JOIN device_templates t ON t.template_id = d.template_id
                    WHERE d.enabled=1 AND d.room_id=?
                    ORDER BY d.name
                    """,
                    (room_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT d.device_id, d.name, d.room_id, d.template_id, d.driver_config_json, d.enabled,
                           t.driver_kind, t.capabilities_json
                    FROM devices d
                    JOIN device_templates t ON t.template_id = d.template_id
                    WHERE d.enabled=1
                    ORDER BY d.room_id, d.name
                    """
                ).fetchall()

            exact = []
            suffix = []

            for r in rows:
                name_l = str(r["name"] or "").strip().lower()
                if name_l == wanted:
                    exact.append(r)
                elif name_l.endswith(" " + wanted):
                    suffix.append(r)

            chosen = exact if exact else suffix

            for row in chosen:
                out.append(
                    DeviceRecord(
                        device_id=row["device_id"],
                        name=row["name"],
                        room_id=row["room_id"],
                        template_id=row["template_id"],
                        driver_kind=row["driver_kind"],
                        capabilities=self._loads(row["capabilities_json"]),
                        driver_config=self._loads(row["driver_config_json"]),
                        enabled=bool(row["enabled"]),
                    )
                )

        return out

    def resolve_device(self, target: DeviceTarget) -> Optional[DeviceRecord]:
        """
        Critical Milestone 3 method:
          - If device_id provided: return that device (if enabled)
          - Else resolve room (room_id or room_name) and device_name
        """
        # 1) Direct by device_id
        matches = self.resolve_candidates(target)
        if len(matches) == 1:
            return matches[0]
        return None