from __future__ import annotations

import os
import time
from pathlib import Path

from app.bootstrap_support import (
    build_voice_stack,
    make_boot_stage_publisher,
    publish_startup_state,
    wire_context_projection,
    wire_execution_and_ui,
    wire_nlp_pipeline,
)
from app.runtime import Runtime
from nlp.memory.services import WorkingMemoryService
from nlp.memory.stores import MemoryStore
from core.config.manager import load_config
from core.event_bus import EventBus
from core.net import http_client
from core.net.policy import NetPolicy
from core.observability.healthcheck import run_healthcheck
from core.observability.logger import get_logger
from core.observability.event_timeline import EventTimeline


DB_PATH = os.getenv("JARED_DB_PATH", "data/jared.db")
DEVICE_STATE_PATH = Path(
    os.getenv("JARED_DEVICE_STATE_PATH", "data/device_power_state.json")
)


def build_runtime() -> Runtime:
    log = get_logger("JARED")
    log.info("Boot sequence started")

    cfg = load_config()
    net_policy = NetPolicy(config=cfg)
    http_client.configure(net_policy)

    offline_only = cfg.offline_only
    log.info(f"Offline mode: {offline_only}")
    log.info(f"NetPolicy allow_internet: {net_policy.allow_internet}")

    if offline_only == net_policy.allow_internet:
        raise RuntimeError("Offline mode mismatch: config vs NetPolicy")

    if not run_healthcheck():
        raise RuntimeError("Healthcheck failed")

    log.info("System initialized successfully (Milestone 0)")

    bus = EventBus()
    EventTimeline(bus)
    publish_boot_stage = make_boot_stage_publisher(bus)

    memory_store = MemoryStore(DB_PATH)
    memory_store.ensure_schema()
    log.info(f"Memory schema ready: ok={memory_store.ping()}")

    working_memory = WorkingMemoryService(memory_store)
    working_memory.attach(bus)

    t_stage = time.perf_counter()
    wire_context_projection(bus)
    publish_boot_stage("Runtime", t_stage)

    t_stage = time.perf_counter()
    execution = wire_execution_and_ui(
        bus,
        offline_only=offline_only,
        db_path=DB_PATH,
        device_state_path=DEVICE_STATE_PATH,
    )
    publish_boot_stage("Devices", t_stage)

    wire_nlp_pipeline(bus, router=execution["router"])

    t_stage = time.perf_counter()
    voice = build_voice_stack(bus)
    publish_boot_stage("Voice", t_stage)

    publish_startup_state(
        bus,
        offline_only=offline_only,
        tts_ready=voice["tts_ready"],
        tts_reason=voice["tts_reason"],
        wake_ready=voice["wake_ready"],
        wake_name=voice["wake_name"],
        stt_ready=voice["stt_ready"],
        stt_name=voice["stt_name"],
    )

    return Runtime(
        bus=bus,
        voice=voice["voice_pipeline"],
        voice_output=voice["voice_output"],
    )