from __future__ import annotations

import os
import time
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, cast

from core.event_bus import EventBus
from core.observability.logger import get_logger
from core.state.context_service import ContextService
from devices.drivers.mqtt.driver import MQTTDriver
from devices.drivers.registry import DriverRegistry
from devices.execution.device_manager import DeviceManager
from devices.registry.store import RegistryStore
from devices.state_tracker import DeviceStateTracker
from nlp.intents.parser import parse
from nlp.intents.router import IntentRouter
from speech.pipeline import VoicePipeline
from speech.stt.local_engine import WhisperCppSTTEngine
from speech.tts.voice_output_service import VoiceOutputService
from speech.wake.engine_keyword import (
    KeywordWakeEngine,
    OpenWakeWordConfig,
    OpenWakeWordEngine,
)
from ui.commands.router import UiCommandRouter
from ui.dashboard.controller import DashboardController
from ui.review.router import ReviewRouter
from ui.review.executor import ReviewExecutor

from core.security.audit_log import AuditLog
from core.security.auth.auth_window import AuthWindow
from core.security.policy_engine import PolicyEngine
from core.security.rate_limits import RateLimiter


def normalize_transcript_for_intent(text: str) -> str | None:
    if not text:
        return None

    raw = text.strip()
    t = raw.lower().strip()
    t_cmp = t.replace(",", "").replace(".", "").replace("!", "").replace("?", "").strip()

    if t_cmp in {"hey jared", "jared"}:
        return None

    prefixes = ("hey jared", "hey, jared", "jared")
    for p in prefixes:
        if t.startswith(p):
            raw = raw[len(p):].lstrip(" ,.!?").strip()
            break

    if len(raw) < 3:
        return None

    return raw if raw else None


def build_device_manager(
    bus: EventBus,
    *,
    db_path: str,
    offline_only: bool,
) -> DeviceManager:
    registry = RegistryStore(db_path)
    audit = AuditLog(db_path)

    drivers = DriverRegistry()
    drivers.register(MQTTDriver())

    auth_window = AuthWindow()
    rate_limiter = RateLimiter()
    policy = PolicyEngine()

    return DeviceManager(
        event_bus=bus,
        registry=registry,
        drivers=drivers,
        policy=policy,
        auth_window=auth_window,
        rate_limiter=rate_limiter,
        audit_log=audit,
        offline_only=offline_only,
    )


def _safe_serialize(obj: Any) -> Any:
    if obj is None:
        return None

    if is_dataclass(obj):
        try:
            out: dict[str, Any] = {}
            for f in fields(obj):
                out[f.name] = _safe_serialize(getattr(obj, f.name))
            return out
        except Exception:
            return repr(obj)

    if isinstance(obj, (str, int, float, bool)):
        return obj

    if isinstance(obj, Mapping):
        return {str(k): _safe_serialize(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple)):
        return [_safe_serialize(x) for x in obj]

    if isinstance(obj, Iterable) and not isinstance(obj, (str, bytes)):
        try:
            return [_safe_serialize(x) for x in obj]
        except Exception:
            return repr(obj)

    return repr(obj)


def _registry_list_devices(registry: Any) -> list[Any]:
    candidates = (
        "list_devices",
        "all_devices",
        "get_all_devices",
        "get_devices",
        "devices",
        "list",
    )

    for name in candidates:
        if not hasattr(registry, name):
            continue

        attr = getattr(registry, name)

        try:
            res = attr() if callable(attr) else attr
        except Exception:
            continue

        if res is None:
            continue

        if isinstance(res, (list, tuple)):
            return list(res)

        if isinstance(res, Iterable) and not isinstance(res, (str, bytes, Mapping)):
            return list(cast(Iterable[Any], res))

    return []


def make_boot_stage_publisher(bus: EventBus):
    boot_started = time.perf_counter()

    def publish(stage: str, stage_started: float) -> None:
        elapsed_ms = int((time.perf_counter() - stage_started) * 1000)
        total_ms = int((time.perf_counter() - boot_started) * 1000)
        bus.publish(
            "system.boot.stage",
            stage=stage,
            elapsed_ms=elapsed_ms,
            total_ms=total_ms,
        )

    return publish


