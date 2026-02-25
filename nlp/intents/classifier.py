from __future__ import annotations
import re
from nlp.intents.schema import IntentMatch


def _norm(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w\s]", "", s)   # remove punctuation
    return re.sub(r"\s+", " ", s)



def classify(text: str) -> IntentMatch:
    t = _norm(text)

    # Media
    if t in {"play", "play music", "resume"}:
        return IntentMatch("media.play", 0.95, {}, text)
    if t in {"pause", "pause music", "stop music", "stop"}:
        return IntentMatch("media.pause", 0.95, {}, text)
    m = re.match(r"set volume (\d{1,3})", t)
    if m:
        v = max(0, min(100, int(m.group(1))))
        return IntentMatch("media.set_volume", 0.9, {"volume": v}, text)

    # System
    if t in {"status", "system status", "health"}:
        return IntentMatch("system.status", 0.9, {}, text)
    if t in {"offline mode on", "go offline"}:
        return IntentMatch("system.offline_on", 0.9, {}, text)
    if t in {"offline mode off", "go online"}:
        return IntentMatch("system.offline_off", 0.9, {}, text)
    if t in {"is it working", "are you working", "can you hear me"}:
        return IntentMatch("system.status", 0.8, {}, text)


    # Devices (placeholders for Milestone 3)
    m = re.match(r"turn (on|off) (.+)", t)
    if m:
        return IntentMatch(
            "device.toggle",
            0.85,
            {"state": m.group(1), "target": m.group(2)},
            text,
        )

    # Garage quick-notes (future memory)
    m = re.match(r"note (.+)", t)
    if m:
        return IntentMatch("garage.note", 0.8, {"text": m.group(1)}, text)

    if t in {"help", "what can you do"}:
        return IntentMatch("system.help", 0.9, {}, text)

    return IntentMatch("unknown", 0.2, {}, text)
