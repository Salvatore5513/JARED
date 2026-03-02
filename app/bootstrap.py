from __future__ import annotations

import os
from dataclasses import dataclass

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

from devices.drivers.mqtt.driver import MQTTDriver
from devices.drivers.registry import DriverRegistry
from devices.execution.device_manager import DeviceManager
from devices.registry.store import RegistryStore

from nlp.intents.parser import parse
from nlp.intents.router import IntentRouter

from speech.pipeline import VoicePipeline
from speech.stt.local_engine import WhisperCppSTTEngine
from speech.wake.engine_keyword import KeywordWakeEngine, OpenWakeWordConfig, OpenWakeWordEngine

DB_PATH = os.getenv("JARED_DB_PATH", "data/jared.db")


@dataclass
class Runtime:
    voice: VoicePipeline

    def run_forever(self) -> None:
        self.voice.run_forever()


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

    # Milestone 3 wiring
    device_manager = build_device_manager(bus, offline_only=offline_only)
    router = IntentRouter(device_manager=device_manager)

    def on_transcript(evt):
        raw_text = evt.data.get("text", "")

        clean = normalize_transcript_for_intent(raw_text)
        if clean is None:
            log.info(f"[transcript] dropped wake-only: '{raw_text}'")
            return

        match = parse(clean)
        if match is None:
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
        # keep your intent log
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

    # Optional: subscribe to STT events now that the pipeline publishes them
    def on_stt_listening(evt):
        log.info("[stt] listening...")
        # ContextService receives this via bus wildcard subscription (stt.*)

    def on_stt_skipped(evt):
        reason = evt.data.get("reason", "unknown")
        rms = evt.data.get("rms", None)
        if rms is None:
            log.info(f"[stt] skipped: {reason}")
        else:
            log.info(f"[stt] skipped: {reason} rms={rms:.1f}")


    bus.subscribe("voice.transcript", on_transcript)
    bus.subscribe("nlp.intent", context.handle_bus_event)
    bus.subscribe("nlp.intent", on_intent)
    bus.subscribe("stt.listening", on_stt_listening)
    bus.subscribe("stt.skipped", on_stt_skipped)

    # Wake engine selection:
    # - default: openWakeWord (your .tflite)
    # - set JARED_WAKE_ENGINE=dev to force dev mode wake
    wake_choice = os.getenv("JARED_WAKE_ENGINE", "").strip().lower()
    if wake_choice in {"dev", "keyword", "stdin"}:
        wake_engine = KeywordWakeEngine()
        log.info("Wake engine: DEV (stdin trigger)")
    else:
        wake_engine = OpenWakeWordEngine(
            cfg=OpenWakeWordConfig(
                cooldown_s=2.0,
            )
        )
        log.info("Wake engine: openWakeWord (.tflite)")

    vp = VoicePipeline(bus=bus, wake=wake_engine, stt=WhisperCppSTTEngine())
    return Runtime(voice=vp)