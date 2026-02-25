from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class PostprocessConfig:
    # add variants you naturally say
    wake_phrases: tuple[str, ...] = (
        "hey jared",
        "okay jared",
        "ok jared",
        "jared",
    )

    # light cleanup
    strip_fillers: tuple[str, ...] = ("please", "can you", "could you")


def _collapse_spaces(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _strip_prefix_phrases(text: str, phrases: Iterable[str]) -> str:
    t = text.lstrip()
    lower = t.lower()

    for p in phrases:
        p = p.lower().strip()
        if lower == p:
            return ""
        if lower.startswith(p + " "):
            # remove only once; re-collapse
            t2 = t[len(p):].lstrip()
            return _collapse_spaces(t2)

    return text


def normalize_transcript(text: str, cfg: PostprocessConfig | None = None) -> str:
    """
    Milestone 2 transcript normalization:
    - remove leading wake phrase (so 'hey jared set volume 19' -> 'set volume 19')
    - light filler stripping
    - collapse spaces
    """
    cfg = cfg or PostprocessConfig()

    t = text.strip()
    if not t:
        return ""

    t = _strip_prefix_phrases(t, cfg.wake_phrases)

    # filler stripping at start (optional)
    t_lower = t.lower()
    for f in cfg.strip_fillers:
        f = f.lower().strip()
        if t_lower == f:
            return ""
        if t_lower.startswith(f + " "):
            t = t[len(f):].lstrip()
            break

    return _collapse_spaces(t)