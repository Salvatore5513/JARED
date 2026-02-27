# `speech/` package

## Voice pipeline boundaries

`speech/` owns the *speech-specific* parts of the pipeline:

- Wake engines produce a **wake event + pre-roll audio** only.
- STT engines produce a **transcript** only.
- TTS engines render **audio** only.

All “meaning” (intent parsing, safety decisions, device execution) happens elsewhere — `nlp/`, `core/`, and `devices/`.
This keeps the voice stack replaceable (e.g., swap wake model, swap STT backend) without rewriting the assistant.


Wake/STT/TTS orchestration and the end-to-end voice pipeline glue.

## `speech/`

### `speech/__init__.py`

### `speech/pipeline.py`

**Classes:** `VoicePipeline`

**Used by:** `app.main`

## `speech/__pycache__/`

### `speech/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `speech/__pycache__/pipeline.cpython-313.pyc`

**Type:** `pyc`

## `speech/stt/`

### `speech/stt/__init__.py`

### `speech/stt/base.py`

**Classes:** `Transcript`, `SpeechToTextEngine`

**Used by:** `speech.pipeline`, `speech.stt.local_engine`

### `speech/stt/local_engine.py`

**Classes:** `WhisperCppSTTEngine`

**Functions:** `_repo_root`, `_rms`

**Used by:** `app.main`

### `speech/stt/postprocess.py`

**Classes:** `PostprocessConfig`

**Functions:** `_collapse_spaces`, `_strip_prefix_phrases`, `normalize_transcript`

## `speech/stt/__pycache__/`

### `speech/stt/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `speech/stt/__pycache__/base.cpython-313.pyc`

**Type:** `pyc`

### `speech/stt/__pycache__/local_engine.cpython-313.pyc`

**Type:** `pyc`

### `speech/stt/__pycache__/postprocess.cpython-313.pyc`

**Type:** `pyc`

## `speech/tts/`

### `speech/tts/__init__.py`

### `speech/tts/base.py`

### `speech/tts/dsp_presets.py`

### `speech/tts/renderer.py`

### `speech/tts/voice_profiles.py`

## `speech/tts/__pycache__/`

### `speech/tts/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `speech/tts/__pycache__/base.cpython-313.pyc`

**Type:** `pyc`

### `speech/tts/__pycache__/dsp_presets.cpython-313.pyc`

**Type:** `pyc`

### `speech/tts/__pycache__/renderer.cpython-313.pyc`

**Type:** `pyc`

### `speech/tts/__pycache__/voice_profiles.cpython-313.pyc`

**Type:** `pyc`

## `speech/tts/engines/`

### `speech/tts/engines/__init__.py`

## `speech/tts/engines/__pycache__/`

### `speech/tts/engines/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

## `speech/wake/`

### `speech/wake/__init__.py`

### `speech/wake/base.py`

**Classes:** `WakeResult`, `WakeWordEngine`

**Used by:** `speech.pipeline`, `speech.wake.engine_keyword`

### `speech/wake/engine_keyword.py`

**Classes:** `KeywordWakeEngine`, `OpenWakeWordConfig`, `OpenWakeWordEngine`

**Functions:** `_project_root`

**Used by:** `app.main`

### `speech/wake/model_manager.py`

**Functions:** `project_root`, `openwakeword_models_dir`, `hey_jared_model_path`

## `speech/wake/__pycache__/`

### `speech/wake/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `speech/wake/__pycache__/base.cpython-313.pyc`

**Type:** `pyc`

### `speech/wake/__pycache__/engine_keyword.cpython-313.pyc`

**Type:** `pyc`

### `speech/wake/__pycache__/model_manager.cpython-313.pyc`

**Type:** `pyc`

## `speech/wake/builder/`

### `speech/wake/builder/__init__.py`

### `speech/wake/builder/trainer.py`

### `speech/wake/builder/wizard.py`

## `speech/wake/builder/__pycache__/`

### `speech/wake/builder/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `speech/wake/builder/__pycache__/trainer.cpython-313.pyc`

**Type:** `pyc`

### `speech/wake/builder/__pycache__/wizard.cpython-313.pyc`

**Type:** `pyc`