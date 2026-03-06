from __future__ import annotations

import os
from core.config.manager import load_config
from core.event_bus import EventBus
from core.net import http_client
from core.net.policy import NetPolicy
from core.observability.healthcheck import run_healthcheck
from core.observability.logger import get_logger
from core.security.audit_log import AuditLog
from core.security.auth.auth_window import AuthWindow
from core.security.policy_engine import PolicyEngine
from core.security.rate_limits import RateLimiter
from core.state.context_service import ContextService
from dataclasses import asdict, is_dataclass, fields
from devices.drivers.mqtt.driver import MQTTDriver
from devices.drivers.registry import DriverRegistry
from devices.execution.device_manager import DeviceManager
from devices.registry.store import RegistryStore

from nlp.intents.parser import parse
from nlp.intents.router import IntentRouter

from speech.pipeline import VoicePipeline
from speech.stt.local_engine import WhisperCppSTTEngine
from speech.tts.voice_output_service import VoiceOutputService
from speech.wake.engine_keyword import KeywordWakeEngine, OpenWakeWordConfig, OpenWakeWordEngine
from typing import Any, Iterable, Mapping, Sequence, cast
from app.runtime import Runtime


DB_PATH = os.getenv("JARED_DB_PATH", "data/jared.db")


def normalize_transcript_for_intent(text: str) -> str | None:
    """
    - If transcript is only the wake word, return None (drop).
    - If transcript starts with the wake word, strip it.
    """
    if not text:
        return None

    raw = text.strip()
    t = raw.lower().strip()

    # comparison version with common punctuation removed
    t_cmp = t.replace(",", "").replace(".", "").replace("!", "").replace("?", "").strip()

    # Drop wake-only transcripts
    if t_cmp in {"hey jared", "jared"}:
        return None

    # Strip wake prefix from commands
    prefixes = ("hey jared", "hey, jared", "jared")
    for p in prefixes:
        if t.startswith(p):
            raw = raw[len(p) :].lstrip(" ,.!?").strip()
            break

    if len(raw) < 3:
        return None

    return raw if raw else None


def build_device_manager(bus: EventBus, *, offline_only: bool) -> DeviceManager:
    """
    Milestone 3: instantiate the execution spine once, at startup.
    """
    registry = RegistryStore(DB_PATH)
    audit = AuditLog(DB_PATH)

    drivers = DriverRegistry()
    drivers.register(MQTTDriver())  # safe even if broker isn't running yet

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

    # dataclass -> dict (manual; avoids asdict() type-checker issues)
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

    # Generic iterable (but NOT strings/bytes/dicts handled above)
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

        # Pylance-safe: only list() things that are actually iterable
        if isinstance(res, (list, tuple)):
            return list(res)

        if isinstance(res, Iterable) and not isinstance(res, (str, bytes, Mapping)):
            return list(cast(Iterable[Any], res))

    return []

def build_runtime() -> Runtime:
    log = get_logger("JARED")
    log.info("Boot sequence started")

    cfg = load_config()
    net_policy = NetPolicy(config=cfg)
    http_client.configure(net_policy)  # uses the same NetPolicy instance

    offline_only = cfg.offline_only
    log.info(f"Offline mode: {offline_only}")
    log.info(f"NetPolicy allow_internet: {net_policy.allow_internet}")

    if offline_only == net_policy.allow_internet:
        raise RuntimeError("Offline mode mismatch: config vs NetPolicy")

    if not run_healthcheck():
        raise RuntimeError("Healthcheck failed")

    log.info("System initialized successfully (Milestone 0)")

    bus = EventBus()

    # Context spine (Milestone 3)
    context = ContextService()

    # Context subscribes to all relevant event domains
    bus.subscribe("voice.wake*", context.handle_bus_event)
    bus.subscribe("stt.*", context.handle_bus_event)
    bus.subscribe("action.*", context.handle_bus_event)
    bus.subscribe("tts.*", context.handle_bus_event)
    bus.subscribe("nlp.intent", context.handle_bus_event)

    # Optional: log context changes while you bring this online
    _ctx_last = {"mode": None, "busy": None, "intent": None, "device": None}

    def _log_ctx(s):
        key = (s.mode, s.busy, s.last_intent_name, s.last_device_id)
        prev = (_ctx_last["mode"], _ctx_last["busy"], _ctx_last["intent"], _ctx_last["device"])
        if key == prev:
            return
        _ctx_last["mode"], _ctx_last["busy"], _ctx_last["intent"], _ctx_last["device"] = key
        log.info(f"[ctx] mode={s.mode} busy={s.busy} intent={s.last_intent_name} device={s.last_device_id}")

    context.add_listener(_log_ctx)

    def _publish_ctx(s):
        bus.publish(
            "ui.context.state",
            mode=str(s.mode),
            busy=bool(s.busy),
            intent=s.last_intent_name,
            device=s.last_device_id,
        )

    context.add_listener(_publish_ctx)

    # Milestone 3 wiring
    device_manager = build_device_manager(bus, offline_only=offline_only)
    router = IntentRouter(device_manager=device_manager, bus=bus)

    def on_ui_devices_refresh(_evt):
        devices = device_manager.registry.list_devices()
        bus.publish("ui.devices.snapshot", devices=_safe_serialize(devices))

    bus.subscribe("ui.devices.refresh", on_ui_devices_refresh)

    def on_transcript(evt):
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

    def on_intent(evt):
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

    def on_stt_listening(_evt):
        log.info("[stt] listening...")

    def on_stt_skipped(evt):
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

    # ---- TTS Voice Output Service ----
    voice_output = VoiceOutputService(bus=bus)

    disable_tts = os.getenv("JARED_TTS_DISABLE", "").strip().lower() in {"1", "true", "yes", "on"}
    if disable_tts:
        log.warning("[tts] disabled by env (JARED_TTS_DISABLE=1)")
        bus.publish("tts.unavailable", reason="disabled_by_env")
        voice_output = None  # type: ignore[assignment]
    else:
        try:
            voice_output.start()
            bus.publish("assistant.say", text="JARED voice output online.")
        except Exception as e:
            log.warning(f"[tts] unavailable: {e!r}")
            bus.publish("tts.unavailable", reason=str(e))
            voice_output = None  # type: ignore[assignment]

    # Wake engine selection
    wake_choice = os.getenv("JARED_WAKE_ENGINE", "").strip().lower()
    if wake_choice in {"dev", "keyword", "stdin"}:
        wake_engine = KeywordWakeEngine()
        log.info("Wake engine: DEV (stdin trigger)")
    else:
        wake_engine = OpenWakeWordEngine(cfg=OpenWakeWordConfig(cooldown_s=2.0))
        log.info("Wake engine: openWakeWord (.tflite)")

    vp = VoicePipeline(bus=bus, wake=wake_engine, stt=WhisperCppSTTEngine())

    bus.publish(
        "system.config",
        offline_only=offline_only,
    )

    bus.publish("system.runtime_ready", ready=True)
    bus.publish("system.stt_ready", ready=True)
    bus.publish("system.wake_ready", ready=True)
    bus.publish("system.tts_ready", ready=True)

    bus.publish("ui.devices.refresh")

    return Runtime(
        bus=bus,
        voice=vp,
        voice_output=voice_output,
    )