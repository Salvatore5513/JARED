from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Optional


def _now_ms() -> int:
    return int(time.time() * 1000)


@dataclass
class RateLimitResult:
    limited: bool
    retry_in_ms: int = 0
    last_ts_ms: int = 0


class RateLimiter:
    """
    Simple cooldown-based rate limiter.

    Keys can be:
      - intent name
      - device_id
      - intent+device_id
    """

    def __init__(self, *, default_cooldown_ms: int = 700):
        self.default_cooldown_ms = int(default_cooldown_ms)
        self._last_seen: Dict[str, int] = {}

    def check(self, key: str, *, cooldown_ms: Optional[int] = None, now_ms: Optional[int] = None) -> RateLimitResult:
        now = _now_ms() if now_ms is None else int(now_ms)
        cd = self.default_cooldown_ms if cooldown_ms is None else int(cooldown_ms)

        last = self._last_seen.get(key, 0)
        elapsed = now - last

        if last != 0 and elapsed < cd:
            return RateLimitResult(limited=True, retry_in_ms=(cd - elapsed), last_ts_ms=last)

        self._last_seen[key] = now
        return RateLimitResult(limited=False, retry_in_ms=0, last_ts_ms=last)