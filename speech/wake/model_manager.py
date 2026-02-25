from __future__ import annotations
from pathlib import Path
import os

def project_root() -> Path:
    # .../jared/speech/wake/model_manager.py -> parents[3] == .../jared
    return Path(__file__).resolve().parents[3]

def openwakeword_models_dir() -> Path:
    # Allow override via env var if you ever move it
    env = os.getenv("JARED_OPENWAKEWORD_MODELS_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return project_root() / "third_party" / "openwakeword_models"

def hey_jared_model_path() -> Path:
    return openwakeword_models_dir() / "hey_jared_float32.tflite"