def wire_context_projection(bus: EventBus) -> ContextService:
    log = get_logger("JARED")
    context = ContextService()

    bus.subscribe("voice.wake*", context.handle_bus_event)
    bus.subscribe("stt.*", context.handle_bus_event)
    bus.subscribe("action.*", context.handle_bus_event)
    bus.subscribe("tts.*", context.handle_bus_event)
    bus.subscribe("nlp.intent", context.handle_bus_event)

    _ctx_last = {"mode": None, "busy": None, "intent": None, "device": None}

    def _log_ctx(s) -> None:
        key = (s.mode, s.busy, s.last_intent_name, s.last_device_id)
        prev = (
            _ctx_last["mode"],
            _ctx_last["busy"],
            _ctx_last["intent"],
            _ctx_last["device"],
        )
        if key == prev:
            return

        _ctx_last["mode"], _ctx_last["busy"], _ctx_last["intent"], _ctx_last["device"] = key
        log.info(
            f"[ctx] mode={s.mode} busy={s.busy} "
            f"intent={s.last_intent_name} device={s.last_device_id}"
        )

    def _publish_ctx(s) -> None:
        bus.publish(
            "ui.context.state",
            mode=str(s.mode),
            busy=bool(s.busy),
            intent=s.last_intent_name,
            device=s.last_device_id,
        )

    context.add_listener(_log_ctx)
    context.add_listener(_publish_ctx)
    return context


def wire_execution_and_ui(
    bus: EventBus,
    *,
    offline_only: bool,
    db_path: str,
    device_state_path: Path,
):
    device_manager = build_device_manager(
        bus,
        db_path=db_path,
        offline_only=offline_only,
    )
    router = IntentRouter(device_manager=device_manager, bus=bus)
    ui_command_router = UiCommandRouter(bus=bus, device_manager=device_manager)
    dashboard_controller = DashboardController(bus=bus, offline_only=offline_only)
    review_executor = ReviewExecutor(device_manager=device_manager)
    review_router = ReviewRouter(bus=bus, executor=review_executor)
    state_tracker = DeviceStateTracker(
        bus=bus,
        state_path=device_state_path,
        registry=device_manager.registry,
    )

    def on_ui_devices_refresh(_evt) -> None:
        devices = _registry_list_devices(device_manager.registry)
        serialized = _safe_serialize(devices)

        if isinstance(serialized, list):
            for item in serialized:
                if not isinstance(item, dict):
                    continue
                device_id = str(item.get("device_id", "")).strip()
                if not device_id:
                    continue
                item["last_known_power_state"] = state_tracker.get_power_state(device_id)
                item["last_known_availability"] = state_tracker.get_availability(device_id)

        bus.publish("ui.devices.snapshot", devices=serialized)

    bus.subscribe("ui.devices.refresh", on_ui_devices_refresh)

    return {
        "device_manager": device_manager,
        "router": router,
        "ui_command_router": ui_command_router,
        "dashboard_controller": dashboard_controller,
        "review_router": review_router,
        "review_executor": review_executor,
        "state_tracker": state_tracker,
    }


