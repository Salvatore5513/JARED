from core.observability.logger import get_logger
from core.observability.healthcheck import run_healthcheck
from core.net.policy import NetPolicy
from core.event_bus import EventBus
from speech.pipeline import VoicePipeline
from speech.wake.engine_keyword import (
    KeywordWakeEngine,
    OpenWakeWordEngine,
    OpenWakeWordConfig,
)
from speech.stt.local_engine import WhisperCppSTTEngine
from nlp.intents.parser import parse
from nlp.intents.router import IntentRouter
import sys, os

import traceback


def main():
    log = get_logger("JARED")

    try:
        log.info("Boot sequence started")

        policy = NetPolicy()
        log.info(f"Offline mode: {not policy.allow_internet}")

        if not run_healthcheck():
            raise RuntimeError("Healthcheck failed")

        log.info("System initialized successfully (Milestone 0)")

        bus = EventBus()
        router = IntentRouter()

        def on_transcript(evt):
            text = evt.data.get("text", "").strip()
            if not text:
                return
            match = parse(text)
            bus.publish(
                "nlp.intent",
                name=match.name,
                confidence=match.confidence,
                slots=match.slots,
                raw_text=match.raw_text,
            )

        def on_intent(evt):
            # optional: keep your intent log
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
        # - set JARED_WAKE_ENGINE=dev to force dev mode
        wake_choice = os.getenv("JARED_WAKE_ENGINE", "").strip().lower()

        if wake_choice in {"dev", "keyword", "stdin"}:
            wake_engine = KeywordWakeEngine()
            log.info("Wake engine: DEV (stdin trigger)")
        else:
            wake_engine = OpenWakeWordEngine(
                cfg=OpenWakeWordConfig(
                    threshold=0.59,   # you liked this
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
