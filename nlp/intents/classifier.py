from __future__ import annotations
import re
from nlp.intents.schema import IntentMatch
from typing import Optional


def _norm(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"^the\s+", "", s)
    return s



def classify(text: str) -> Optional[IntentMatch]:
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


    # Pattern A: "turn on/off <target>"
    m = re.match(r"turn (on|off) (.+)", t)
    if m:
        return IntentMatch(
            "device.toggle",
            0.85,
            {"state": m.group(1), "target": m.group(2)},
            text,
        )

    # Pattern B: "turn <target> on/off" (what you said: "turn garage lights on")
    m = re.match(r"turn (.+) (on|off)", t)
    if m:
        return IntentMatch(
            "device.toggle",
            0.85,
            {"state": m.group(2), "target": m.group(1)},
            text,
        )

    # Pattern C (optional): "switch <target> on/off"
    m = re.match(r"switch (.+) (on|off)", t)
    if m:
        return IntentMatch(
            "device.toggle",
            0.85,
            {"state": m.group(2), "target": m.group(1)},
            text,
        )
