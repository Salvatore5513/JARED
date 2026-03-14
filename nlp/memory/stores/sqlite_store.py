from __future__ import annotations

import sqlite3
import threading
import time
from pathlib import Path


DEFAULT_PROJECT_ID = "default"


class MemoryStore:
    """
    SQLite-backed schema owner for Milestone 5 memory tables.

    Step 1 responsibilities only:
    - open SQLite connection
    - ensure memory tables exist
    - seed a default project scope
    """

    def __init__(self, db_path: str | Path, *, default_project_id: str = DEFAULT_PROJECT_ID) -> None:
        self.db_path = str(db_path)
        self.default_project_id = default_project_id
        self._lock = threading.RLock()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def ensure_schema(self) -> None:
        with self._lock:
            with self._connect() as conn:
                conn.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS memory_projects (
                        project_id TEXT PRIMARY KEY,
                        name TEXT NOT NULL,
                        kind TEXT NOT NULL DEFAULT 'general',
                        is_active INTEGER NOT NULL DEFAULT 0,
                        created_ts REAL NOT NULL,
                        updated_ts REAL NOT NULL
                    );

                    CREATE TABLE IF NOT EXISTS memory_command_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id TEXT NOT NULL,
                        ts REAL NOT NULL,
                        source TEXT NOT NULL DEFAULT 'voice',
                        source_endpoint_id TEXT,
                        room_id TEXT,
                        request_id TEXT,
                        raw_text TEXT NOT NULL,
                        normalized_text TEXT,
                        intent_name TEXT,
                        intent_confidence REAL,
                        device_id TEXT,
                        outcome TEXT,
                        slots_json TEXT NOT NULL DEFAULT '{}',
                        FOREIGN KEY(project_id) REFERENCES memory_projects(project_id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS memory_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id TEXT NOT NULL,
                        pref_scope TEXT NOT NULL DEFAULT 'global',
                        preference_key TEXT NOT NULL,
                        preference_value TEXT,
                        value_json TEXT NOT NULL DEFAULT '{}',
                        source TEXT NOT NULL DEFAULT 'manual',
                        confidence REAL NOT NULL DEFAULT 1.0,
                        is_active INTEGER NOT NULL DEFAULT 1,
                        created_ts REAL NOT NULL,
                        updated_ts REAL NOT NULL,
                        FOREIGN KEY(project_id) REFERENCES memory_projects(project_id) ON DELETE CASCADE,
                        UNIQUE(project_id, pref_scope, preference_key)
                    );

                    CREATE TABLE IF NOT EXISTS memory_device_aliases (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id TEXT NOT NULL,
                        alias TEXT NOT NULL,
                        canonical_type TEXT NOT NULL DEFAULT 'device',
                        canonical_id TEXT NOT NULL,
                        room_id TEXT,
                        source TEXT NOT NULL DEFAULT 'learned',
                        confidence REAL NOT NULL DEFAULT 1.0,
                        status TEXT NOT NULL DEFAULT 'active',
                        created_ts REAL NOT NULL,
                        updated_ts REAL NOT NULL,
                        FOREIGN KEY(project_id) REFERENCES memory_projects(project_id) ON DELETE CASCADE,
                        UNIQUE(project_id, alias)
                    );

                    CREATE TABLE IF NOT EXISTS memory_decisions (
                        decision_id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        summary TEXT NOT NULL,
                        details_json TEXT NOT NULL DEFAULT '{}',
                        confidence REAL NOT NULL DEFAULT 1.0,
                        source TEXT NOT NULL DEFAULT 'manual',
                        status TEXT NOT NULL DEFAULT 'approved',
                        created_ts REAL NOT NULL,
                        updated_ts REAL NOT NULL,
                        FOREIGN KEY(project_id) REFERENCES memory_projects(project_id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS memory_troubleshooting (
                        troubleshooting_id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        symptom TEXT NOT NULL,
                        attempted_fixes_json TEXT NOT NULL DEFAULT '[]',
                        verified_solution TEXT,
                        context_json TEXT NOT NULL DEFAULT '{}',
                        verification_notes TEXT,
                        status TEXT NOT NULL DEFAULT 'open',
                        created_ts REAL NOT NULL,
                        updated_ts REAL NOT NULL,
                        FOREIGN KEY(project_id) REFERENCES memory_projects(project_id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS memory_teach_candidates (
                        candidate_id TEXT PRIMARY KEY,
                        project_id TEXT NOT NULL,
                        transcript TEXT NOT NULL,
                        transcript_confidence REAL,
                        candidate_kind TEXT NOT NULL,
                        candidate_intent TEXT,
                        candidate_slots_json TEXT NOT NULL DEFAULT '{}',
                        candidate_action_json TEXT NOT NULL DEFAULT '{}',
                        source_endpoint_id TEXT,
                        room_id TEXT,
                        risk_level TEXT NOT NULL DEFAULT 'medium',
                        review_status TEXT NOT NULL DEFAULT 'queued',
                        notes TEXT,
                        created_ts REAL NOT NULL,
                        updated_ts REAL NOT NULL,
                        FOREIGN KEY(project_id) REFERENCES memory_projects(project_id) ON DELETE CASCADE
                    );

                    CREATE TABLE IF NOT EXISTS memory_stt_corrections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id TEXT NOT NULL,
                        heard_text TEXT NOT NULL,
                        corrected_text TEXT NOT NULL,
                        source TEXT NOT NULL DEFAULT 'manual',
                        confidence REAL NOT NULL DEFAULT 1.0,
                        status TEXT NOT NULL DEFAULT 'approved',
                        created_ts REAL NOT NULL,
                        updated_ts REAL NOT NULL,
                        FOREIGN KEY(project_id) REFERENCES memory_projects(project_id) ON DELETE CASCADE,
                        UNIQUE(project_id, heard_text, corrected_text)
                    );

                    CREATE TABLE IF NOT EXISTS suggestion_stats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id TEXT NOT NULL,
                        suggestion_key TEXT NOT NULL,
                        shown_count INTEGER NOT NULL DEFAULT 0,
                        accepted_count INTEGER NOT NULL DEFAULT 0,
                        rejected_count INTEGER NOT NULL DEFAULT 0,
                        last_shown_ts REAL,
                        last_response_ts REAL,
                        FOREIGN KEY(project_id) REFERENCES memory_projects(project_id) ON DELETE CASCADE,
                        UNIQUE(project_id, suggestion_key)
                    );

                    CREATE TABLE IF NOT EXISTS suggestion_suppression (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id TEXT NOT NULL,
                        suggestion_key TEXT NOT NULL,
                        suppression_type TEXT NOT NULL DEFAULT 'cooldown',
                        suppressed_until_ts REAL,
                        reason TEXT,
                        created_ts REAL NOT NULL,
                        FOREIGN KEY(project_id) REFERENCES memory_projects(project_id) ON DELETE CASCADE,
                        UNIQUE(project_id, suggestion_key, suppression_type)
                    );

                    CREATE TABLE IF NOT EXISTS suggestion_quiet_hours (
                        project_id TEXT PRIMARY KEY,
                        enabled INTEGER NOT NULL DEFAULT 0,
                        start_local TEXT NOT NULL DEFAULT '22:00',
                        end_local TEXT NOT NULL DEFAULT '07:00',
                        updated_ts REAL NOT NULL,
                        FOREIGN KEY(project_id) REFERENCES memory_projects(project_id) ON DELETE CASCADE
                    );

                    CREATE INDEX IF NOT EXISTS idx_memory_command_history_project_ts
                        ON memory_command_history(project_id, ts DESC);

                    CREATE INDEX IF NOT EXISTS idx_memory_command_history_intent
                        ON memory_command_history(project_id, intent_name, ts DESC);

                    CREATE INDEX IF NOT EXISTS idx_memory_preferences_project_scope
                        ON memory_preferences(project_id, pref_scope);

                    CREATE INDEX IF NOT EXISTS idx_memory_aliases_project_alias
                        ON memory_device_aliases(project_id, alias);

                    CREATE INDEX IF NOT EXISTS idx_memory_decisions_project_status
                        ON memory_decisions(project_id, status, created_ts DESC);

                    CREATE INDEX IF NOT EXISTS idx_memory_troubleshooting_project_status
                        ON memory_troubleshooting(project_id, status, created_ts DESC);

                    CREATE INDEX IF NOT EXISTS idx_memory_teach_candidates_status
                        ON memory_teach_candidates(project_id, review_status, created_ts DESC);

                    CREATE INDEX IF NOT EXISTS idx_memory_stt_corrections_project
                        ON memory_stt_corrections(project_id, status);

                    CREATE INDEX IF NOT EXISTS idx_suggestion_stats_project_key
                        ON suggestion_stats(project_id, suggestion_key);

                    CREATE INDEX IF NOT EXISTS idx_suggestion_suppression_project_key
                        ON suggestion_suppression(project_id, suggestion_key);
                    """
                )

                self._ensure_default_project(conn)
                conn.commit()

    def _ensure_default_project(self, conn: sqlite3.Connection) -> None:
        now = time.time()
        conn.execute(
            """
            INSERT OR IGNORE INTO memory_projects (
                project_id,
                name,
                kind,
                is_active,
                created_ts,
                updated_ts
            )
            VALUES (?, ?, 'general', 1, ?, ?)
            """,
            (self.default_project_id, "Default Project", now, now),
        )

    def ping(self) -> bool:
        try:
            with self._connect() as conn:
                conn.execute("SELECT 1;").fetchone()
            return True
        except Exception:
            return False