def wire_nlp_pipeline(bus: EventBus, *, router: IntentRouter) -> None:
    log = get_logger("JARED")

    def on_transcript(evt) -> None:
        raw_text = evt.data.get("text", "")
        clean = normalize_transcript_for_intent(raw_text)
        if clean is None:
            log.info(f"[transcript] dropped wake-only: '{raw_text}'")
            return

        match = parse(clean)
        if match is None:
            if router.has_pending_clarification():
                handled = router.handle_clarification_reply(clean)
                if handled:
                    log.info(f"[nlp] clarification reply handled: '{clean}'")
                    return

            log.info(f"[nlp] no match for: '{clean}'")
            return

        bus.publish(
            "nlp.intent",
            name=match.name,
            confidence=match.confidence,
            slots=match.slots,
            raw_text=match.raw_text,
        )

    def on_intent(evt) -> None:
        log.info(
            f"[intent] {evt.data['name']} ({evt.data['confidence']:.2f}) "
            f"slots={evt.data['slots']} | '{evt.data['raw_text']}'"
        )
        router.handle(
            name=evt.data["name"],
            confidence=evt.data["confidence"],
            slots=evt.data["slots"],
            raw_text=evt.data["raw_text"],
        )

    def on_stt_listening(_evt) -> None:
        log.info("[stt] listening...")

    def on_stt_skipped(evt) -> None:
        reason = evt.data.get("reason", "unknown")
        rms = evt.data.get("rms")
        if rms is None:
            log.info(f"[stt] skipped: {reason}")
        else:
            log.info(f"[stt] skipped: {reason} rms={rms:.1f}")

    bus.subscribe("voice.transcript", on_transcript)
    bus.subscribe("nlp.intent", on_intent)
    bus.subscribe("stt.listening", on_stt_listening)
    bus.subscribe("stt.skipped", on_stt_skipped)


def build_voice_stack(bus: EventBus):
    log = get_logger("JARED")

    voice_output: VoiceOutputService | None = VoiceOutputService(bus=bus)
    tts_ready = False
    tts_reason: str | None = None

    disable_tts = os.getenv("JARED_TTS_DISABLE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }

    if disable_tts:
        log.warning("[tts] disabled by env (JARED_TTS_DISABLE=1)")
        tts_reason = "disabled_by_env"
        bus.publish("tts.unavailable", reason=tts_reason)
        voice_output = None
    else:
        try:
            voice_output.start()
            tts_ready = True
            bus.publish("assistant.say", text="JARED voice output online.")
        except Exception as e:
            tts_reason = str(e)
            log.warning(f"[tts] unavailable: {e!r}")
            log.warning("[tts] start sidecar with: python -m speech.tts.sidecar.service")
            bus.publish("tts.unavailable", reason=tts_reason)
            voice_output = None

    wake_choice = os.getenv("JARED_WAKE_ENGINE", "").strip().lower()
    if wake_choice in {"dev", "keyword", "stdin"}:
        wake_engine = KeywordWakeEngine()
        wake_name = "keyword"
        log.info("Wake engine: DEV (stdin trigger)")
    else:
        wake_engine = OpenWakeWordEngine(cfg=OpenWakeWordConfig(cooldown_s=2.0))
        wake_name = "openwakeword"
        log.info("Wake engine: openWakeWord (.tflite)")

    stt_engine = WhisperCppSTTEngine()
    stt_name = getattr(stt_engine, "name", "whispercpp")

    voice_pipeline = VoicePipeline(
        bus=bus,
        wake=wake_engine,
        stt=stt_engine,
    )

    return {
        "voice_output": voice_output,
        "voice_pipeline": voice_pipeline,
        "tts_ready": tts_ready,
        "tts_reason": tts_reason,
        "wake_ready": True,
        "wake_name": wake_name,
        "stt_ready": True,
        "stt_name": stt_name,
    }


def publish_startup_state(
    bus: EventBus,
    *,
    offline_only: bool,
    tts_ready: bool,
    tts_reason: str | None = None,
    wake_ready: bool = True,
    wake_name: str | None = None,
    stt_ready: bool = True,
    stt_name: str | None = None,
) -> None:
    bus.publish("system.config", offline_only=offline_only)

    bus.publish(
        "system.runtime_ready",
        ready=True,
        offline_only=offline_only,
    )

    bus.publish(
        "system.stt_ready",
        ready=stt_ready,
        engine=stt_name,
    )

    bus.publish(
        "system.wake_ready",
        ready=wake_ready,
        engine=wake_name,
    )

    bus.publish(
        "system.tts_ready",
        ready=tts_ready,
        reason=tts_reason,
    )

    bus.publish("ui.devices.refresh")
    bus.publish("ui.dashboard.refresh")