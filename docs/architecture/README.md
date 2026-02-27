# Repository map

Generated: 2026-02-27

This folder contains human-readable documentation for *what each folder/module/file does*.
It's meant to be the living "map" of the repo.

## Top-level folders

- **app/**
  - config/
  - __init__.py
  - bootstrap.py
  - lifecycle.py
  - main.py
  - service_locator.py
- **audio/**
  - calibration/
  - __init__.py
  - barge_in.py
  - capture.py
  - devices.py
  - ducking.py
  - ducking_test.py
  - echo_control.py
  - mixer.py
  - pipeline.py
  - playback.py
  - vad.py
  - wav_player.py
- **automation/**
  - rules/
  - __init__.py
  - scenes.py
  - timers.py
- **core/**
  - config/
  - net/
  - observability/
  - security/
  - state/
  - __init__.py
  - clock.py
  - errors.py
  - event_bus.py
  - ids.py
  - scheduler.py
- **data/**
  - migrations/
  - seed/
  - jared.db
- **devices/**
  - drivers/
  - execution/
  - registry/
  - __init__.py
- **docs/**
  - architecture/
  - milestones/
  - runbooks/
- **knowledge/**
  - answer/
  - index/
  - ingest/
  - retrieve/
  - __init__.py
  - library.py
- **logs/**
  - system.log
- **nlp/**
  - dialogue/
  - intents/
  - memory/
  - __init__.py
- **ops/**
  - backup/
  - service/
  - updates/
  - __init__.py
- **packs/**
  - sources/
  - __init__.py
  - format.md
  - installer.py
  - registry.py
  - signatures.py
- **skills/**
  - _framework/
  - garage/
  - media/
  - system/
  - __init__.py
- **speech/**
  - stt/
  - tts/
  - wake/
  - __init__.py
  - pipeline.py
- **tests/**
  - audio_sim/
  - fixtures/
  - integration/
  - unit/
  - test_class2_policy.py
  - test_device_manager.py
- **tflite_runtime/**
  - __init__.py
  - interpreter.py
- **third_party/**
  - openwakeword_models/
  - wakeword_dataset/
  - whisper_models/
  - whispercpp/
  - whispercpp_cuda/
- **tools/**
  - __init__.py
  - cli.py
  - gen_wav_48k.py
  - guardrails_smoke.py
  - pack_builder.py
  - seed_registry.py
- **ui/**
  - components/
  - dashboard/
  - devices/
  - logs/
  - manuals/
  - review_queue/
  - settings/
  - __init__.py

## Quick mental model

- `app/`: process startup + wiring.
- `core/`: shared primitives (event bus, config, net policy, security, logging).
- `speech/` + `audio/`: the voice pipeline (wake/STT/TTS + audio capture/mixer/ducking).
- `nlp/`: intent parsing, routing, repair.
- `devices/`: device registry + drivers + execution spine (DeviceManager, policy adapter, verifier).
- `automation/`: timers/scenes/rules (future expansion hooks).
- `knowledge/`: manuals ingestion/index/retrieval/answering.
- `skills/`: skill framework + early skills (system/media/garage).
- `ui/`: placeholder UI package boundaries.
- `ops/`: service/install/update/backup primitives.
- `packs/`: offline installable "packs" (voices/wake/skills).
- `tests/`: guardrails + smoke tests.
- `third_party/`: vendored deps (trimmed in the uploaded zip).
- `tflite_runtime/`: runtime bits for wake models.
- `tools/`: developer tooling and guardrails checks.
- `data/`: local DB and migrations/seed data (generated at runtime / in dev).

## Reading order (recommended)

1. `00_execution_spine.md`
2. `core.md` → `devices.md` → `speech.md`
3. `nlp.md` → `audio.md`
4. Everything else as needed.
