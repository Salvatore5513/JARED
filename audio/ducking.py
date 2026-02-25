from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DuckingParams:
    strength: float = 0.60
    threshold_db: float = -35.0
    hysteresis_db: float = 6.0
    attack_ms: float = 120.0
    release_ms: float = 350.0


class DuckingState:
    """
    Smooth ducking gain based on speech state.
    """
    def __init__(self, params: DuckingParams):
        self.p = params
        self.speech = False
        self.gain = 1.0

    def update_speech_from_rms_db(self, rms_db: float) -> bool:
        on_th = self.p.threshold_db
        off_th = self.p.threshold_db - self.p.hysteresis_db

        if not self.speech and rms_db >= on_th:
            self.speech = True
        elif self.speech and rms_db < off_th:
            self.speech = False
        return self.speech

    def step(self, dt_s: float) -> float:
        strength = max(0.0, min(1.0, self.p.strength))
        target = (1.0 - strength) if self.speech else 1.0

        # Attack: snap down using 1-pole
        if target < self.gain:
            tau = max(0.001, self.p.attack_ms / 1000.0)
            x = min(1.0, dt_s / tau)
            self.gain += (target - self.gain) * x
            return self.gain

        # Release: true linear ramp to 1.0 over release_ms
        release_s = max(0.05, self.p.release_ms / 1000.0)
        rate = (1.0 - (1.0 - self.p.strength)) / release_s  # max change per second from ducked->full
        # But since we might not be fully ducked, just move toward 1.0 at a steady rate:
        self.gain = min(1.0, self.gain + rate * dt_s)
        return self.gain



# ---- Backwards compatible wrapper (your original API) ----

class DuckingController:
    """
    Backwards compatible with your original class.
    Internally uses DuckingState for smooth gain.
    """
    def __init__(self, strength: float = 0.6):
        self._state = DuckingState(DuckingParams(strength=strength))

    def apply(self, base_volume: float) -> float:
        # If you call apply() without calling step(), this just returns base_volume * current gain.
        return base_volume * self._state.gain

    def set_active(self, active: bool):
        self._state.speech = bool(active)

    @property
    def strength(self) -> float:
        return self._state.p.strength

    @strength.setter
    def strength(self, v: float) -> None:
        self._state.p.strength = max(0.0, min(1.0, float(v)))
