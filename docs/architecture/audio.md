# `audio/` package

## Audio responsibilities

`audio/` is everything that deals with sound as *signal*:

- Capture and device selection
- VAD / level meters / calibration
- Playback routing
- Mixing + ducking + barge-in behaviors

It does **not** decide what a command means and does not execute devices. It provides the *plumbing* so voice UX feels clean in a noisy garage.


Audio I/O: capture, playback, mixer, ducking, barge-in, calibration primitives.

## `audio/`

### `audio/__init__.py`

### `audio/barge_in.py`

### `audio/capture.py`

**Classes:** `LevelReading`

**Functions:** `_lin_to_db`, `start_level_meter`

**Used by:** `audio.calibration.wizard`, `audio.ducking_test`, `audio.playback`, `tools.cli`

### `audio/devices.py`

**Classes:** `AudioDevice`

**Functions:** `_hostapi_name`, `list_devices`, `input_devices`, `output_devices`, `find_by_name_contains`, `get_default_devices`

**Used by:** `tools.cli`

### `audio/ducking.py`

**Classes:** `DuckingParams`, `DuckingState`, `DuckingController`

**Used by:** `audio.ducking_test`, `audio.playback`, `tools.cli`

### `audio/ducking_test.py`

**Classes:** `DuckingTestConfig`, `DuckingTestRunner`

**Used by:** `tools.cli`

### `audio/echo_control.py`

### `audio/mixer.py`

### `audio/pipeline.py`

### `audio/playback.py`

**Classes:** `PlaybackConfig`, `MusicPlayback`

**Used by:** `tools.cli`

### `audio/vad.py`

### `audio/wav_player.py`

**Classes:** `WavInfo`, `WavPlayer`

**Used by:** `audio.playback`

## `audio/__pycache__/`

### `audio/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `audio/__pycache__/barge_in.cpython-313.pyc`

**Type:** `pyc`

### `audio/__pycache__/capture.cpython-313.pyc`

**Type:** `pyc`

### `audio/__pycache__/devices.cpython-313.pyc`

**Type:** `pyc`

### `audio/__pycache__/ducking.cpython-313.pyc`

**Type:** `pyc`

### `audio/__pycache__/ducking_test.cpython-313.pyc`

**Type:** `pyc`

### `audio/__pycache__/echo_control.cpython-313.pyc`

**Type:** `pyc`

### `audio/__pycache__/mixer.cpython-313.pyc`

**Type:** `pyc`

### `audio/__pycache__/pipeline.cpython-313.pyc`

**Type:** `pyc`

### `audio/__pycache__/playback.cpython-313.pyc`

**Type:** `pyc`

### `audio/__pycache__/vad.cpython-313.pyc`

**Type:** `pyc`

### `audio/__pycache__/wav_player.cpython-313.pyc`

**Type:** `pyc`

## `audio/calibration/`

### `audio/calibration/__init__.py`

### `audio/calibration/profiles.py`

### `audio/calibration/wizard.py`

**Classes:** `CalibrationResult`

**Functions:** `_sample_rms_db`, `_robust_mean`, `run_basic_calibration`

**Used by:** `tools.cli`

## `audio/calibration/__pycache__/`

### `audio/calibration/__pycache__/__init__.cpython-313.pyc`

**Type:** `pyc`

### `audio/calibration/__pycache__/profiles.cpython-313.pyc`

**Type:** `pyc`

### `audio/calibration/__pycache__/wizard.cpython-313.pyc`

**Type:** `pyc`