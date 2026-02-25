from __future__ import annotations
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]  # .../jared
THIRD_PARTY = PROJECT_ROOT / "third_party"

OPENWAKEWORD_MODELS_DIR = THIRD_PARTY / "openwakeword_models"
HEY_JARED_MODEL_PATH = OPENWAKEWORD_MODELS_DIR / "hey_jared_float32.tflite"
