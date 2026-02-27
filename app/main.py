from __future__ import annotations

import os
import sys
import traceback

from core.event_bus import EventBus
from core.net.policy import NetPolicy
from core.observability.healthcheck import run_healthcheck
from core.observability.logger import get_logger

from speech.pipeline import VoicePipeline
from speech.stt.local_engine import WhisperCppSTTEngine
from speech.wake.engine_keyword import KeywordWakeEngine, OpenWakeWordEngine, OpenWakeWordConfig

from nlp.intents.parser import parse
from nlp.intents.router import IntentRouter

# Milestone 3 wiring
from core.security.audit_log import AuditLog
from core.security.rate_limits import RateLimiter
from core.security.policy_engine import PolicyEngine
from core.security.auth.auth_window import AuthWindow

from devices.registry.store import RegistryStore
from devices.drivers.registry import DriverRegistry
from devices.execution.device_manager import DeviceManager

# Driver(s)
from devices.drivers.mqtt.driver import MQTTDriver


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


def build_device_manager(bus: EventBus) -> DeviceManager:
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
        offline_only=True,
    )


def main() -> None:
    log = get_logger("JARED")

    try:
        log.info("Boot sequence started")

        policy = NetPolicy()
        log.info(f"Offline mode: {not policy.allow_internet}")

        if not run_healthcheck():
            raise RuntimeError("Healthcheck failed")

        log.info("System initialized successfully (Milestone 0)")

        bus = EventBus()

        # Milestone 3 wiring
        device_manager = build_device_manager(bus)
        router = IntentRouter(device_manager=device_manager)

        def on_transcript(evt):
            raw_text = evt.data.get("text", "")
            clean = normalize_transcript_for_intent(raw_text)
            if clean is None:
                log.info(f"[transcript] dropped wake-only: '{raw_text}'")
                return

            match = parse(clean)
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

        bus.subscribe("voice.transcript", on_transcript)
        bus.subscribe("nlp.intent", on_intent)

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
        vp.run_forever()

    except KeyboardInterrupt:
        log.info("Shutdown requested")
        sys.exit(0)
    except Exception:
        log.critical("Fatal startup error")
        log.critical(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()