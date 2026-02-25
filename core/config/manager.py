from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _default_data_dir() -> Path:
    env = os.getenv("JARED_DATA_DIR", "").strip()
    if env:
        return Path(env)

    if os.name == "nt":
        appdata = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(appdata) / "jared"

    return Path.home() / ".local" / "share" / "jared"


@dataclass(frozen=True)
class Config:
    # Keep this for net/policy gate compatibility
    offline_only: bool = True
    # Useful everywhere; safe additive field
    data_dir: Path = Path(".")


def load_config() -> Config:
    """
    Backwards-compatible API for modules like core/net/policy.py.

    Env overrides:
      - JARED_OFFLINE_ONLY=1 (default) blocks outbound net
      - JARED_DATA_DIR sets config/data root
    """
    offline_env = os.getenv("JARED_OFFLINE_ONLY", "1").strip()
    data_dir = _default_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return Config(
        offline_only=(offline_env == "1"),
        data_dir=data_dir,
    )


class ConfigManager:
    """
    Local-only persistent config store for non-sensitive settings:
      - audio device selection
      - volumes
      - ducking strength
      - calibration profiles (later)
    """
    def __init__(self, data_dir: Path | None = None) -> None:
        cfg = load_config()
        self.data_dir = data_dir or cfg.data_dir
        self.config_file = self.data_dir / "config.json"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, Any]:
        if not self.config_file.exists():
            return {}
        try:
            return json.loads(self.config_file.read_text(encoding="utf-8"))
        except Exception:
            # Don't brick startup if config is corrupted
            return {}

    def save(self, data: dict[str, Any]) -> None:
        tmp = self.config_file.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        tmp.replace(self.config_file)

    def get(self, key: str, default: Any = None) -> Any:
        return self.load().get(key, default)

    def set(self, key: str, value: Any) -> None:
        data = self.load()
        data[key] = value
        self.save(data)
